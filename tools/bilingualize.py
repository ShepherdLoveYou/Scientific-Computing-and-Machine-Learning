"""Bilingualize Jupyter notebooks: append English translation after each Chinese
markdown cell, separated by `\\n\\n---\\n\\n` and terminated with an idempotency
marker `<!-- bilingual:en -->`.

Cost / speed design:
  * All cells -> claude-sonnet-4-6 (user preference: consistent translation quality
    over cheaper Haiku routing; LaTeX-heavy technical terminology requires stronger model).
  * Uses the Anthropic Message Batches API (50% discount, ~24h SLA)
  * Prompt caching on the shared system prompt per chapter

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    # Step 1: submit batches for one chapter (dry-run writes *.bilingual.ipynb)
    python tools/bilingualize.py --chapter Chapter01 --dry-run
    # Step 2: after review, run again to commit in place
    python tools/bilingualize.py --chapter Chapter01

    # All chapters in parallel (4 chapters at a time):
    python tools/bilingualize.py --all --jobs 4

Resume / idempotency:
    A cell already containing `<!-- bilingual:en -->` is skipped unconditionally.
    Interrupted runs leave the notebook unchanged if `--dry-run` is used.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import nbformat

try:
    import anthropic
except ImportError:
    sys.exit("anthropic SDK not installed. Run: pip install anthropic")

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKER = "<!-- bilingual:en -->"
SEP = "\n\n---\n\n"

MODEL = "claude-sonnet-4-6"  # single-model policy; see module docstring

SYSTEM_PROMPT = (
    "You translate Chinese Jupyter notebook markdown cells into English for a graduate-level "
    "scientific computing and machine learning course. Rules:\n"
    "1. Output ONLY the English translation. No preamble, no quotes, no commentary.\n"
    "2. Preserve ALL Markdown structure: headings, lists, tables, inline/block code, links, images.\n"
    "3. Preserve ALL LaTeX math verbatim ($...$, $$...$$, \\begin{...}).\n"
    "4. Preserve code fence contents exactly; translate only prose around them.\n"
    "5. Use standard technical terminology:\n"
    "   - 科学计算 = scientific computing\n"
    "   - 数值积分 = numerical integration\n"
    "   - 有限元 = finite element\n"
    "   - 蒙特卡罗 = Monte Carlo\n"
    "   - 密度泛函理论 = density functional theory (DFT)\n"
    "   - 分子动力学 = molecular dynamics\n"
    "   - 贝叶斯 = Bayesian\n"
    "   - 卷积神经网络 = convolutional neural network (CNN)\n"
    "   - 长短期记忆 = long short-term memory (LSTM)\n"
    "   - 反向传播 = backpropagation\n"
    "   - 方程求解 = equation solving\n"
    "   - 函数优化 = function optimization\n"
    "6. For Chinese book titles or Chinese-only cultural references, keep the Chinese then add a parenthetical English gloss.\n"
    "7. Keep names of libraries, functions, parameters in English exactly as written.\n"
    "8. Keep URLs unchanged."
)


@dataclass
class CellJob:
    notebook: Path
    cell_index: int
    source: str
    custom_id: str = field(init=False)

    def __post_init__(self) -> None:
        self.custom_id = f"{self.notebook.as_posix()}#{self.cell_index}"


def iter_notebooks(chapter: str | None) -> Iterator[Path]:
    if chapter:
        base = REPO_ROOT / chapter
        if not base.exists():
            raise FileNotFoundError(base)
        yield from sorted(base.rglob("*.ipynb"))
    else:
        for ch in sorted(REPO_ROOT.glob("Chapter*")):
            yield from sorted(ch.rglob("*.ipynb"))


def collect_jobs(notebook: Path) -> tuple[nbformat.NotebookNode, list[CellJob]]:
    nb = nbformat.read(notebook, as_version=4)
    jobs: list[CellJob] = []
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "markdown":
            continue
        source: str = cell.source if isinstance(cell.source, str) else "".join(cell.source)
        if MARKER in source:
            continue
        if not source.strip():
            continue
        jobs.append(CellJob(notebook=notebook, cell_index=i, source=source))
    return nb, jobs


def build_batch_request(job: CellJob) -> dict:
    return {
        "custom_id": job.custom_id,
        "params": {
            "model": MODEL,
            "max_tokens": 2048,
            "system": [
                {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
            ],
            "messages": [
                {"role": "user", "content": job.source}
            ],
        },
    }


def extract_text(result_message: dict) -> str:
    parts = result_message.get("content", [])
    return "".join(b.get("text", "") for b in parts if b.get("type") == "text").strip()


def splice_translation(notebook_path: Path, out_path: Path, nb: nbformat.NotebookNode,
                       translations: dict[str, str]) -> int:
    spliced = 0
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "markdown":
            continue
        custom_id = f"{notebook_path.as_posix()}#{i}"
        if custom_id not in translations:
            continue
        english = translations[custom_id]
        if not english:
            continue
        original = cell.source if isinstance(cell.source, str) else "".join(cell.source)
        cell.source = f"{original}{SEP}{english}\n\n{MARKER}"
        spliced += 1
    if spliced:
        nbformat.write(nb, out_path)
    return spliced


def process_notebook(client: anthropic.Anthropic, notebook: Path, dry_run: bool) -> tuple[Path, int, int, str]:
    nb, jobs = collect_jobs(notebook)
    if not jobs:
        return notebook, 0, 0, "no-work"

    requests = [build_batch_request(j) for j in jobs]
    batch = client.messages.batches.create(requests=requests)

    # Poll until ended (cheap calls, small backoff)
    while True:
        refreshed = client.messages.batches.retrieve(batch.id)
        if refreshed.processing_status == "ended":
            break
        time.sleep(15)

    translations: dict[str, str] = {}
    for r in client.messages.batches.results(batch.id):
        if r.result.type == "succeeded":
            translations[r.custom_id] = extract_text(r.result.message.model_dump())
        else:
            translations[r.custom_id] = ""  # leave cell untranslated; safe to re-run

    out_path = notebook.with_suffix(".bilingual.ipynb") if dry_run else notebook
    spliced = splice_translation(notebook, out_path, nb, translations)
    return notebook, len(jobs), spliced, batch.id


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--chapter", help="single chapter directory name, e.g. Chapter01")
    group.add_argument("--all", action="store_true", help="process every chapter")
    parser.add_argument("--dry-run", action="store_true",
                        help="write *.bilingual.ipynb alongside the source instead of modifying in place")
    parser.add_argument("--jobs", type=int, default=4, help="parallel notebooks (default 4)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return sys.exit("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic()
    notebooks = list(iter_notebooks(None if args.all else args.chapter))
    if not notebooks:
        return sys.exit("no notebooks found")

    print(f"Bilingualizing {len(notebooks)} notebooks; dry_run={args.dry_run}")
    total_jobs = total_spliced = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(process_notebook, client, nb, args.dry_run): nb for nb in notebooks}
        for fut in as_completed(futures):
            nb, n_jobs, n_spliced, batch_id = fut.result()
            total_jobs += n_jobs
            total_spliced += n_spliced
            print(f"  [done] {nb.relative_to(REPO_ROOT).as_posix()}  jobs={n_jobs}  spliced={n_spliced}  batch={batch_id}")

    print(f"\nTOTAL: jobs={total_jobs}  cells spliced={total_spliced}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
