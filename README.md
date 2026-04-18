# 科学计算和机器学习 / Scientific Computing and Machine Learning

<!-- HF_SPACE: jingjiang233/Scientific-Computing-and-Machine-Learning -->

面向有基础编程经验、但未接触过高性能计算或机器学习的研究生的 64 学时课程。

---

A 64-hour course for graduate students with basic programming experience but no prior exposure to high-performance computing or machine learning.

<!-- bilingual:en -->

## 目录 / Contents

| # | 中文标题 | English title | Entry |
|---|---|---|---|
| 01 | 科学计算和 Python | Scientific Computing and Python | [Chapter01/](Chapter01/) |
| 02 | 数值计算和 NumPy | Numerical Computing with NumPy | [Chapter02/](Chapter02/) |
| 03 | 符号计算和 SymPy | Symbolic Computation with SymPy | [Chapter03/](Chapter03/) |
| 04 | 数据可视化和 Matplotlib | Data Visualization with Matplotlib | [Chapter04/](Chapter04/) |
| 05 | 方程求解和函数优化 | Equation Solving and Function Optimization | [Chapter05/](Chapter05/) |
| 06 | 数据插值和数值积分 | Interpolation and Numerical Integration | [Chapter06/](Chapter06/) |
| 07 | 微分方程和有限元方法 | Differential Equations and Finite Element Methods | [Chapter07/](Chapter07/) |
| 08 | 随机过程和蒙特卡罗方法 | Stochastic Processes and Monte Carlo | [Chapter08/](Chapter08/) |
| 09 | 分子动力学和密度泛函理论 | Molecular Dynamics and DFT | [Chapter09/](Chapter09/) |
| 10 | 数据分析和统计建模 | Data Analysis and Statistical Modeling | [Chapter10/](Chapter10/) |
| 11 | 机器学习和 scikit-learn | Machine Learning with scikit-learn | [Chapter11/](Chapter11/) |
| 14 | 多层感知机 | Multilayer Perceptrons | [Chapter14/](Chapter14/) |
| 15 | 卷积神经网络和长短期记忆网络 | CNN and LSTM | [Chapter15/](Chapter15/) |

## 参考书目 / Reference Books

- [《Python 科学计算和数据科学应用 — Numerical Python》](http://product.dangdang.com/28974447.html)
- [《动手学深度学习 — Dive into Deep Learning》](https://item.jd.com/47908427478.html)

---

## 快速开始 / Quick Start

### 方式 A：本地 conda 环境（推荐）/ Local conda environment (recommended)

本项目约定：本地虚拟环境安装在 `D:\Conda\envs\scml`（Windows）或 `$HOME/envs/scml`（Linux/macOS）。

The project convention installs the local virtual environment at `D:\Conda\envs\scml` (Windows) or `$HOME/envs/scml` (Linux/macOS).

<!-- bilingual:en -->

```powershell
# Windows PowerShell
./scripts/setup-env.ps1
conda activate D:\Conda\envs\scml
$env:KERAS_BACKEND = "torch"
jupyter lab
```

```bash
# Linux / macOS / WSL
./scripts/setup-env.sh
conda activate $HOME/envs/scml
export KERAS_BACKEND=torch
jupyter lab
```

### 方式 B：Docker（与 Hugging Face Space 一致）/ Docker (matches the HF Space)

```bash
docker build -t scml .
docker run --rm -p 7860:7860 scml
# open http://localhost:7860
```

### 方式 C：pip-only（精简依赖，不含 FEniCSx / LAMMPS）/ pip-only (no FEniCSx / LAMMPS)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

## 测试 / Testing

批量执行全部章节：/ Batch-execute every chapter:

```bash
python _test_notebooks.py
# PASS: 39  FAIL: 0  TIMEOUT: 0  SKIP: 1  TOTAL: 40
```

仅跑单章：/ Run a single chapter:

```bash
python _test_notebooks.py --only Chapter08
```

Wolfram 章节（`Chapter03/2. Wolfram语言.ipynb`）需要 Wolfram Engine license，CI 中默认 SKIP；运行时由 `tools/skip_notebooks.txt` 管理。该章已额外提供 SymPy 并列可运行版本。

The Wolfram notebook requires a Wolfram Engine license and is skipped by default in CI (see `tools/skip_notebooks.txt`). A SymPy parallel runnable version is provided alongside.

<!-- bilingual:en -->

## 部署到 Hugging Face Space / Deploy to Hugging Face Space

1. 在 https://huggingface.co/spaces/new 创建一个 Docker Space（例如 `yourname/scml`）。
2. 生成一个 fine-grained HF token（仅限该 Space 的 write 权限）。
3. 在 GitHub repo **Settings → Secrets → Actions** 添加 `HF_TOKEN` secret。
4. 将本 README 顶部的 `<!-- HF_SPACE: ... -->` 注释取消注释并填入你的 Space 路径。
5. Push 到 `main` 分支；`.github/workflows/sync-to-hf.yml` 自动同步。

1. Create a Docker Space at https://huggingface.co/spaces/new (e.g. `yourname/scml`).
2. Generate a fine-grained HF token with write scope limited to that Space.
3. Add an `HF_TOKEN` secret under **Settings → Secrets → Actions** in the GitHub repo.
4. Uncomment the `<!-- HF_SPACE: ... -->` marker at the top of this README and fill in your Space path.
5. Push to `main`; `.github/workflows/sync-to-hf.yml` auto-mirrors.

<!-- bilingual:en -->

## 项目结构 / Project Layout

```
Chapter01..16/        # 课程笔记本（每章 1-5 个 .ipynb）/ course notebooks
ReferenceBooks/       # 教材 PDF（本地用；Docker 构建时被 .dockerignore 排除）
                      # reference textbooks (local only; excluded from Docker)
tools/                # 双语化 / 骨架生成 / RAG 索引 / skip list
scripts/              # 本地环境搭建 + 验证脚本 / env setup + verify
.github/workflows/    # nbconvert 测试 + HF Space 同步 / test + sync workflows
Dockerfile            # python:3.11-slim + Julia + FEniCSx + LAMMPS + PyTorch
environment.yml       # conda-forge 等价环境（本地 D 盘 conda）/ conda-forge env
requirements.txt      # pip-only 精简路径 / pip-only slim path
_test_notebooks.py    # nbclient 批量执行器 / batch executor
_inventory.csv        # 每本 notebook 的运行时策略 / per-notebook runtime policy
```

## 上游与许可 / Upstream and License

本仓库基于已停更的上游 [sim42/SCML](https://github.com/sim42/SCML)（最后一次提交 2022-06-18，CC0 1.0 许可）。现代化工作（依赖更新、双语化、HF Space 部署）在本 fork 中完成。

This repository is based on the archived upstream [sim42/SCML](https://github.com/sim42/SCML) (last commit 2022-06-18, CC0 1.0 license). Modernization work (dependency update, bilingualization, HF Space deployment) happens in this fork.

<!-- bilingual:en -->
