#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_tree.py — 目录架构体检

检测四类问题：
  1. 嵌套超限（默认 > 3 层）
  2. 命名违规（空格、非国际标准日期、禁用版本词、中文标点等）
  3. 收集箱堆积（Inbox 类目录中文件过多 / 过旧）
  4. 缺失目录说明文件（非叶子目录无 README）

用法:
    python3 audit_tree.py <目录> [--max-depth 3] [--json] [--inbox-age 7] [--quiet]

退出码: 0 = 无问题; 1 = 存在 WARN/ERROR
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# ---------- 常量 ----------

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__",
    ".idea", ".vscode", ".DS_Store", ".pnpm-store", "dist", "build",
    ".next", ".cache", "target", ".pytest_cache", ".mypy_cache",
}

# 归档/收集箱类目录识别（大小写不敏感，支持中英文）
INBOX_PATTERNS = re.compile(r"^(0*1?_?)?(inbox|收集箱|待整理|收件箱|_inbox)$", re.I)
ARCHIVE_PATTERNS = re.compile(r"^(0*9?_?|z_?)?(archive|archives|归档|_archive)$", re.I)

# 命名违规
BANNED_VERSION_WORDS = re.compile(
    r"(最终版|终极版|最终稿|真的最终|最后版本|final\s*final|new\s*final)", re.I
)
NONSTD_DATE = re.compile(r"(?<!\d)(20\d{2})[./年](\d{1,2})[./月](\d{1,2})(?!\d)")
ISO_DATE = re.compile(r"(?<!\d)20\d{2}-\d{2}-\d{2}(?!\d)")
# 中文标点/特殊符号出现在文件名中（易导致跨平台问题）
BAD_CHARS = re.compile(r'[\\/:*?"<>|\u3000]')
# 目录/文件说明文件候选名
README_NAMES = {"readme.md", "readme.txt", "readme", "_readme.md", "index.md"}
# 根目录主控文件候选名（AI 导航层入口）
ROOT_INDEX_NAMES = README_NAMES | {"claude.md", "agents.md", "gemini.md", "copilot-instructions.md"}


# ---------- 数据结构 ----------

class Issue:
    __slots__ = ("level", "kind", "path", "detail")

    def __init__(self, level: str, kind: str, path: str, detail: str):
        self.level = level
        self.kind = kind
        self.path = path
        self.detail = detail

    def as_dict(self):
        return {"level": self.level, "kind": self.kind, "path": self.path, "detail": self.detail}


# ---------- 采集 ----------

def walk(root: Path, max_depth: int):
    """遍历目录，返回 (dirs, files_by_dir, depth_by_path)。不进入隐藏目录与依赖目录。"""
    dirs, files_by_dir, depth_by_path = [], {}, {}
    root_depth = len(root.resolve().parts)

    for cur, dirnames, filenames in os.walk(root, followlinks=False):
        cur_path = Path(cur)
        rel_depth = len(cur_path.resolve().parts) - root_depth  # root 自身为 0
        depth_by_path[str(cur_path)] = rel_depth

        # 过滤：隐藏目录与已知依赖目录
        kept = []
        for d in sorted(dirnames):
            if d in SKIP_DIRS or d.startswith("."):
                continue
            kept.append(d)
            dirs.append((str(cur_path / d), rel_depth + 1))
        dirnames[:] = kept

        real_files = [f for f in sorted(filenames) if not f.startswith(".")]
        files_by_dir[str(cur_path)] = real_files
        for f in real_files:
            depth_by_path[str(cur_path / f)] = rel_depth + 1

    return dirs, files_by_dir, depth_by_path


# ---------- 检查 ----------

def check_depth(dirs, max_depth):
    out = []
    for path, depth in dirs:
        if depth > max_depth:
            out.append(Issue("WARN", "depth", path,
                             f"嵌套 {depth} 层，超过上限 {max_depth}；更深的层级通常意味着分类维度选错了"))
    return out


def check_naming(files_by_dir):
    out = []
    for d, files in files_by_dir.items():
        for f in files:
            p = str(Path(d) / f)
            stem = Path(f).stem
            reasons = []

            if " " in f:
                reasons.append("含空格（路径需转义，脚本与 AI 处理易出错）")
            if BAD_CHARS.search(f):
                reasons.append("含非法/全角字符")
            if BANNED_VERSION_WORDS.search(stem):
                reasons.append("使用「最终版/终极版」类不可排序版本词")
            m = NONSTD_DATE.search(stem)
            if m and not ISO_DATE.search(stem):
                reasons.append(f"日期格式非国际标准（{m.group(0)} → 应为 YYYY-MM-DD）")

            if reasons:
                level = "ERROR" if ("含空格" in "".join(reasons) or "最终版" in "".join(reasons)) else "WARN"
                out.append(Issue(level, "naming", p, "；".join(reasons)))
    return out


