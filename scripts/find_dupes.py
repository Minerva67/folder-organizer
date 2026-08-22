#!/usr/bin/env python3
"""
find_dupes.py — Find redundant files objectively, by CONTENT not by name.

Two kinds of redundancy, reported separately because they need different handling:
  A) EXACT duplicates  — identical bytes (same md5). Safe to collapse to one copy.
  B) VERSION residue   — different bytes but near-identical names once version
                         tokens are stripped (v1/v2, 副本, "(1)", " 2", _final,
                         timestamps). These are ITERATIONS — never auto-pick which
                         to delete; that's the user's call.

Usage:
    python3 find_dupes.py <folder> [--json out.json]

Strategy: group by size first (cheap), md5 only within same-size groups.
"""
import os, sys, hashlib, re, argparse, json
from collections import defaultdict

def human(n):
    for u in ("B","K","M","G","T"):
        if n < 1024: return f"{n:.0f}{u}" if u=="B" else f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}P"

def md5(p, chunk=1<<20):
    h = hashlib.md5()
    try:
        with open(p,"rb") as f:
            for b in iter(lambda: f.read(chunk), b""): h.update(b)
    except OSError: return None
    return h.hexdigest()

# tokens that mark a version/copy, stripped to find the "stem"
VER = re.compile(r"""
    (\s*[\(（]\s*\d+\s*[\)）])        # (1) （2）  copy suffix
  | (\s+\d+(?=\.[^.]+$))               # " 2" before extension (macOS dup)
  | ([_\-\s]*v?\d+(\.\d+)*)            # v1 v12.3 _2 -3
  | ([_\-\s]*(final|终版|定稿|副本|旧版|old|copy|draft|过程稿|待修改))
  | (\.?\d{8,}(\d{6,})?)              # timestamps 20260807 / long ms stamps
  | (before\s*\d+(\.\d+)?)
""", re.I | re.X | re.U)

def stem(name):
    base, ext = os.path.splitext(name)
    prev = None
    while prev != base:
        prev = base
        base = VER.sub("", base)
    base = re.sub(r"[ _\-]+", "", base).strip().lower()
    return base + ext.lower()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--json")
    a = ap.parse_args()
    root = os.path.abspath(a.folder)

    by_size = defaultdict(list)
    all_files = []
    for dp, dns, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            try: st = os.lstat(p)
            except OSError: continue
            if not os.path.isfile(p) or os.path.islink(p): continue
            by_size[st.st_size].append(p)
            all_files.append((p, fn, st.st_size))

    # A) exact duplicates
    exact = []   # list of dicts {hash,size,paths}
    reclaim = 0
    for sz, paths in by_size.items():
        if len(paths) < 2 or sz == 0: continue
        by_hash = defaultdict(list)
        for p in paths: by_hash[md5(p)].append(p)
        for h, ps in by_hash.items():
            if h and len(ps) > 1:
                ps.sort()
                exact.append({"hash":h,"size":sz,"paths":ps})
                reclaim += sz*(len(ps)-1)
    exact.sort(key=lambda d:-d["size"]*(len(d["paths"])-1))

    # B) version residue (name stems shared by >1 DISTINCT-content file)
    by_stem = defaultdict(list)
    exact_set = {p for d in exact for p in d["paths"]}
    for p, fn, sz in all_files:
        by_stem[os.path.join(os.path.dirname(p), stem(fn))].append((p,fn,sz))
    versions = []
    for k, items in by_stem.items():
        names = {fn for _,fn,_ in items}
        if len(items) > 1 and len(names) > 1:
            versions.append(sorted(items, key=lambda x:x[1]))

    # ---- report ----
    print(f"# 冗余扫描  {root}\n")
    print(f"## A · 完全重复（内容逐字节相同，可只留一份）  可回收 {human(reclaim)}")
    if not exact: print("  （无）")
    for d in exact:
        print(f"\n  [{human(d['size'])} ×{len(d['paths'])}]  可省 {human(d['size']*(len(d['paths'])-1))}")
        for p in d["paths"]:
            print(f"      {os.path.relpath(p,root)}")

    print(f"\n## B · 版本残留（名字相近、内容不同 = 迭代版本，不要自动删）")
    if not versions: print("  （无）")
    for grp in versions:
        stemname = os.path.splitext(grp[0][1])[0]
        print(f"\n  {os.path.relpath(os.path.dirname(grp[0][0]),root)}/ · 疑似 {len(grp)} 版:")
        for p,fn,sz in grp:
            print(f"      {human(sz):>7}  {fn}")

    if a.json:
        json.dump({"root":root,"exact":exact,"reclaim":reclaim,
                   "versions":[[list(x) for x in g] for g in versions]},
                  open(a.json,"w"), ensure_ascii=False, indent=2)
        print(f"\n(JSON → {a.json})")

if __name__ == "__main__":
    main()
