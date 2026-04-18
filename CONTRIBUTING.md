# 贡献指南 / Contributing

欢迎对本课程提交改进。本文档简要说明贡献流程与双语内容约定。

We welcome contributions to this course. This document briefly explains the contribution workflow and bilingual content conventions.

---

## 本地开发 / Local Development

Windows 用户（项目约定）/ Windows (project convention):

```powershell
./scripts/setup-env.ps1
conda activate D:\Conda\envs\scml
python scripts/verify-env.py
```

Linux / macOS / WSL:

```bash
./scripts/setup-env.sh
conda activate "$HOME/envs/scml"
python scripts/verify-env.py
```

Docker（与 HF Space 一致 / matches the HF Space):

```bash
docker build -t scml:slim .
docker run --rm -p 7860:7860 scml:slim
```

---

## 测试 / Testing

提 PR 前请在本地跑完整 nbconvert：/ Before opening a PR, run the full nbconvert sweep locally:

```bash
python _test_notebooks.py --timeout 300
```

目标：`FAIL: 0`。SKIP 列表见 [`tools/skip_notebooks.txt`](tools/skip_notebooks.txt)（含每条条目为何被跳过的注释）。

Target: `FAIL: 0`. The skip list is in [`tools/skip_notebooks.txt`](tools/skip_notebooks.txt) with a comment for each entry explaining why.

---

## 双语内容约定 / Bilingual Content Convention

markdown cell 必须中英双语，格式：/ Markdown cells must be bilingual, in this format:

```
# 标题 / Title

中文段落。

English paragraph.

<!-- bilingual -->
```

- 同级标题合并成 `## 中文 / English`
- 每 cell 结尾加 `<!-- bilingual -->` 作幂等标记
- LaTeX、代码块、链接原样保留
- 段落级交替，不整段 CN-then-EN

- Merge same-level headings into `## CN / English`
- End each cell with `<!-- bilingual -->` as an idempotency marker
- Preserve LaTeX, code fences, and links verbatim
- Interleave at paragraph level, not one CN block followed by one EN block

工具：/ Tooling:

- `tools/dialog_bilingual.py dump / apply` — 抽取 / 回写翻译
- `tools/reformat_bilingual.py` — 把"整段追加"格式转成"段落交替"格式

---

## 新章节 / New Chapter

若要新增章节（如 `ChapterNN/…`）：/ When adding a chapter (e.g. `ChapterNN/…`):

1. 按 `ChapterNN/...ipynb` 路径放 notebook
2. 更新 `README.md` 顶部的目录表
3. 更新 `_inventory.csv` 加一行
4. 更新 `_generate_welcome.py` 里的 `PARTS` 把章节加到合适分组
5. 本地跑 `_test_notebooks.py` 确认 PASS

1. Place notebook at `ChapterNN/...ipynb`
2. Update the TOC table at the top of `README.md`
3. Add a row to `_inventory.csv`
4. Add the chapter to the appropriate group in `PARTS` inside `_generate_welcome.py`
5. Run `_test_notebooks.py` locally to confirm PASS

---

## 部署到 Hugging Face Space / Deploying to Hugging Face Space

见 [`README.md`](README.md) 的 Deploy 章节。CI workflow `sync-to-hf.yml` 会读取 README 顶部的 `<!-- HF_SPACE: user/space -->` marker 自动同步。

See the Deploy section of [`README.md`](README.md). The `sync-to-hf.yml` workflow auto-mirrors to the Space path declared in the `<!-- HF_SPACE: user/space -->` marker at the top of the README.

---

## 许可 / License

本项目在 CC0 1.0 下发布（继承自上游 sim42/SCML）。提 PR 即视为同意你的贡献也以 CC0 释放。

This project is released under CC0 1.0 (inherited from the upstream sim42/SCML). Opening a PR is deemed consent to release your contribution under CC0 as well.
