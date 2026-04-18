"""Restore every chapter notebook from its `.ipynb.bak` sibling, re-apply the
cached translations under `tmp_trans/`, then run `reformat_bilingual` on the
result. Useful after improving the reformat logic mid-flight.

This is a one-shot batch helper; not part of the normal bilingualization flow.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TMP = REPO_ROOT / "tmp_trans"
PY = sys.executable


CHAPTER_NB_TO_TRANS: dict[str, str] = {
    # Chapter01
    "Chapter01/1. 科学计算.ipynb": "ch01_nb1_trans.json",
    "Chapter01/2. Python语言.ipynb": "ch01_nb2_trans.json",
    "Chapter01/3. Python高级功能.ipynb": "ch01_nb3_trans.json",
    "Chapter01/4. Jupyter.ipynb": "ch01_nb4_trans.json",
    # Chapter02
    "Chapter02/1. Numpy数组操作.ipynb": "ch02_nb1_trans.json",
    "Chapter02/2. Scipy高级科学计算.ipynb": "ch02_nb2_trans.json",
    "Chapter02/3. Julia语言.ipynb": "ch02_nb3_trans.json",
    # Chapter03
    "Chapter03/1. SymPy符号计算.ipynb": "ch03_nb1_trans.json",
    "Chapter03/2. Wolfram语言.ipynb": "ch03_nb2_trans.json",
    # Chapter04
    "Chapter04/1. Matplotlib和数据可视化.ipynb": "ch04_nb1_trans.json",
    "Chapter04/2. 数据可视化Python库.ipynb": "ch04_nb2_trans.json",
    # Chapter05
    "Chapter05/1. 方程求解.ipynb": "ch05_nb1_trans.json",
    "Chapter05/2. 函数优化.ipynb": "ch05_nb2_trans.json",
    "Chapter05/3. 微动弹性带方法.ipynb": "ch05_nb3_trans.json",
    "Chapter05/AssessmentTask.ipynb": "ch05_at_trans.json",
    # Chapter06
    "Chapter06/1. 数据插值.ipynb": "ch06_nb1_trans.json",
    "Chapter06/2. 数值积分.ipynb": "ch06_nb2_trans.json",
    # Chapter07
    "Chapter07/1. 常微分方程.ipynb": "ch07_nb1_trans.json",
    "Chapter07/2. 稀疏矩阵.ipynb": "ch07_nb2_trans.json",
    "Chapter07/3. 偏微分方程.ipynb": "ch07_nb3_trans.json",
    "Chapter07/4. 有限元方法和FEniCSx计算框架.ipynb": "ch07_nb4_trans.json",
    "Chapter07/AssessmentTask.ipynb": "ch07_at_trans.json",
    # Chapter08
    "Chapter08/1. 随机过程和等概率原理.ipynb": "ch08_nb1_trans.json",
    "Chapter08/2. 蒙特卡罗方法.ipynb": "ch08_nb2_trans.json",
    # Chapter09
    "Chapter09/1. 数值求解薛定谔方程.ipynb": "ch09_nb1_trans.json",
    "Chapter09/2. 密度泛函理论.ipynb": "ch09_nb2_trans.json",
    "Chapter09/3. 分子热运动和数值模拟.ipynb": "ch09_nb3_trans.json",
    "Chapter09/4. 分子动力学模拟.ipynb": "ch09_nb4_trans.json",
    "Chapter09/HydrogenWaveFunction/HydrogenWaveFunction.ipynb": "ch09_nb5_trans.json",
    # Chapter10
    "Chapter10/1. 数据处理和Pandas库.ipynb": "ch10_nb1_trans.json",
    "Chapter10/2. 统计和建模.ipynb": "ch10_nb2_trans.json",
    # Chapter11
    "Chapter11/1. 机器学习.ipynb": "ch11_nb1_trans.json",
    "Chapter11/2. 机器学习算法.ipynb": "ch11_nb2_trans.json",

    # Chapter14
    "Chapter14/chapter.ipynb": "ch14_nb1_trans.json",
    "Chapter14/通用近似器.ipynb": "ch14_nb2_trans.json",
    # Chapter15
    "Chapter15/AssessmentTask.ipynb": "ch15_nb1_trans.json",
}


def find_trans_json(nb_rel: str) -> Path | None:
    """Find a translation JSON for this notebook. Falls back to any file whose
    name starts with the chapter prefix and contains a notebook number, since
    each sub-agent chose its own naming scheme."""
    explicit = TMP / CHAPTER_NB_TO_TRANS.get(nb_rel, "")
    if explicit.exists():
        return explicit
    # heuristic scan
    stem = Path(nb_rel).stem.lower()
    chapter_num = Path(nb_rel).parts[0].replace("Chapter", "").lstrip("0") or "0"
    candidates = [
        p for p in TMP.glob("*.json")
        if p.name.endswith("_trans.json")
        and f"ch{int(chapter_num):02d}" in p.name.lower()
    ]
    if not candidates:
        return None
    # If only one, take it. Otherwise, pick by nb index match if present.
    if len(candidates) == 1:
        return candidates[0]
    # try matching notebook order: "1." -> nb1, "2." -> nb2, "AssessmentTask" -> at
    nb_name = Path(nb_rel).name.lower()
    hint = "at" if "assessment" in nb_name else nb_name.split(".")[0]
    best = [p for p in candidates if f"nb{hint}" in p.name.lower() or f"_{hint}_" in p.name.lower()]
    return best[0] if best else candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="actually restore/reapply/reformat")
    args = parser.parse_args()

    done = skipped = failed = 0
    for nb_rel in CHAPTER_NB_TO_TRANS:
        nb = REPO_ROOT / nb_rel
        bak = nb.with_suffix(nb.suffix + ".bak")
        if not bak.exists():
            print(f"  [skip] {nb_rel}  (no .bak)")
            skipped += 1
            continue
        trans = find_trans_json(nb_rel)
        if trans is None:
            print(f"  [skip] {nb_rel}  (no tmp_trans match)")
            skipped += 1
            continue
        if not args.apply:
            print(f"  [plan] {nb_rel}  <- {trans.name}")
            continue
        try:
            shutil.copy(bak, nb)
            subprocess.run(
                [PY, "tools/dialog_bilingual.py", "apply", nb_rel, str(trans.relative_to(REPO_ROOT))],
                cwd=REPO_ROOT, check=True, capture_output=True,
                env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
            )
            subprocess.run(
                [PY, "tools/reformat_bilingual.py", "--notebook", nb_rel, "--apply"],
                cwd=REPO_ROOT, check=True, capture_output=True,
                env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
            )
            print(f"  [ok]   {nb_rel}")
            done += 1
        except subprocess.CalledProcessError as exc:
            print(f"  [FAIL] {nb_rel}  :: {exc.stderr.decode(errors='replace')[:200]}")
            failed += 1

    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"\n{mode}: ok={done}  skipped={skipped}  failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