def check_inbox(files_by_dir, inbox_max_age_days):
    """收集箱堆积：文件数过多，或存在超期未处理文件。"""
    out = []
    now = time.time()
    for d, files in files_by_dir.items():
        name = Path(d).name
        if not INBOX_PATTERNS.match(name):
            continue
        if not files:
            continue

        # 文件数量阈值
        if len(files) > 20:
            out.append(Issue("WARN", "inbox", d,
                             f"收集箱堆积 {len(files)} 个文件（建议每周清空，阈值 20）"))

        # 超期文件
        stale = []
        for f in files:
            fp = Path(d) / f
            try:
                age = (now - fp.stat().st_mtime) / 86400
                if age > inbox_max_age_days:
                    stale.append((f, int(age)))
            except OSError:
                continue
        if stale:
            preview = "、".join(f"{n}({a}天)" for n, a in stale[:5])
            more = f" 等 {len(stale)} 个" if len(stale) > 5 else ""
            out.append(Issue("WARN", "inbox", d,
                             f"收集箱存在超期文件（>{inbox_max_age_days}天）：{preview}{more}"))
    return out


def check_readme(dirs, files_by_dir, root):
    """非叶子目录（含子目录的目录）缺失 README；根目录单独按主控文件判定。"""
    out = []
    subdir_parents = set()
    for path, _ in dirs:
        subdir_parents.add(str(Path(path).parent))

    root_resolved = Path(root).resolve()

    for d in sorted(subdir_parents):
        files = files_by_dir.get(d, [])
        lower = {f.lower() for f in files}
        is_root = Path(d).resolve() == root_resolved

        if is_root:
            if not (lower & ROOT_INDEX_NAMES):
                out.append(Issue("INFO", "readme", d,
                                 "根目录建议有主控文件（CLAUDE.md / AGENTS.md / README.md）"))
            continue

        if not (lower & README_NAMES):
            out.append(Issue("WARN", "readme", d,
                             "非叶子目录缺说明文件，AI 进入时无从判断这里放什么"))
    return out


# ---------- 汇总 ----------

def summarize(root: Path, max_depth: int, inbox_age: int):
    dirs, files_by_dir, _ = walk(root, max_depth)
    issues = []
    issues += check_depth(dirs, max_depth)
    issues += check_naming(files_by_dir)
    issues += check_inbox(files_by_dir, inbox_age)
    issues += check_readme(dirs, files_by_dir, root)

    total_files = sum(len(v) for v in files_by_dir.values())
    max_actual_depth = max((d for _, d in dirs), default=0)

    return {
        "root": str(root),
        "stats": {
            "dirs": len(dirs),
            "files": total_files,
            "max_depth": max_actual_depth,
            "top_level_dirs": len([d for d, dep in dirs if dep == 1]),
        },
        "issues": issues,
    }


def main():
    ap = argparse.ArgumentParser(description="目录架构体检（深度/命名/收集箱/目录说明）")
    ap.add_argument("path", help="目标目录")
    ap.add_argument("--max-depth", type=int, default=3, help="嵌套层级上限（默认 3）")
    ap.add_argument("--inbox-age", type=int, default=7, help="收集箱文件超期天数（默认 7）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总与 ERROR")
    args = ap.parse_args()

    root = Path(args.path).expanduser()
    if not root.is_dir():
        print(f"ERROR: 目录不存在或不是目录: {root}", file=sys.stderr)
        return 2

    data = summarize(root, args.max_depth, args.inbox_age)
    issues = data["issues"]

    if args.json:
        payload = dict(data)
        payload["issues"] = [i.as_dict() for i in issues]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        s = data["stats"]
        print(f"📁 体检目录: {data['root']}")
        print(f"   目录 {s['dirs']} 个 | 文件 {s['files']} 个 | "
              f"实际最深 {s['max_depth']} 层 | 一级目录 {s['top_level_dirs']} 个")

        if not issues:
            print("\n✅ 未发现问题")
        else:
            by_kind = {}
            for i in issues:
                if args.quiet and i.level != "ERROR":
                    continue
                by_kind.setdefault(i.kind, []).append(i)

            labels = {
                "depth": "嵌套超限",
                "naming": "命名违规",
                "inbox": "收集箱堆积",
                "readme": "目录说明缺失",
            }
            for kind, items in by_kind.items():
                print(f"\n【{labels.get(kind, kind)}】{len(items)} 项")
                for i in items:
                    rel = os.path.relpath(i.path, root)
                    print(f"  [{i.level}] {rel} — {i.detail}")

        counts = {}
        for i in issues:
            counts[i.level] = counts.get(i.level, 0) + 1
        print("\n汇总: " + " | ".join(f"{k} {v}" for k, v in sorted(counts.items())) if counts else "\n汇总: 0 项问题")

        # 一级目录数量提示（7±2 原则）
        n_top = data["stats"]["top_level_dirs"]
        if n_top > 9:
            print(f"⚠️  一级目录 {n_top} 个，超过 7±2 上限，建议合并维度")
        elif n_top == 0 and data["stats"]["dirs"] == 0:
            print("ℹ️  目标目录为空，可直接按模板搭建骨架")

    return 1 if any(i.level in ("WARN", "ERROR") for i in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
