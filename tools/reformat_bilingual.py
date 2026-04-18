"""Reformat already-bilingualized markdown cells from "two big blocks" layout
to the "interleaved paragraph-by-paragraph" layout used by the reference
project re0-futures-options-and-derivatives.

Input cell layout (from tools/dialog_bilingual.py):

    <CN full content>

    ---

    <EN full content>

    <!-- bilingual:en -->

Output cell layout (matches reference project):

    # <CN heading> / <EN heading>
    ## <CN sub> / <EN sub>

    <CN paragraph 1>

    <EN paragraph 1>

    <CN paragraph 2>

    <EN paragraph 2>

Rules:
  * CN and EN halves are split on the first `\\n\\n---\\n\\n` delimiter.
  * The `<!-- bilingual:en -->` marker is replaced with `<!-- bilingual -->`
    so idempotent re-runs still skip already-reformatted cells.
  * Blocks are separated by blank lines, with code fences and HTML blocks
    treated as atomic.
  * Same-level headings (same `#`-count) at matching positions are merged
    into a single line: `## CN / EN`. Headings whose text is the same in
    CN and EN (e.g. pure English titles) are not duplicated.
  * If the CN and EN halves have different block counts, the tool falls
    back to zipping by index and emitting leftover blocks from whichever
    side is longer at the end.
  * Tables, code fences, LaTeX blocks, and images are preserved verbatim
    (emitted on the CN side; the tool does not try to translate them).

Usage:
    python tools/reformat_bilingual.py                # preview (dry-run)
    python tools/reformat_bilingual.py --apply        # rewrite in place
    python tools/reformat_bilingual.py --notebook "Chapter01/1. 科学计算.ipynb" --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterator

import nbformat

REPO_ROOT = Path(__file__).resolve().parent.parent
OLD_MARKER = "<!-- bilingual:en -->"
NEW_MARKER = "<!-- bilingual -->"
DELIM_RE = re.compile(r"\n\n---\n\n")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def split_blocks(text: str) -> list[str]:
    """Split markdown into block-level units. Blank lines separate blocks.
    Heading lines (# ...) are always emitted as their own block so
    `heading + paragraph` without an intervening blank still splits cleanly.
    A trailing horizontal rule (`---` / `===`) immediately under a heading
    stays attached to that heading so `merge_headings` can still identify it.
    Fenced code blocks and HTML blocks are atomic."""
    lines = text.split("\n")
    blocks: list[str] = []
    buf: list[str] = []
    in_fence = False
    in_html = False

    def flush() -> None:
        nonlocal buf
        if buf and any(l.strip() for l in buf):
            blocks.append("\n".join(buf).rstrip())
        buf = []

    for line in lines:
        stripped = line.strip()
        if not in_fence and not in_html and stripped.startswith("```"):
            in_fence = True
            flush()
            buf.append(line)
            continue
        if in_fence:
            buf.append(line)
            if stripped.startswith("```"):
                in_fence = False
                flush()
            continue
        if not in_html and re.match(r"^<(img|table|div|pre|figure|video)\b", stripped, re.I):
            flush()
            in_html = True
            buf.append(line)
            if re.search(r"/>$|</\w+>$", stripped):
                in_html = False
                flush()
            continue
        if in_html:
            buf.append(line)
            if re.search(r"</(img|table|div|pre|figure|video)>$", stripped, re.I):
                in_html = False
                flush()
            continue
        if stripped == "":
            flush()
            continue
        # heading? emit as its own block
        if HEADING_RE.match(stripped):
            flush()
            buf.append(line)
            continue
        # horizontal rule immediately after a single-line heading -> attach
        if re.fullmatch(r"[-=]{3,}", stripped) and len(buf) == 1 and HEADING_RE.match(buf[0].strip()):
            buf.append(line)
            flush()
            continue
        # incoming line follows a heading-only buf (no blank between) -> split
        if buf and HEADING_RE.match(buf[0].strip()) and all(HEADING_RE.match(l.strip()) or re.fullmatch(r"[-=]{3,}", l.strip()) for l in buf):
            flush()
        buf.append(line)
    flush()
    return blocks


def heading_info(block: str) -> tuple[int, str, bool] | None:
    """Return (level, text, has_hr) if the block is a heading (single line, or
    `# X\\n---` / `# X\\n===` style with a trailing horizontal rule). Otherwise
    return None. `has_hr` indicates whether the trailing horizontal rule was
    present in the original and should be reinstated after the merged line."""
    stripped = block.strip()
    lines = [l for l in stripped.split("\n") if l.strip()]
    if not lines:
        return None
    first = lines[0]
    # strip trailing horizontal-rule lines (--- or ===) of any length
    rest = lines[1:]
    has_hr = False
    if rest and re.fullmatch(r"[-=]{3,}", rest[-1].strip()):
        has_hr = True
        rest = rest[:-1]
    if rest:
        # still multi-line content after stripping hr -> not a plain heading
        return None
    m = HEADING_RE.match(first)
    if not m:
        return None
    return len(m.group(1)), m.group(2).strip(), has_hr


def merge_headings(cn: str, en: str) -> str | None:
    """If both blocks are headings of the same level, return merged heading line."""
    cn_h, en_h = heading_info(cn), heading_info(en)
    if cn_h is None or en_h is None:
        return None
    if cn_h[0] != en_h[0]:
        return None
    has_hr = cn_h[2] or en_h[2]
    if cn_h[1].strip() == en_h[1].strip():
        merged = "#" * cn_h[0] + " " + cn_h[1]
    else:
        merged = "#" * cn_h[0] + " " + cn_h[1] + " / " + en_h[1]
    if has_hr:
        # Emit as two blocks so `split_blocks` later preserves structure
        return merged + "\n\n---"
    return merged


def interleave(cn_text: str, en_text: str) -> str:
    cn_blocks = split_blocks(cn_text)
    en_blocks = split_blocks(en_text)
    out: list[str] = []
    i = j = 0
    while i < len(cn_blocks) and j < len(en_blocks):
        cn, en = cn_blocks[i], en_blocks[j]
        # Dedup identical blocks (e.g. <img>, <figure>, fenced code) that appear
        # in both halves because the translator didn't treat them as Chinese.
        if cn.strip() == en.strip():
            out.append(cn)
            i += 1
            j += 1
            continue
        merged = merge_headings(cn, en)
        if merged is not None:
            out.append(merged)
            i += 1
            j += 1
            continue
        # default: emit CN then EN as sibling paragraphs
        out.append(cn)
        out.append(en)
        i += 1
        j += 1
    # trailing blocks from either side (counts differed)
    while i < len(cn_blocks):
        out.append(cn_blocks[i])
        i += 1
    while j < len(en_blocks):
        out.append(en_blocks[j])
        j += 1
    # collapse consecutive identical blocks (conservative second pass)
    deduped: list[str] = []
    for b in out:
        if deduped and deduped[-1].strip() == b.strip():
            continue
        deduped.append(b)
    return "\n\n".join(deduped)


def reformat_cell(source: str) -> str | None:
    """Reformat a single markdown cell source. Returns None if nothing to do."""
    if NEW_MARKER in source:
        return None  # already reformatted
    if OLD_MARKER not in source:
        return None  # not bilingualized yet
    body = source
    # strip the old end marker
    body = body.replace(OLD_MARKER, "").rstrip()
    # split on first `---` delimiter
    parts = DELIM_RE.split(body, maxsplit=1)
    if len(parts) != 2:
        return None
    cn, en = parts[0].rstrip(), parts[1].strip()
    interleaved = interleave(cn, en)
    return interleaved + "\n\n" + NEW_MARKER


def iter_notebooks(only: str | None) -> Iterator[Path]:
    if only:
        p = Path(only)
        if not p.is_absolute():
            p = REPO_ROOT / p
        yield p
        return
    for nb in sorted(REPO_ROOT.rglob("*.ipynb")):
        if ".ipynb_checkpoints" in nb.parts:
            continue
        if nb.suffix == ".ipynb" and ".bak" not in nb.name and ".bilingual" not in nb.name:
            if any(nb.parts[i].startswith("Chapter") for i in range(len(nb.parts))):
                yield nb


def process(nb_path: Path, apply: bool) -> tuple[int, int]:
    nb = nbformat.read(nb_path, as_version=4)
    changed = 0
    total = 0
    for cell in nb.cells:
        if cell.cell_type != "markdown":
            continue
        src = cell.source if isinstance(cell.source, str) else "".join(cell.source)
        if OLD_MARKER not in src:
            continue
        total += 1
        new = reformat_cell(src)
        if new is None or new == src:
            continue
        cell.source = new
        changed += 1
    if apply and changed:
        nbformat.write(nb, nb_path)
    return total, changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="actually rewrite notebooks")
    parser.add_argument("--notebook", help="process a single notebook (repo-relative or absolute)")
    args = parser.parse_args()

    gtotal = gchanged = nb_count = 0
    for nb in iter_notebooks(args.notebook):
        if not nb.exists():
            continue
        total, changed = process(nb, args.apply)
        nb_count += 1
        gtotal += total
        gchanged += changed
        rel = nb.relative_to(REPO_ROOT).as_posix()
        mode = "applied" if args.apply else "would change"
        print(f"  {rel}: {changed}/{total} cells ({mode})")

    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"\n{mode}: {gchanged} cells reformatted across {nb_count} notebooks "
          f"(eligible: {gtotal})")
    if not args.apply:
        print("Pass --apply to actually rewrite notebooks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
