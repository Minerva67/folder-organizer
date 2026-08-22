#!/usr/bin/env bash
# safe_stage.sh — Move files/dirs into a reversible staging trash instead of
# hard-deleting. Nothing is ever destroyed by this skill; the user empties the
# staging folder themselves once they've confirmed.
#
# Usage:
#   safe_stage.sh <root> <path1> [path2 ...]
# Creates <root>/_待删_<YYYYMMDD>/ and moves each path there, preserving basename.
# Prints what it moved and the staging folder's total size.
#
# Handles spaces / CJK / special chars because every path is quoted and passed
# as a separate argument (never word-split a filename).

set -u
root="${1:?need root}"; shift
stage="$root/_待删_$(date +%Y%m%d)"
mkdir -p "$stage"

for p in "$@"; do
  [ -e "$p" ] || { echo "SKIP (缺失): $p"; continue; }
  base="$(basename "$p")"
  dest="$stage/$base"
  # avoid clobbering a same-named earlier staged item
  n=1; while [ -e "$dest" ]; do dest="$stage/${base%.*}~$n.${base##*.}"; n=$((n+1)); done
  mv "$p" "$dest" && echo "STAGED: $base"
done

echo "----"
echo "暂存夹: $stage"
du -sh "$stage" 2>/dev/null
echo "确认无误后可清空该文件夹（拖废纸篓 / rm -rf），或把内容拖回。"
