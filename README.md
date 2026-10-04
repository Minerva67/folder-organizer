# folder-organizer

**A Claude skill that organizes any messy folder by reading what's inside — then dedupes, classifies, and renames, without ever hard-deleting.**

> 一个先读懂内容再动手的文件整理 skill · [中文说明](#中文)

Most "organizers" sort by filename. That's the problem — filenames lie. A file called `final` is often a draft; an `invoice.html` is often a login page; three `report_v2.xlsx` copies are often *not* the same file. `folder-organizer` opens each file, figures out what it actually is, and only then decides where it goes. Nothing is deleted — removals go to a staging trash you empty yourself.

---

## What it catches that a rename tool can't

- **Exact duplicates by content**, not name — the macOS `… 2.png` copies, the `(1)` re-downloads, the zip that's just a packed copy of files already sitting next to it.
- **Version residue** — `draft / v2 / final / 副本 / 20250807` chains — grouped for *you* to prune, never auto-deleted.
- **Mis-filed files** — a spreadsheet whose sheet names reveal it's a duplicate of another; an `.html` that's actually a marketing page, not a report.
- **Sensitive files loose in a work folder** — IDs, contracts, bank details — flagged to move out, not filed away.
- **The real space hogs** — one 500 MB export hiding among 200 documents.

## How it works — 5 phases, each ending at a checkpoint you approve

| Phase | Does | Script |
|------:|------|--------|
| **0 · Profile** | Size hotspots, type mix, biggest files, date span | `scan.py` |
| **1 · Dedupe** | md5 content dedup → **A** exact dups · **B** version residue | `find_dupes.py` |
| **2 · Read** | A content signature for every file, gracefully degrading | `signatures.py` |
| **3 · Propose** | Ask the *organizing axis*, propose a structure + mapping | — |
| **4 · Execute** | Move / categorize; optional content-driven rename | `safe_stage.sh` |

## In action

**Phase 0 — know the terrain before touching it:**

```
$ python3 scripts/scan.py ~/Downloads
# Folder profile  ~/Downloads
1,204 files · 8.3G  (23 hidden) · span 2023-04-11 → 2025-08-22

## Biggest subtrees            ## File types           ## Largest files
  4.1G  screen-recordings        4.1G   18  .mov         612M  demo-v3-FINAL.mov
  1.9G  design-exports           1.9G  340  .png         612M  demo-v3-FINAL 2.mov
  320M  (loose files)            210M  512  .pdf         …
```

**Phase 1 — redundancy, by content not name:**

```
$ python3 scripts/find_dupes.py ~/Downloads
## A · Exact duplicates (identical bytes)   reclaimable 1.2G
  [612M ×2]  save 612M
      screen-recordings/demo-v3-FINAL.mov
      screen-recordings/demo-v3-FINAL 2.mov      ← macOS copy, safe to drop

## B · Version residue (similar name, different bytes — you decide which to keep)
  reports/ · 3 versions:
      report.xlsx  ·  report-v2.xlsx  ·  report-final.xlsx
```

**Phase 2 — what each file *actually* is:**

```
$ python3 scripts/signatures.py ~/Downloads --ext .html,.xlsx
── invoice.html
   title:Sign in · h1:Welcome back              ← a login page, not an invoice
── Q3-numbers.xlsx
   sheets: Raw | Pivot | Summary-final          ← same sheets as Q3-copy.xlsx → likely a dup
── receipt.pdf
   first page: Booking confirmation #A83…       ← read via pdftotext
── IMG_4471.jpg
   EXIF: 2024-09-02 · iPhone 15 · 4032×3024     ← read via exiftool
```

Removals never destroy anything:

```
$ bash scripts/safe_stage.sh ~/Downloads "~/Downloads/demo-v3-FINAL 2.mov"
STAGED: demo-v3-FINAL 2.mov
staging: ~/Downloads/_待删_20250822   ·   612M
```

**Phases 3–4 — you pick the axis, it proposes the structure, you approve, then it moves:**

```
You:    organize ~/Desktop/client-work
Claude: [profile + dedupe + read]  86 files · 2 exact dups staged · 3 version chains found
        How should this be grouped?  ① by client  ② by project stage  ③ by date  ④ by file type
You:    by client, then by stage

Proposed structure (nothing moved yet):

  before                                after
  client-work/                          client-work/
  ├── acme_brief.pdf                    ├── Acme/
  ├── acme-contract-signed.pdf          │   ├── 1-brief/      acme_brief.pdf
  ├── Untitled.docx      ← Acme SOW     │   ├── 2-contract/   acme-contract-signed.pdf · Untitled.docx
  ├── deck_v2.key                       │   └── 3-delivery/   deck_v2.key · deck_final.key   (version chain, kept both)
  ├── deck_final.key                    ├── Northwind/
  ├── nw-invoice-0412.pdf               │   └── 4-billing/    nw-invoice-0412.pdf
  ├── passport-scan.jpg  ← sensitive    └── _flagged/         passport-scan.jpg  → suggest moving out of a work folder
  └── …

Approve, adjust, or rename the axis?
```

`Untitled.docx` lands under Acme because its first page names Acme, not because of its filename. The version chain is grouped, never pruned for you.

## Why it works on *any* folder (not just office docs)

- **Pluggable readers with graceful degradation.** Office files, HTML, PDF, images (EXIF), audio/video (ffprobe), code, archives each have a reader; anything unknown falls back to name + size + date. It never hard-fails on a format it doesn't know.
- **The taxonomy is discovered, not built in.** The same pile might want organizing by date, client, project, or type. Phase 3 asks for the axis instead of imposing one — so it fits a photographer's library and a lawyer's contracts equally.
- **Reversible by default.** Every deletion is a move to a dated staging folder. You are the only one who empties it.

## What it deliberately won't do

- Hard-delete anything.
- Pick which *version* to keep for you.
- Restructure a **code repository** (that's an engineering task with build/dependency constraints).
- Rename files with internal cross-references (skill packages, code, interlinked page sets) — those move, but keep their names.

## Install & trigger

The repo root *is* the skill folder, so one clone installs it:

```bash
git clone https://github.com/Minerva67/folder-organizer.git ~/.claude/skills/folder-organizer
```

No slash command needed. It triggers on requests like *"organize this folder / clean up my desktop / declutter Downloads / 帮我整理这个文件夹 / 这堆文件归一下类 / 有一堆重复和版本残留"*.

## Requirements

Scripts are Python stdlib + POSIX shell, cross-platform, and safe with CJK / spaces / special characters in filenames. Three optional tools make the content readers stronger — absence just triggers the fallback:

| Tool | Enables | Install |
|------|---------|---------|
| `pdftotext` (poppler) | PDF first-page text | `brew install poppler` |
| `exiftool` | image capture date / camera / GPS | `brew install exiftool` |
| `ffprobe` (ffmpeg) | audio/video duration + tags | `brew install ffmpeg` |

## Safety notes baked into the method

Stage instead of delete · confirm before every destructive step · group version residue rather than pruning it · flag sensitive files · quote every path and iterate with `find -print0` (never `for f in $(…)`) · `rm -f .DS_Store` before `rmdir` · avoid bash associative arrays under zsh.

---

<a name="中文"></a>
## 中文

一个**先读懂内容再动手**的文件整理 skill，适用于任意乱文件夹（桌面 / Downloads / 项目盘 / 照片库 / 混合内容），全程可逆。

多数整理工具按文件名排序——可文件名会骗人：叫 `final` 的常是草稿，`invoice.html` 可能是登录页，三个 `report_v2.xlsx` 未必是同一份。本 skill 会打开每个文件、判断它**真实是什么**，再决定去哪。删除只进暂存夹，由你自己清空。

**五阶段**（每阶段收在一个你确认的闸门）：画像 `scan.py` → 内容查重 `find_dupes.py` → 读内容 `signatures.py` → 问轴给建议 → 执行 `safe_stage.sh`。查重分「完全重复」和「版本残留」，版本残留只归拢、绝不替你删。

**为什么通用**：内容读取器可插拔且优雅退化（office/图片/音视频/代码/PDF 各有读法，读不了退回元数据）；分类法在阶段 3 现问现推，不内置——所以摄影师的素材库和律师的合同都能整。

详见 [`SKILL.md`](SKILL.md)。

## License

MIT
