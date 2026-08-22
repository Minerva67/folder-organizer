#!/usr/bin/env python3
"""
scan.py — Profile a folder so you know the terrain before touching anything.

Outputs: total size, per-extension counts/sizes, biggest files, date range,
and the deepest/most-cluttered subtrees. Works on any folder, any OS.

Usage:
    python3 scan.py <folder> [--top 20]

Notes:
- Creation time is best-effort: st_birthtime on macOS, else st_ctime.
- Hidden files (dotfiles) are counted but flagged separately.
"""
import os, sys, argparse, time
from collections import defaultdict

def human(n):
    for u in ("B","K","M","G","T"):
        if n < 1024: return f"{n:.0f}{u}" if u=="B" else f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}P"

def birth(st):
    return getattr(st, "st_birthtime", st.st_ctime)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--top", type=int, default=20)
    a = ap.parse_args()
    root = os.path.abspath(a.folder)

    ext_count = defaultdict(int); ext_size = defaultdict(int)
    biggest = []            # (size, path)
    dir_size = defaultdict(int)
    total = 0; nfiles = 0; nhidden = 0
    tmin = None; tmax = None

    for dp, dns, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            try: st = os.lstat(p)
            except OSError: continue
            if not os.path.isfile(p) or os.path.islink(p): continue
            sz = st.st_size; total += sz; nfiles += 1
            if fn.startswith("."): nhidden += 1
            ext = os.path.splitext(fn)[1].lower() or "(noext)"
            ext_count[ext]+=1; ext_size[ext]+=sz
            biggest.append((sz,p))
            # attribute size to the top-level subfolder under root
            rel = os.path.relpath(dp, root)
            top = root if rel=="." else os.path.join(root, rel.split(os.sep)[0])
            dir_size[top]+=sz
            b = birth(st)
            tmin = b if tmin is None else min(tmin,b)
            tmax = b if tmax is None else max(tmax,b)

    biggest.sort(reverse=True)
    print(f"# 文件夹画像  {root}")
    print(f"总计: {nfiles} 个文件 · {human(total)}  (含 {nhidden} 个隐藏文件)")
    if tmin: print(f"时间跨度: {time.strftime('%Y-%m-%d',time.localtime(tmin))} → {time.strftime('%Y-%m-%d',time.localtime(tmax))}")

    print(f"\n## 顶层子夹体积 (Top)")
    for d,s in sorted(dir_size.items(), key=lambda x:-x[1])[:a.top]:
        name = "(根目录散文件)" if d==root else os.path.basename(d)
        print(f"  {human(s):>7}  {name}")

    print(f"\n## 文件类型分布")
    for ext,cnt in sorted(ext_count.items(), key=lambda x:-ext_size[x[0]])[:a.top]:
        print(f"  {human(ext_size[ext]):>7}  {cnt:>4} 个  {ext}")

    print(f"\n## 最大的文件 (Top {a.top})")
    for s,p in biggest[:a.top]:
        print(f"  {human(s):>7}  {os.path.relpath(p,root)}")

if __name__ == "__main__":
    main()
