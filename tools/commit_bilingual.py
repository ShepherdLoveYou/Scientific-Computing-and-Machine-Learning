"""Promote every `*.bilingual.ipynb` dry-run sibling to the canonical notebook
path, after the user has reviewed the dry-run output.

For each `X/Y.bilingual.ipynb`:
  1. Move `X/Y.ipynb` -> `X/Y.ipynb.bak` (keeps a local copy alongside git).
  2. Move `X/Y.bilingual.ipynb` -> `X/Y.ipynb`.

Idempotent: if the bilingual sibling is missing, the notebook is skipped; if a
`.bak` already exists, it is overwritten so re-running after a second round of
bilingual output still works.

Usage:
    python tools/commit_bilingual.py                # preview (dry-run)
    python tools/commit_bilingual.py --apply        # actually move files
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def iter_bilingual_pairs() -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for bi in sorted(REPO_ROOT.rglob("*.bilingual.ipynb")):
        if ".ipynb_checkpoints" in bi.parts:
            continue
        orig = bi.with_name(bi.name.replace(".bilingual.ipynb", ".ipynb"))
        pairs.append((orig, bi))
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="actually move files (otherwise preview only)")
    args = parser.parse_args()

    pairs = iter_bilingual_pairs()
    print(f"Found {len(pairs)} bilingual pairs")
    for orig, bi in pairs:
        bak = orig.with_suffix(orig.suffix + ".bak")
        rel = orig.relative_to(REPO_ROOT).as_posix()
        if args.apply:
            if orig.exists():
                shutil.move(str(orig), str(bak))
            shutil.move(str(bi), str(orig))
            print(f"  [moved] {rel}  (original preserved as {bak.name})")
        else:
            print(f"  [plan]  {rel}  <- {bi.name}  (original -> {bak.name})")

    if not args.apply:
        print("\nDry-run only. Pass --apply to actually move files.")
    else:
        print(f"\nDone. {len(pairs)} notebooks updated. Review via `git diff --stat`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
