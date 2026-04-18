"""Batch-execute every chapter notebook and report PASS / FAIL / TIMEOUT / SKIP.

Design mirrors the reference project `re0-futures-options-and-derivatives`:
walks the repo for `Chapter*/**/*.ipynb`, filters out paths listed in
`tools/skip_notebooks.txt`, and runs each one with
`nbclient.NotebookClient` at a 180 s per-cell timeout. The exit code is
non-zero if any notebook fails. Output ends with a one-line summary so it
is grep-friendly from CI logs.

Run locally:
    conda activate D:\\envs\\scml  # or your chosen prefix
    python _test_notebooks.py
    python _test_notebooks.py --only Chapter08       # one chapter
    python _test_notebooks.py --timeout 60 --quick   # fast smoke pass
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError, CellTimeoutError

REPO_ROOT = Path(__file__).resolve().parent
SKIP_LIST_FILE = REPO_ROOT / "tools" / "skip_notebooks.txt"

os.environ.setdefault("KERAS_BACKEND", "torch")


@dataclass
class Result:
    path: Path
    status: str  # "PASS" | "FAIL" | "TIMEOUT" | "SKIP"
    elapsed_s: float
    error: str = ""


def load_skip_list() -> set[str]:
    if not SKIP_LIST_FILE.exists():
        return set()
    entries: set[str] = set()
    for line in SKIP_LIST_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.add(line.replace("\\", "/"))
    return entries


def iter_notebooks() -> Iterable[Path]:
    for chapter_dir in sorted(REPO_ROOT.glob("Chapter*")):
        for nb in sorted(chapter_dir.rglob("*.ipynb")):
            if ".ipynb_checkpoints" in nb.parts:
                continue
            if nb.name.endswith(".bilingual.ipynb"):
                continue
            yield nb


def relative_posix(p: Path) -> str:
    return p.relative_to(REPO_ROOT).as_posix()


def execute(nb_path: Path, timeout: int) -> Result:
    start = time.monotonic()
    try:
        nb = nbformat.read(nb_path, as_version=4)
        client = NotebookClient(
            nb,
            timeout=timeout,
            kernel_name=nb.metadata.get("kernelspec", {}).get("name", "python3"),
            resources={"metadata": {"path": str(nb_path.parent)}},
        )
        client.execute()
    except CellTimeoutError as exc:
        return Result(nb_path, "TIMEOUT", time.monotonic() - start, str(exc)[:200])
    except CellExecutionError as exc:
        return Result(nb_path, "FAIL", time.monotonic() - start, str(exc).splitlines()[-1][:200])
    except Exception as exc:  # e.g. missing kernel for Julia if kernel not installed
        return Result(nb_path, "FAIL", time.monotonic() - start, f"{type(exc).__name__}: {exc}"[:200])
    return Result(nb_path, "PASS", time.monotonic() - start)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=180,
                        help="per-cell timeout in seconds (default 180)")
    parser.add_argument("--only", default=None,
                        help="only run notebooks whose path contains this substring")
    parser.add_argument("--quick", action="store_true",
                        help="sort shortest-first and stop after 3 failures")
    args = parser.parse_args()

    skip = load_skip_list()
    notebooks = list(iter_notebooks())
    if args.only:
        notebooks = [nb for nb in notebooks if args.only in relative_posix(nb)]
    if args.quick:
        notebooks.sort(key=lambda p: p.stat().st_size)

    results: list[Result] = []
    fail_count = 0
    for nb in notebooks:
        rel = relative_posix(nb)
        if rel in skip:
            results.append(Result(nb, "SKIP", 0.0, "in skip_notebooks.txt"))
            print(f"  [SKIP] {rel}")
            continue
        print(f"  ....   {rel}", flush=True)
        r = execute(nb, args.timeout)
        results.append(r)
        marker = {"PASS": "PASS", "FAIL": "FAIL", "TIMEOUT": "TOUT", "SKIP": "SKIP"}[r.status]
        line = f"  [{marker}] {rel}  ({r.elapsed_s:.1f}s)"
        if r.error:
            line += f"  :: {r.error}"
        print(line, flush=True)
        if r.status in ("FAIL", "TIMEOUT"):
            fail_count += 1
            if args.quick and fail_count >= 3:
                print("  --quick threshold reached; stopping early")
                break

    p = sum(1 for r in results if r.status == "PASS")
    f = sum(1 for r in results if r.status == "FAIL")
    t = sum(1 for r in results if r.status == "TIMEOUT")
    s = sum(1 for r in results if r.status == "SKIP")
    total = len(results)
    print()
    print(f"PASS: {p}  FAIL: {f}  TIMEOUT: {t}  SKIP: {s}  TOTAL: {total}")
    return 0 if (f == 0 and t == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
