"""Strip output cells and execution counts from every notebook in the repo.

This cuts the on-disk size of the repo substantially (Ch09 alone drops from
~57 MB to ~0.2 MB) because matplotlib animation GIFs and other large outputs
are not carried in git or in the Docker image. Students re-generate them by
running the notebook.

Never modifies markdown cells (those contain our bilingual translations).

Usage:
    python tools/nbstripout_all.py                # dry-run (count only)
    python tools/nbstripout_all.py --apply        # actually strip
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nbformat

REPO_ROOT = Path(__file__).resolve().parent.parent


def strip_notebook(nb_path: Path) -> tuple[int, int]:
    """Strip outputs from a single notebook. Returns (cells_stripped, bytes_freed)."""
    before = nb_path.stat().st_size
    nb = nbformat.read(nb_path, as_version=4)
    stripped = 0
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        if cell.get("outputs") or cell.get("execution_count") is not None:
            cell["outputs"] = []
            cell["execution_count"] = None
            stripped += 1
    nbformat.write(nb, nb_path)
    after = nb_path.stat().st_size
    return stripped, before - after


def iter_notebooks() -> list[Path]:
    out: list[Path] = []
    for nb in sorted(REPO_ROOT.rglob("*.ipynb")):
        if ".ipynb_checkpoints" in nb.parts:
            continue
        if nb.name.endswith(".bak") or ".bilingual" in nb.name:
            continue
        if any(p.startswith("Chapter") for p in nb.parts):
            out.append(nb)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="actually strip outputs")
    args = parser.parse_args()

    notebooks = iter_notebooks()
    total_cells = 0
    total_freed = 0
    for nb_path in notebooks:
        if not args.apply:
            # Just count
            nb = nbformat.read(nb_path, as_version=4)
            candidates = sum(
                1 for c in nb.cells
                if c.cell_type == "code" and (c.get("outputs") or c.get("execution_count") is not None)
            )
            total_cells += candidates
            rel = nb_path.relative_to(REPO_ROOT).as_posix()
            if candidates:
                print(f"  {rel}: would strip {candidates} cells")
            continue
        stripped, freed = strip_notebook(nb_path)
        total_cells += stripped
        total_freed += freed
        rel = nb_path.relative_to(REPO_ROOT).as_posix()
        if stripped:
            print(f"  {rel}: stripped {stripped} cells, freed {freed/1024:.1f} KB")

    mode = "APPLIED" if args.apply else "DRY-RUN"
    if args.apply:
        print(f"\n{mode}: {total_cells} cells across {len(notebooks)} notebooks, {total_freed/1024/1024:.2f} MB freed")
    else:
        print(f"\n{mode}: {total_cells} cells would be stripped across {len(notebooks)} notebooks (pass --apply to do it)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
