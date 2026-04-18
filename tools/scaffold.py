"""Generate bilingual skeleton content for the 9 sparse SCML notebooks, grounded
in textbook excerpts via tools/rag_scaffold.py.

Never claims to "complete" a chapter. Every inserted markdown cell starts with
    > ⚠️ **Skeleton / 骨架** — based on <book> p.<page>; author review required
and every inserted code cell ends with a
    # TODO: author review
comment.

Targets the 9 sparse notebooks identified in _inventory.csv:
    Chapter01/1. 科学计算.ipynb          (3 cells)
    Chapter03/2. Wolfram语言.ipynb       (9; dual-track Wolfram+SymPy)
    Chapter04/2. 数据可视化Python库.ipynb (16)
    Chapter05/AssessmentTask.ipynb       (8)
    Chapter07/4. 有限元方法和FEniCSx计算框架.ipynb (13)
    Chapter07/AssessmentTask.ipynb       (8)
    Chapter10/2. 统计和建模.ipynb         (7)
    Chapter11/1. 机器学习.ipynb           (3)
    Chapter12/贝叶斯统计.ipynb            (14)

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python tools/scaffold.py --dry-run               # write .scaffold.ipynb
    python tools/scaffold.py --notebook Chapter12/贝叶斯统计.ipynb
    python tools/scaffold.py --all                   # all 9 targets in place
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import nbformat

try:
    import anthropic
except ImportError:
    sys.exit("anthropic SDK not installed. Run: pip install anthropic")

from rag_scaffold import excerpts_for  # sibling module in tools/

REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL = "claude-sonnet-4-6"  # per user preference (see memory: feedback_translation_model)

SPARSE_TARGETS: dict[str, dict] = {
    "Chapter01/1. 科学计算.ipynb": {"chapter_key": "Chapter01", "topic_cn": "科学计算概述", "topic_en": "Overview of scientific computing"},
    "Chapter03/2. Wolfram语言.ipynb": {"chapter_key": "Chapter03", "topic_cn": "Wolfram 语言（展示）+ SymPy 可运行并列", "topic_en": "Wolfram language display + SymPy runnable equivalent", "dual_track": True},
    "Chapter04/2. 数据可视化Python库.ipynb": {"chapter_key": "Chapter04", "topic_cn": "Python 可视化库巡礼（bqplot/k3d/plotly）", "topic_en": "Tour of Python visualization libraries"},
    "Chapter05/AssessmentTask.ipynb": {"chapter_key": "Chapter05", "topic_cn": "方程求解与函数优化评估题", "topic_en": "Assessment task: equation solving and function optimization"},
    "Chapter07/4. 有限元方法和FEniCSx计算框架.ipynb": {"chapter_key": "Chapter07", "topic_cn": "有限元方法与 FEniCSx 框架入门", "topic_en": "Finite element method and FEniCSx framework intro"},
    "Chapter07/AssessmentTask.ipynb": {"chapter_key": "Chapter07", "topic_cn": "微分方程评估题", "topic_en": "Assessment task: differential equations"},
    "Chapter10/2. 统计和建模.ipynb": {"chapter_key": "Chapter10", "topic_cn": "统计建模与 statsmodels", "topic_en": "Statistical modeling with statsmodels"},
    "Chapter11/1. 机器学习.ipynb": {"chapter_key": "Chapter11", "topic_cn": "机器学习概述", "topic_en": "Machine learning overview"},
    "Chapter12/贝叶斯统计.ipynb": {"chapter_key": "Chapter12", "topic_cn": "贝叶斯统计与 PyMC 入门", "topic_en": "Bayesian statistics with PyMC"},
}

SYSTEM_PROMPT = (
    "You are writing skeleton teaching content for a Chinese/English bilingual Jupyter notebook "
    "in a graduate-level scientific computing and machine learning course. The notebook is sparse "
    "and needs structure. Generate concise, correct, textbook-grounded scaffold cells. Rules:\n"
    "1. Output a JSON array of cell objects. Each cell: {\"type\": \"markdown\"|\"code\", \"source\": \"...\"}.\n"
    "2. First markdown cell must be a bilingual chapter intro (## heading in both CN and EN).\n"
    "3. Every markdown cell MUST start with this callout on its own first line:\n"
    "   > ⚠️ **Skeleton / 骨架** — based on <book-name> p.<page>; author review required\n"
    "4. Every code cell MUST end with this comment on its own line:\n"
    "   # TODO: author review\n"
    "5. Keep code short and executable against the SCML env (numpy, scipy, sympy, torch+keras, "
    "   statsmodels, pymc if available, fenicsx for FEM). No network calls, no GPU.\n"
    "6. Both Chinese and English explanations appear in the same markdown cell, separated by `---`.\n"
    "7. End each markdown cell with the idempotency marker `<!-- bilingual:en -->`.\n"
    "8. 2-3 markdown overview cells + 1-2 example code cells is typical. DO NOT pad.\n"
    "9. If the chapter is dual-track (Wolfram+SymPy), show both syntaxes side by side: "
    "Wolfram in a fenced ```mathematica``` block inside markdown, SymPy in an executable code cell.\n"
    "10. Return raw JSON only. No markdown fencing around the JSON."
)


def build_context_block(chapter_key: str) -> str:
    excerpts = excerpts_for(chapter_key)
    if not excerpts:
        return "(no textbook excerpt found; rely on chapter title alone)"
    parts = []
    for e in excerpts:
        parts.append(f"[{e.book} p.{e.page}]\n{e.text}")
    return "\n\n".join(parts)


def generate_cells(client: anthropic.Anthropic, rel_path: str, spec: dict) -> list[dict]:
    context_block = build_context_block(spec["chapter_key"])
    dual = spec.get("dual_track", False)
    user_prompt = (
        f"Target notebook: {rel_path}\n"
        f"Chapter topic (Chinese): {spec['topic_cn']}\n"
        f"Chapter topic (English): {spec['topic_en']}\n"
        f"Dual-track Wolfram+SymPy required: {dual}\n\n"
        f"Textbook excerpts to ground your content:\n{context_block}\n\n"
        "Return the JSON array of scaffold cells."
    )

    resp = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = "".join(b.text for b in resp.content if b.type == "text").strip()
    import json
    try:
        cells = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"model returned non-JSON: {raw[:200]}") from exc
    if not isinstance(cells, list):
        raise RuntimeError("model did not return a JSON array")
    return cells


def insert_into_notebook(notebook_path: Path, new_cells: list[dict], out_path: Path) -> int:
    nb = nbformat.read(notebook_path, as_version=4)
    inserted = 0
    for c in new_cells:
        ctype = c.get("type")
        source = c.get("source", "")
        if not source.strip():
            continue
        if ctype == "markdown":
            cell = nbformat.v4.new_markdown_cell(source)
        elif ctype == "code":
            cell = nbformat.v4.new_code_cell(source)
        else:
            continue
        nb.cells.append(cell)
        inserted += 1
    nbformat.write(nb, out_path)
    return inserted


def process_one(client: anthropic.Anthropic, rel_path: str, dry_run: bool) -> tuple[str, int]:
    spec = SPARSE_TARGETS[rel_path]
    nb_path = REPO_ROOT / rel_path
    if not nb_path.exists():
        return rel_path, 0
    cells = generate_cells(client, rel_path, spec)
    out = nb_path.with_suffix(".scaffold.ipynb") if dry_run else nb_path
    n = insert_into_notebook(nb_path, cells, out)
    return rel_path, n


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--notebook", help="one target from the sparse list (relative path)")
    group.add_argument("--all", action="store_true", help="process all 9 sparse targets")
    parser.add_argument("--dry-run", action="store_true",
                        help="write *.scaffold.ipynb alongside instead of modifying in place")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return sys.exit("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic()

    if args.notebook:
        if args.notebook not in SPARSE_TARGETS:
            return sys.exit(f"{args.notebook} is not in the sparse-target list. "
                            f"Known: {list(SPARSE_TARGETS)}")
        targets = [args.notebook]
    else:
        targets = list(SPARSE_TARGETS)

    print(f"Scaffolding {len(targets)} sparse notebook(s); dry_run={args.dry_run}")
    for rel in targets:
        try:
            path, n = process_one(client, rel, args.dry_run)
            print(f"  [ok]   {path}  +{n} cells")
        except Exception as exc:
            print(f"  [fail] {rel}  :: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
