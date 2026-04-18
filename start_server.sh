#!/bin/bash
# Start JupyterLab with settings that work inside a Hugging Face Space iframe.
# CSP header allows embedding, SameSite=None cookies survive iframe context,
# default_url lands users on Welcome.ipynb, noisy extensions are silenced.

JUPYTER_TOKEN="${JUPYTER_TOKEN:-}"
NOTEBOOK_DIR="/home/user/app"

# Clear cached workspace so default_url wins every visit.
rm -rf "$HOME/.jupyter/lab/workspaces" 2>/dev/null || true

jupyter labextension disable "@jupyterlab/apputils-extension:announcements" 2>/dev/null || true

exec jupyter-lab \
    --ip 0.0.0.0 \
    --port 7860 \
    --no-browser \
    --allow-root \
    --ServerApp.token="$JUPYTER_TOKEN" \
    --ServerApp.password="" \
    --IdentityProvider.token="$JUPYTER_TOKEN" \
    --ServerApp.tornado_settings="{'headers': {'Content-Security-Policy': 'frame-ancestors *'}}" \
    --ServerApp.cookie_options="{'SameSite': 'None', 'Secure': True}" \
    --ServerApp.disable_check_xsrf=True \
    --ServerApp.default_url=/lab/tree/Welcome.ipynb \
    --LabApp.default_url=/lab/tree/Welcome.ipynb \
    --LabApp.news_url=None \
    --LabApp.check_for_updates_class="jupyterlab.NeverCheckForUpdate" \
    --notebook-dir="$NOTEBOOK_DIR"
