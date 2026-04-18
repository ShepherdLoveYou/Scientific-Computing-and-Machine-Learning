"""Generate Welcome.ipynb — the HF Space landing notebook.

Takes the repo's README.md, strips Space-irrelevant sections, and splices
in a clickable 4-part chapter TOC (each English title links straight to
the chapter's primary notebook via a URL-encoded JupyterLab tree path).

Invoked by Dockerfile at image build time, before the app lockdown.
"""
from __future__ import annotations

import json
import pathlib
import re
import urllib.parse

APP_DIR = pathlib.Path(__file__).resolve().parent

# (chapter_num, primary_notebook_path_relative_to_repo_root, english_title, chinese_title)
Chapter = tuple[str, str, str, str]
PARTS: list[tuple[str, list[Chapter]]] = [
    (
        "Part 1 — 基础与编程 / Foundations & Programming",
        [
            ("01", "Chapter01/1. 科学计算.ipynb",            "Scientific Computing with Python",  "科学计算和 Python"),
            ("02", "Chapter02/1. Numpy数组操作.ipynb",       "Numerical Computing with NumPy",    "数值计算和 NumPy"),
            ("03", "Chapter03/1. SymPy符号计算.ipynb",       "Symbolic Computation with SymPy",   "符号计算和 SymPy"),
            ("04", "Chapter04/1. Matplotlib和数据可视化.ipynb", "Data Visualization with Matplotlib", "数据可视化和 Matplotlib"),
        ],
    ),
    (
        "Part 2 — 数值方法 / Numerical Methods",
        [
            ("05", "Chapter05/1. 方程求解.ipynb",            "Equation Solving and Function Optimization", "方程求解和函数优化"),
            ("06", "Chapter06/1. 数据插值.ipynb",            "Interpolation and Numerical Integration",    "数据插值和数值积分"),
            ("07", "Chapter07/1. 常微分方程.ipynb",          "Differential Equations and FEM",             "微分方程和有限元方法"),
            ("08", "Chapter08/1. 随机过程和等概率原理.ipynb", "Stochastic Processes and Monte Carlo",       "随机过程和蒙特卡罗方法"),
        ],
    ),
    (
        "Part 3 — 科学应用 / Scientific Applications",
        [
            ("09", "Chapter09/1. 数值求解薛定谔方程.ipynb",  "Molecular Dynamics and DFT",              "分子动力学和密度泛函理论"),
            ("10", "Chapter10/1. 数据处理和Pandas库.ipynb",  "Data Analysis and Statistical Modeling",  "数据分析和统计建模"),
            ("11", "Chapter11/1. 机器学习.ipynb",            "Machine Learning with scikit-learn",      "机器学习和 scikit-learn"),
        ],
    ),
    (
        "Part 4 — 深度学习 / Deep Learning",
        [
            ("14", "Chapter14/通用近似器.ipynb",              "Multilayer Perceptrons (from scratch)", "多层感知机（通用近似器）"),
            ("15", "Chapter15/AssessmentTask.ipynb",         "CNN and LSTM (assessment task)",  "卷积神经网络和长短期记忆网络"),
        ],
    ),
]

SPACE_NOTE = """\
> 👋 你正在 Hugging Face Space 的 JupyterLab 里浏览本教程。点击下方任何章节的英文标题即可在新 tab 中打开对应 notebook，Shift+Enter 执行 cell。
>
> You're viewing this tutorial inside the Hugging Face Space's JupyterLab. Click any chapter's English title below to open it in a new tab, and run cells with Shift+Enter.
"""

INTRO = """\
# 科学计算和机器学习 / Scientific Computing and Machine Learning

面向有基础编程经验、但未接触过高性能计算或机器学习的研究生的 64 学时课程。

A 64-hour course for graduate students with basic programming experience but no prior exposure to high-performance computing or machine learning.

<!-- bilingual:en -->
"""


def encode_notebook_path(path: str) -> str:
    """URL-encode a notebook path relative to repo root so JupyterLab's
    `/lab/tree/...` URL resolves correctly for Chinese-named files."""
    return urllib.parse.quote(path, safe="/")


def build_clickable_tables() -> str:
    """Emit four Part tables, each English title linked to its chapter notebook."""
    lines: list[str] = [
        "## 目录 / Contents",
        "",
        "点击任一章节的英文标题，在新 tab 中打开对应 notebook。",
        "",
        "Click any chapter's English title to open that notebook in a new tab.",
        "",
    ]
    for part_title, chapters in PARTS:
        lines.append(f"### {part_title}")
        lines.append("")
        lines.append("| # | Chapter / 章节 | 中文标题 |")
        lines.append("|---|---|---|")
        for num, nb_path, en_title, zh_title in chapters:
            href = encode_notebook_path(nb_path)
            lines.append(f"| {num} | [{en_title}]({href}) | {zh_title} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_welcome_markdown() -> str:
    """Assemble the full welcome markdown body."""
    parts = [
        INTRO.rstrip(),
        "",
        SPACE_NOTE.rstrip(),
        "",
        build_clickable_tables(),
        "---",
        "",
        "## 参考书目 / Reference Books",
        "",
        "- 《Python 科学计算和数据科学应用 — Numerical Python》",
        "- 《动手学深度学习 — Dive into Deep Learning》",
        "",
        "## 项目仓库 / Project Repository",
        "",
        "完整 README、贡献指南、部署说明见仓库 `README.md`。",
        "",
        "See the repo's `README.md` for the full README, contribution guide, and deployment notes.",
        "",
        "<!-- bilingual -->",
    ]
    return "\n".join(parts)


def build_notebook(body: str) -> dict:
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "id": "welcome",
                "metadata": {},
                "source": body,
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    body = build_welcome_markdown()
    nb = build_notebook(body)
    out = APP_DIR / "Welcome.ipynb"
    out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
