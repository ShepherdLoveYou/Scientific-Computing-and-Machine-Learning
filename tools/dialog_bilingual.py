"""Dialog-driven bilingualizer — use when ANTHROPIC_API_KEY is not configured
and Claude inside Claude Code translates directly in the chat.

Two subcommands:

    dump <notebook>
        Print all markdown cells that still need translation (i.e. do NOT
        contain the idempotency marker `<!-- bilingual:en -->`) as a JSON
        object mapping `cell_index` -> `source`. Claude reads this output,
        produces translations in-chat, then emits a translations JSON file
        back on disk.

    apply <notebook> <translations.json> [--dry-run]
        Splice each translation into the notebook. The resulting cell source
        becomes:
            <original>\\n\\n---\\n\\n<translation>\\n\\n<!-- bilingual:en -->
        With --dry-run the output is written to `<notebook>.bilingual.ipynb`
        instead of in-place.

Typical flow (per notebook):
    python tools/dialog_bilingual.py dump   "Chapter01/1. 科学计算.ipynb" > cells.json
    # Claude (in chat) writes translations.json with same keys
    python tools/dialog_bilingual.py apply  "Chapter01/1. 科学计算.ipynb" translations.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import nbformat

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKER = "<!-- bilingual:en -->"
SEP = "\n\n---\n\n"


def _resolve(path_arg: str) -> Path:
    p = Path(path_arg)
    return p if p.is_absolute() else (REPO_ROOT / p)


def cmd_dump(args: argparse.Namespace) -> int:
    nb_path = _resolve(args.notebook)
    nb = nbformat.read(nb_path, as_version=4)
    out: dict[int, str] = {}
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "markdown":
            continue
        source = cell.source if isinstance(cell.source, str) else "".join(cell.source)
        if MARKER in source:
            continue
        if not source.strip():
            continue
        out[i] = source
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    nb_path = _resolve(args.notebook)
    translations_path = _resolve(args.translations)
    with open(translations_path, encoding="utf-8") as fh:
        translations = json.load(fh)
    # JSON keys are strings; normalise to int
    translations = {int(k): v for k, v in translations.items()}

    nb = nbformat.read(nb_path, as_version=4)
    spliced = skipped = 0
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "markdown":
            continue
        if i not in translations:
            continue
        english = translations[i]
        if not english or not english.strip():
            skipped += 1
            continue
        original = cell.source if isinstance(cell.source, str) else "".join(cell.source)
        if MARKER in original:
            skipped += 1
            continue
        cell.source = f"{original}{SEP}{english.rstrip()}\n\n{MARKER}"
        spliced += 1

    out_path = nb_path.with_suffix(".bilingual.ipynb") if args.dry_run else nb_path
    nbformat.write(nb, out_path)
    mode = "dry-run" if args.dry_run else "in-place"
    print(f"{mode}: spliced={spliced}  skipped={skipped}  out={out_path.relative_to(REPO_ROOT).as_posix()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_dump = sub.add_parser("dump", help="print markdown cells needing translation as JSON")
    p_dump.add_argument("notebook", help="notebook path (repo-relative or absolute)")
    p_dump.set_defaults(func=cmd_dump)

    p_apply = sub.add_parser("apply", help="splice translations back into the notebook")
    p_apply.add_argument("notebook", help="notebook path (repo-relative or absolute)")
    p_apply.add_argument("translations", help="JSON file mapping cell_index (str) -> english text")
    p_apply.add_argument("--dry-run", action="store_true",
                         help="write to <notebook>.bilingual.ipynb instead of in place")
    p_apply.set_defaults(func=cmd_apply)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
