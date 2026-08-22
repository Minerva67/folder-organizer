# folder-organizer

A Claude skill for **organizing any messy folder** — desktops, Downloads, project drives, photo libraries, mixed dumps — by *understanding the contents first*, then deduping, classifying, and (optionally) renaming, all reversibly.

> 中文说明在下方 · [Chinese below](#中文说明)

It is not a "smarter rename tool." Its whole point is the step most tools skip: it **reads what each file actually is** (a file called `final` may be a draft; a `report.html` may be a login page) before it moves or renames anything — and it never hard-deletes.

---

## Why it exists

Two rules drive the whole method:

1. **Understand before touching.** Filenames lie. Classifying or renaming from names alone guarantees mis-filed, misleading results. So *reading the content* is a mandatory, separate phase.
2. **Everything is reversible.** Deletion only ever means "moved to a staging trash." Nothing is destroyed; you empty the staging folder yourself once you're sure.

And one rule throughout: **the taxonomy is discovered, not imposed.** The same pile of files might want to be organized by date, client, project, or type — the skill asks for the axis instead of hard-coding one.

## The method — 5 phases, each ending at a human checkpoint

| Phase | What it does | Script |
|---|---|---|
| **0 · Profile** | Size hotspots, file-type distribution, biggest files, date range | `scripts/scan.py` |
| **1 · Dedupe** | Content-level (md5) dedup → **A** exact duplicates, **B** version residue | `scripts/find_dupes.py` |
| **2 · Read content** | A per-type content signature for every file, degrading gracefully | `scripts/signatures.py` |
| **3 · Propose** | Ask the organizing *axis*, then propose a structure + mapping | — |
| **4 · Execute** | Move/categorize, optional content-driven renaming | `scripts/safe_stage.sh` |

The two things that make it general:

- **Pluggable content readers with graceful degradation** — office docs, HTML, PDF, images (EXIF), audio/video (ffprobe), code, archives each have a reader; anything unknown falls back to name + size + date. So it works on *any* folder, not just office documents.
- **The taxonomy is asked, not built in** — Phase 3 derives structure from the content and the user's chosen axis.

## What it deliberately does NOT do

- Hard-delete anything (staging only).
- Decide which *version* to keep for you (version residue is grouped, never auto-pruned).
- Restructure a **code repository** (that's an engineering task with build/dependency constraints).
- Rename files that have internal cross-references (skill packages, code, interlinked page sets) — those are moved but never renamed.

## Scripts

All are Python stdlib / POSIX shell, cross-platform, and **safe with CJK / spaces / special characters** in filenames.

- **`scan.py`** `<folder> [--top N]` — folder profile.
- **`find_dupes.py`** `<folder> [--json out.json]` — exact duplicates + version-residue candidates.
- **`signatures.py`** `<folder> [--ext .html,.xlsx] | --files a b` — per-file content signatures.
- **`safe_stage.sh`** `<root> <path...>` — move to a reversible `_待删_<date>/` staging trash.

Optional external tools make the readers stronger (all optional; absence just triggers fallback): `pdftotext` (poppler) for PDF text, `exiftool` for image EXIF, `ffprobe` (ffmpeg) for media. See [`references/readers.md`](references/readers.md).

## Hard-won safety rules (baked into `SKILL.md`)

- Stage instead of hard-delete; confirmation checkpoint before every destructive phase.
- Group version residue, never auto-delete a version.
- Flag sensitive files (IDs, contracts, bank info) instead of filing them into a work folder.
- Quote every path; iterate with `find -print0 | while IFS= read -r -d ''` — never `for f in $(...)`.
- `rm -f .DS_Store` before `rmdir` (it silently blocks empty-dir removal on macOS).
- Don't use bash associative arrays under zsh (`${!arr[@]}` → *bad substitution*).

## Install

Copy the `folder-organizer/` directory into your Claude skills directory (e.g. `~/.claude/skills/`). The skill triggers on requests like *"帮我整理这个文件夹 / clean up my desktop / declutter Downloads / 这堆文件归一下类 / 有一堆重复和版本残留"*.

---

## 中文说明

一个用于**整理任意乱文件夹**的 Claude skill（桌面 / Downloads / 项目盘 / 照片库 / 混合内容），核心是**先读懂内容再动手**，全程可逆。

它不是"更聪明的重命名工具"。它做了多数工具跳过的一步：**先真读每个文件是什么**（叫 `final` 的可能是草稿，`report.html` 可能是登录页）再归类/改名；且**从不硬删**。

**两条铁律**：① 先搞懂再动手（文件名会骗人）；② 一切可逆（删除=移进暂存夹，你自己清）。还有一条：**分类法是问出来的，不是内置的**。

**五阶段**（每阶段收在一个人工确认闸门）：画像 → 查重 → 读内容 → 给建议 → 执行。查重按 md5 内容分「完全重复 / 版本残留」；版本残留**只归拢不替你删**。

**通用性靠两点**：内容读取器可插拔且优雅退化（office/图片/音视频/代码/PDF 各有读法，读不了退回元数据）；分类法在阶段3现问现推。

详见 [`SKILL.md`](SKILL.md)。

## License

MIT
