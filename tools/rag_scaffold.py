"""Index the reference textbook PDFs in ReferenceBooks/ and expose a per-SCML-chapter
lookup that returns 1-3 textbook excerpts relevant to that chapter's topic.

Used by tools/scaffold.py to ground LLM skeleton generation in textbook content
rather than free-form hallucination. Deliberately keyword-based (no embedding
dependency) because the set of topics is small and the keyword heuristic is
auditable.

Two reference books:
  * Numerical Python (Johansson) -> covers Chapter01..12 of SCML
  * Dive into Deep Learning -> covers Chapter13..16 of SCML

Run directly to dump the built index as JSON:
    python tools/rag_scaffold.py --dump
    python tools/rag_scaffold.py --query Chapter12
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
REFBOOKS = REPO_ROOT / "ReferenceBooks"

# Per-chapter keyword bags. Matches (a) Chinese chapter titles and
# (b) English textbook section titles. Keyword match on extracted PDF text
# returns the matching page(s) plus ~400 chars of context.
CHAPTER_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "Chapter01": {"book": "numerical-python", "kw": ["scientific computing", "python basics", "jupyter", "introduction"]},
    "Chapter02": {"book": "numerical-python", "kw": ["numpy", "scipy", "array", "vectorization"]},
    "Chapter03": {"book": "numerical-python", "kw": ["sympy", "symbolic", "computer algebra"]},
    "Chapter04": {"book": "numerical-python", "kw": ["matplotlib", "visualization", "plotting"]},
    "Chapter05": {"book": "numerical-python", "kw": ["optimization", "root finding", "equation solving", "minimization"]},
    "Chapter06": {"book": "numerical-python", "kw": ["interpolation", "integration", "quadrature"]},
    "Chapter07": {"book": "numerical-python", "kw": ["ordinary differential", "partial differential", "ode", "pde", "finite element"]},
    "Chapter08": {"book": "numerical-python", "kw": ["monte carlo", "random", "stochastic", "sampling"]},
    "Chapter09": {"book": "numerical-python", "kw": ["molecular dynamics", "schrödinger", "density functional"]},
    "Chapter10": {"book": "numerical-python", "kw": ["pandas", "data frame", "statistics", "regression"]},
    "Chapter11": {"book": "numerical-python", "kw": ["scikit-learn", "machine learning", "classification", "regression"]},
    "Chapter12": {"book": "numerical-python", "kw": ["bayesian", "markov chain", "mcmc", "pymc"]},
    "Chapter13": {"book": "dive-into-deep-learning", "kw": ["deep learning", "neural network", "preliminaries"]},
    "Chapter14": {"book": "dive-into-deep-learning", "kw": ["multilayer perceptron", "mlp", "backpropagation"]},
    "Chapter15": {"book": "dive-into-deep-learning", "kw": ["convolutional neural network", "cnn", "lstm", "recurrent"]},
    "Chapter16": {"book": "dive-into-deep-learning", "kw": ["molecular", "physics", "simulation", "deep learning applications"]},
}

BOOK_FILENAMES = {
    "numerical-python": "Numerical Python.pdf",
    "dive-into-deep-learning": "Dive into Deep Learning.pdf",
}


@dataclass
class Excerpt:
    book: str
    page: int
    text: str

    def to_dict(self) -> dict:
        return {"book": self.book, "page": self.page, "text": self.text}


def load_pdf_pages(pdf_path: Path) -> list[str]:
    """Return a list of page texts. Uses pypdf if available, else raises."""
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("pypdf not installed. Run: pip install pypdf")

    reader = PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]


def find_excerpts(pages: list[str], keywords: list[str], max_excerpts: int = 3,
                  context_chars: int = 400) -> list[Excerpt]:
    """Locate up to `max_excerpts` keyword hits; return surrounding context."""
    pattern = re.compile("|".join(re.escape(k) for k in keywords), re.IGNORECASE)
    hits: list[Excerpt] = []
    seen_pages: set[int] = set()
    for page_idx, text in enumerate(pages):
        if page_idx in seen_pages:
            continue
        m = pattern.search(text)
        if not m:
            continue
        start = max(0, m.start() - context_chars // 2)
        end = min(len(text), m.end() + context_chars // 2)
        snippet = text[start:end].replace("\n", " ").strip()
        hits.append(Excerpt(book="", page=page_idx + 1, text=snippet))
        seen_pages.add(page_idx)
        if len(hits) >= max_excerpts:
            break
    return hits


def build_index(chapters: Iterable[str]) -> dict[str, list[Excerpt]]:
    cache_pdf: dict[str, list[str]] = {}
    index: dict[str, list[Excerpt]] = {}
    for chapter in chapters:
        if chapter not in CHAPTER_KEYWORDS:
            continue
        spec = CHAPTER_KEYWORDS[chapter]
        book = spec["book"]
        pdf_name = BOOK_FILENAMES[book]
        pdf_path = REFBOOKS / pdf_name
        if not pdf_path.exists():
            index[chapter] = []
            continue
        if book not in cache_pdf:
            cache_pdf[book] = load_pdf_pages(pdf_path)
        excerpts = find_excerpts(cache_pdf[book], spec["kw"])
        for e in excerpts:
            e.book = pdf_name
        index[chapter] = excerpts
    return index


def excerpts_for(chapter: str) -> list[Excerpt]:
    """Public API used by scaffold.py."""
    return build_index([chapter]).get(chapter, [])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump", action="store_true", help="dump full index for all chapters")
    parser.add_argument("--query", help="single chapter name, e.g. Chapter12")
    args = parser.parse_args()

    chapters = list(CHAPTER_KEYWORDS) if args.dump else [args.query] if args.query else []
    if not chapters:
        return sys.exit("--dump or --query required")

    index = build_index(chapters)
    print(json.dumps({k: [e.to_dict() for e in v] for k, v in index.items()}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
