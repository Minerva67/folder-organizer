#!/usr/bin/env python3
"""
signatures.py — Read what a file ACTUALLY IS, not what its name claims.

This is the heart of organizing any folder well: you cannot categorize or rename
honestly from filenames alone (a file called "final" may be a draft; "report.html"
may be a login page). For each file it emits a one-line content signature using a
reader chosen by type, and degrades gracefully to name+size+date when it can't
open the content (missing tool, unknown format).

Pluggable readers by family:
  text/code/md/csv/json  -> first meaningful lines / structure
  html                   -> <title> + first h1/h2 (the real subject)
  xlsx/docx/pptx         -> embedded titles + sheet/slide names (zip xml)
  pdf                    -> pdftotext first page, else /Title metadata
  images                 -> EXIF date+camera+dims via exiftool, else dims
  audio/video            -> ffprobe duration + tags, else size
  zip/archive            -> top entries
  fallback               -> "(binary) size · dates"

Usage:
    python3 signatures.py <folder> [--ext .html,.xlsx] [--max 400]
    python3 signatures.py --files a.pdf "b c.xlsx"

External tools are OPTIONAL; if absent that type falls back. Never hard-fails.
"""
import os, sys, re, html, zipfile, subprocess, argparse, shutil, time

def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return ""

def has(tool): return shutil.which(tool) is not None

def clean(s, n=200):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s[:n]

# ---------- readers ----------
def r_text(p):
    try: t = open(p, encoding="utf-8", errors="ignore").read(20000)
    except OSError: return ""
    heads = re.findall(r"^#{1,3}\s+(.+)$", t, re.M)          # markdown
    if heads: return "标题: " + " | ".join(clean(h,40) for h in heads[:4])
    lines = [l.strip() for l in t.splitlines() if l.strip()]
    return "首行: " + clean(" / ".join(lines[:3]), 180)

def r_html(p):
    try: t = open(p, encoding="utf-8", errors="ignore").read()
    except OSError: return ""
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", t, flags=re.S | re.I)
    def g(tag, n):
        return [clean(re.sub(r"<[^>]+>", " ", html.unescape(m)), 60)
                for m in re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", t, re.S | re.I)][:n]
    title = g("title", 1); h1 = g("h1", 1); h2 = g("h2", 4)
    parts = []
    if title: parts.append("title:" + title[0])
    if h1: parts.append("h1:" + h1[0])
    if h2: parts.append("节:" + " ".join(h2))
    return " · ".join(parts) or "(html 无标题)"

def r_office(p):
    ext = os.path.splitext(p)[1].lower()
    try: z = zipfile.ZipFile(p)
    except Exception: return ""
    names = z.namelist()
    out = []
    # document title from core properties
    if "docProps/core.xml" in names:
        core = z.read("docProps/core.xml").decode("utf-8", "ignore")
        m = re.search(r"<dc:title>(.*?)</dc:title>", core)
        if m and m.group(1).strip(): out.append("标题:" + clean(m.group(1), 40))
    if ext == ".xlsx" and "xl/workbook.xml" in names:
        wb = z.read("xl/workbook.xml").decode("utf-8", "ignore")
        sheets = [s for s in re.findall(r'name="([^"]+)"', wb)
                  if not s.startswith(("_xlnm", "microsoft.com"))]
        if sheets: out.append("表: " + " | ".join(sheets[:10]))
    if ext == ".pptx":
        n = len([x for x in names if re.match(r"ppt/slides/slide\d+\.xml$", x)])
        out.append(f"{n} 页幻灯片")
    if ext == ".docx" and "word/document.xml" in names:
        doc = z.read("word/document.xml").decode("utf-8", "ignore")
        txt = clean(re.sub(r"<[^>]+>", " ", doc), 120)
        if txt: out.append("正文:" + txt)
    return " · ".join(out) or f"({ext} 无法提取标题)"

def r_pdf(p):
    if has("pdftotext"):
        t = clean(sh(["pdftotext", "-l", "1", "-nopgbrk", p, "-"]), 180)
        if t: return "首页: " + t
    # metadata title fallback
    try:
        raw = open(p, "rb").read(4000).decode("latin-1", "ignore")
        m = re.search(r"/Title\s*\(([^)]{2,120})\)", raw)
        if m: return "标题(元): " + clean(m.group(1), 60)
    except OSError: pass
    return "(pdf · 需 pdftotext 才能读正文)"

def r_image(p):
    if has("exiftool"):
        out = sh(["exiftool", "-s3", "-DateTimeOriginal", "-Model",
                  "-ImageSize", "-GPSPosition", p]).splitlines()
        out = [o.strip() for o in out if o.strip()]
        if out: return "EXIF: " + " · ".join(out[:4])
    return "(图片 · 装 exiftool 可读拍摄时间/机型/定位)"

def r_media(p):
    if has("ffprobe"):
        dur = clean(sh(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", p]), 20)
        title = clean(sh(["ffprobe", "-v", "error", "-show_entries",
                          "format_tags=title,artist", "-of", "csv=p=0", p]), 60)
        s = []
        if dur:
            try: s.append(f"时长{float(dur):.0f}s")
            except ValueError: pass
        if title: s.append(title)
        if s: return "媒体: " + " · ".join(s)
    return "(音视频 · 装 ffmpeg 可读时长/标签)"

def r_zip(p):
    try:
        n = zipfile.ZipFile(p).namelist()
        return f"压缩包 {len(n)} 项: " + " ".join(os.path.basename(x) for x in n[:5] if x)
    except Exception: return "(压缩包)"

READERS = {
    ".md": r_text, ".txt": r_text, ".csv": r_text, ".json": r_text, ".log": r_text,
    ".py": r_text, ".js": r_text, ".ts": r_text, ".sh": r_text, ".yml": r_text, ".yaml": r_text,
    ".html": r_html, ".htm": r_html,
    ".xlsx": r_office, ".docx": r_office, ".pptx": r_office,
    ".pdf": r_pdf,
    ".jpg": r_image, ".jpeg": r_image, ".png": r_image, ".heic": r_image, ".tiff": r_image,
    ".mp4": r_media, ".mov": r_media, ".mp3": r_media, ".wav": r_media, ".m4a": r_media, ".mkv": r_media,
    ".zip": r_zip,
}

def sig(p):
    ext = os.path.splitext(p)[1].lower()
    fn = READERS.get(ext)
    if fn:
        try:
            out = fn(p)
            if out: return out
        except Exception as e:
            return f"(读取失败: {type(e).__name__})"
    try:
        st = os.stat(p)
        b = getattr(st, "st_birthtime", st.st_ctime)
        return f"(二进制/未知 · {time.strftime('%Y-%m-%d', time.localtime(b))})"
    except OSError:
        return "(无法读取)"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?")
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--ext", help="comma list, e.g. .html,.xlsx")
    ap.add_argument("--max", type=int, default=400)
    a = ap.parse_args()

    exts = set(a.ext.split(",")) if a.ext else None
    files = []
    if a.files:
        files = a.files
    else:
        root = os.path.abspath(a.folder)
        for dp, dns, fns in os.walk(root):
            if os.path.basename(dp).startswith("."): continue
            for fn in fns:
                if fn.startswith("."): continue
                if exts and os.path.splitext(fn)[1].lower() not in exts: continue
                files.append(os.path.join(dp, fn))
        files.sort()
    for p in files[:a.max]:
        rel = os.path.relpath(p) if not a.files else p
        print(f"── {rel}")
        print(f"   {sig(p)}")

if __name__ == "__main__":
    main()
