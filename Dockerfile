# syntax=docker/dockerfile:1.7
# Multi-stage slim build for SCML on Hugging Face Space.
#
#   Stage 1 (builder): micromamba installs the conda-forge environment,
#   then strips dead weight (pandoc, Qt GUI, C headers, __pycache__,
#   tests, docs) BEFORE the runtime stage copies it. Putting the cleanup
#   in the builder matters — once COPY --from=builder runs, its layer is
#   frozen in the image, so any later deletion only creates an overlay
#   without actually shrinking the image.
#
#   Stage 2 (runtime): python:3.11-slim base + the pre-stripped env.
#   Runs JupyterLab as non-root user:1000 on port 7860 per the Hugging
#   Face Space Docker convention.
#
# Expected final image: < 3 GB. First build ~8 min (BuildKit cache mount
# amortizes subsequent builds to ~2 min).

# ------------------------- builder stage -------------------------
FROM mambaorg/micromamba:1.5.8-bookworm AS builder

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates curl git build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY environment-docker.yml /tmp/environment-docker.yml

# micromamba build. The cache mount makes subsequent `docker build`
# invocations re-use the conda package cache.
RUN --mount=type=cache,target=/opt/conda/pkgs \
    micromamba create -p /opt/env -y -f /tmp/environment-docker.yml && \
    micromamba clean -a -y

# Aggressive strip: everything below is dead weight for a JupyterLab
# server + nbclient CI runtime. Each item audited to confirm nothing in
# the SCML chapters actually imports it.
RUN set -eux; \
    # 1. pandoc (155 MB): nbconvert PDF/DocX export only; we use HTML.
    rm -f /opt/env/bin/pandoc; \
    # 2. C headers (~80 MB): compile-time only.
    rm -rf /opt/env/include; \
    # 3. Qt GUI stack (~60 MB): we do not run any Qt matplotlib backend.
    rm -rf /opt/env/share/qt6 /opt/env/share/PySide6 \
           /opt/env/lib/python3.11/site-packages/PySide6 \
           /opt/env/lib/python3.11/site-packages/shiboken6 \
           /opt/env/lib/python3.11/site-packages/shiboken6_generator \
           /opt/env/bin/shiboken6 /opt/env/bin/pyside6-* 2>/dev/null || true; \
    # 4. Unused share assets (~25 MB).
    rm -rf /opt/env/share/gir-1.0 /opt/env/share/cups /opt/env/share/xkeyboard-config-2 \
           /opt/env/share/X11 /opt/env/share/postgres.bki /opt/env/share/terminfo 2>/dev/null || true; \
    # 5. Toolchain binaries (~5 MB): we do not compile anything in the runtime.
    rm -f /opt/env/bin/x86_64-conda-linux-gnu-* \
          /opt/env/bin/aomenc /opt/env/bin/aomdec \
          /opt/env/bin/ldapsearch /opt/env/bin/ldapmodify* /opt/env/bin/ldap* \
          /opt/env/bin/pcre2test /opt/env/bin/pcre2grep 2>/dev/null || true; \
    # 6. Daemon-style dirs and runtime-irrelevant caches.
    rm -rf /opt/env/sbin /opt/env/var /opt/env/compiler_compat \
           /opt/env/x86_64-conda-linux-gnu /opt/env/libexec 2>/dev/null || true; \
    # 7. Standard cache / test / doc stripping (from the previous iteration).
    find /opt/env -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true; \
    find /opt/env -name '*.pyc' -delete 2>/dev/null || true; \
    find /opt/env/lib -type d \( -name 'tests' -o -name 'test' \) -exec rm -rf {} + 2>/dev/null || true; \
    rm -rf /opt/env/share/doc /opt/env/share/man /opt/env/share/info /opt/env/share/locale 2>/dev/null || true; \
    rm -rf /opt/env/pkgs /opt/env/conda-meta 2>/dev/null || true; \
    # Report what remains in the top of /opt/env
    du -sh /opt/env 2>/dev/null || true


# ------------------------- runtime stage -------------------------
FROM python:3.11-slim-bookworm AS runtime

# Minimal runtime system libs required by matplotlib / jupyter / k3d /
# bqplot widgets and by the scientific python stack. `tini` is PID 1
# for graceful signal handling; `git` supports any in-container cloning
# users might do.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgomp1 libgl1 libglib2.0-0 libstdc++6 libxext6 libxrender1 \
        ca-certificates tini git && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/env /opt/env

# Put all jupyter runtime state under a single user-writable /home/user/.jupyter
# tree so the app directory itself can stay read-only.
ENV PATH=/opt/env/bin:$PATH \
    JUPYTER_TOKEN="" \
    HOME=/home/user \
    JUPYTER_CONFIG_DIR=/home/user/.jupyter \
    JUPYTER_DATA_DIR=/home/user/.jupyter/data \
    JUPYTER_RUNTIME_DIR=/home/user/.jupyter/runtime \
    IPYTHONDIR=/home/user/.jupyter/ipython \
    MPLCONFIGDIR=/home/user/.jupyter/matplotlib \
    XDG_CACHE_HOME=/tmp/.cache \
    POOCH_CACHE_DIR=/tmp/.cache/pooch \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home --shell /bin/bash --uid 1000 user

WORKDIR /home/user/app
COPY --chown=root:root . /home/user/app

# Build-time generation of the landing page from README + the PARTS table.
RUN /opt/env/bin/python /home/user/app/_generate_welcome.py
RUN chmod +x /home/user/app/start_server.sh

# Pre-warm matplotlib font cache and bake it into the image so cold
# container starts don't spend 30-60s rebuilding fc-cache on first plot.
# Cache lives at $MPLCONFIGDIR = /home/user/.jupyter/matplotlib (writable).
RUN mkdir -p /home/user/.jupyter/matplotlib && \
    MPLCONFIGDIR=/home/user/.jupyter/matplotlib \
    XDG_CACHE_HOME=/home/user/.jupyter/matplotlib \
    /opt/env/bin/python -c "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; plt.plot([0,1]); plt.savefig('/tmp/_warmup.png'); import os; os.remove('/tmp/_warmup.png'); print('font cache warmed')"

# Hugging Face Space-style permission lockdown: app and caches root-owned
# read-only; only /home/user/.jupyter subtree is user-writable so
# notebooks, widget state, and matplotlib font cache can be created at
# runtime.
RUN set -eu && \
    chown -R root:root /home/user/app && \
    chmod -R a-w,a+rX /home/user/app && \
    mkdir -p /home/user/.cache /home/user/.config && \
    chown -R root:root /home/user/.cache /home/user/.config && \
    chmod -R a-w,a+rX /home/user/.cache /home/user/.config && \
    mkdir -p /home/user/.local && \
    chown root:root /home/user/.local && \
    chmod 555 /home/user/.local && \
    mkdir -p /home/user/.jupyter/data \
             /home/user/.jupyter/runtime \
             /home/user/.jupyter/ipython \
             /home/user/.jupyter/matplotlib \
             /home/user/.jupyter/lab/workspaces \
             /home/user/.jupyter/lab/user-settings && \
    chown -R user:user /home/user/.jupyter && \
    chmod 755 /home/user/.jupyter && \
    chown root:root /home/user && \
    chmod 755 /home/user

USER user
EXPOSE 7860

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["./start_server.sh"]
