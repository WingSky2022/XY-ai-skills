#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""作业评分快照刷新：whyai CLI 只读拉取「一堂」全部作业评分 → 本地 JSON 数据真相源 + 自包含 HTML 工作台。

流程：
  0. 环境核对（版本基线 + 登录态/Gateway，可用 --skip-env-check 跳过）
  1. 发现 whyai CLI（env WHYAI_BIN > PATH > macOS ~/.local/bin > Windows %LOCALAPPDATA%\\WhyAI\\bin）
  2. 分页拉取 homework list（只读），去重组装 rows
  3. 与现有 JSON 合并：保留 account（账户学分为官方口径，不从作业列表推算）
  4. 原子写 JSON（默认先把旧文件备份为 .bak）
  5. 目标目录无 HTML 时从 assets/workbench.template.html 实例化工作台；已有则仅替换 seed 块

只读拉取、零出境：不调用 whyai chat / 上传 / 任何写操作。
用法（在你想存放数据的目录里运行）：
  python3 refresh_homework.py --dry-run          # 环境核对 + 只拉取出报告，不写任何文件
  python3 refresh_homework.py                    # 拉取并生成/更新 JSON + 工作台
  python3 refresh_homework.py --with-raw         # 额外归档原始返回（含作业正文全文）到 raw/
  python3 refresh_homework.py --target 某目录    # 指定输出目录（默认当前目录）
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

NAME = "一堂作业评分清单"
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(SKILL_DIR, "..", "assets", "workbench.template.html")
DEFAULT_TARGET = os.getcwd()

# 环境核对基线：与本技能核对时的 whyai CLI 版本。版本变化可能意味着行为边界变化，
# 不一致时脚本默认拒绝执行；人工确认版本变化无碍后可加 --skip-env-check。
BASELINE_VERSION = "0.5.7"
GATEWAY = "https://ai.yitang.top"


def find_whyai():
    cand = os.environ.get("WHYAI_BIN")
    if cand and os.path.exists(cand):
        return cand
    found = shutil.which("whyai")
    if found:
        return found
    home = os.path.expanduser("~")
    for p in (
        os.path.join(home, ".local", "bin", "whyai"),
        os.path.join(home, ".local", "bin", "whyai.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "WhyAI", "bin", "whyai.exe"),
    ):
        if p and os.path.exists(p):
            return p
    return None


def preflight(whyai):
    """内嵌的环境核对与安全边界：版本基线 + 登录态/Gateway。"""
    v = subprocess.run([whyai, "--version"], capture_output=True, text=True, timeout=60).stdout.strip()
    if v != BASELINE_VERSION:
        raise SystemExit(
            "[STOP] whyai 版本 %s 与本技能核对基线 %s 不一致。\n"
            "版本变化可能改变命令行为与数据边界，请先人工确认版本变化内容；确认无碍后加 --skip-env-check 重跑。"
            % (v, BASELINE_VERSION))
    st = subprocess.run([whyai, "status", "--json"], capture_output=True, text=True, timeout=60)
    try:
        d = json.loads(st.stdout)
    except Exception:
        raise SystemExit("[STOP] 无法解析 whyai status 输出，请先手动运行 whyai status --json 检查登录态。")
    ok = d.get("logged_in") is True and d.get("gateway") == GATEWAY and d.get("environment") == "prod"
    if not ok:
        raise SystemExit(
            "[STOP] 登录态/Gateway 校验未通过（logged_in=%s, gateway=%s, environment=%s）。\n"
            "请先 whyai login --gateway %s 完成正式环境登录；确认无误后可加 --skip-env-check。"
            % (d.get("logged_in"), d.get("gateway"), d.get("environment"), GATEWAY))
    print("环境核对 OK：whyai v%s · gateway %s · prod · 已登录" % (v, GATEWAY))


def run_page(whyai, page):
    cmd = [whyai, "yitang", "homework", "list", "--param", "page=%d" % page, "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        raise RuntimeError("page %d 拉取失败 (exit %d): %s" % (page, proc.returncode, proc.stderr.strip()[:300]))
    d = json.loads(proc.stdout)
    if not d.get("ok"):
        raise RuntimeError("page %d 返回 ok=false" % page)
    data = d.get("data") or {}
    return data.get("items") or [], (data.get("meta") or {})


def build_rows(items):
    rows = {}
    for it in items:
        rows[it["id"]] = {
            "id": it["id"],
            "title": it.get("lessonName") or "",
            "score": it.get("score") or 0,
            "excellent": bool(it.get("isExcellentWork")),
            "commented": bool(it.get("commented")),
            "wordCount": it.get("textCount") or 0,
            "date": it.get("editTime") or "",
        }
    out = sorted(rows.values(), key=lambda r: (-r["score"], r["date"]))
    return out


def summarize(rows):
    dist = {"6": 0, "5": 0, "4": 0, "3": 0, "0": 0}
    s = 0
    graded = 0
    for r in rows:
        k = str(r["score"] or 0)
        dist[k] = dist.get(k, 0) + 1
        if r["score"]:
            s += r["score"]
            graded += 1
    return dist, s, graded


def atomic_write(path, text, backup=True):
    if backup and os.path.exists(path):
        bak = path + ".bak"
        shutil.copy2(path, bak)
        print("  备份: %s -> %s" % (os.path.basename(path), os.path.basename(bak)))
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main():
    ap = argparse.ArgumentParser(description="作业评分快照刷新（whyai CLI 只读拉取 → JSON + 工作台）")
    ap.add_argument("--dry-run", action="store_true", help="环境核对 + 只拉取出报告，不写文件")
    ap.add_argument("--pages", type=int, default=0, help="限定页数（默认按 meta.pageCount 自动）")
    ap.add_argument("--target", default=DEFAULT_TARGET, help="输出目录（默认当前目录）")
    ap.add_argument("--no-backup", action="store_true", help="覆盖前不生成 .bak")
    ap.add_argument("--skip-env-check", action="store_true",
                    help="跳过版本基线与登录态核对（人工确认环境无碍后使用）")
    ap.add_argument("--with-raw", action="store_true",
                    help="同时归档原始 API 返回（含作业正文全文）到 raw/一堂作业正文-<日期>.json")
    args = ap.parse_args()

    whyai = find_whyai()
    if not whyai:
        print("[STOP] 未找到 whyai CLI（试过 WHYAI_BIN / PATH / ~/.local/bin / %LOCALAPPDATA%\\WhyAI\\bin）")
        print("安装与登录见 https://ai.yitang.top/cli")
        return 2
    preflight(whyai) if not args.skip_env_check else print("[WARN] 已跳过环境核对（--skip-env-check）")

    items, meta = run_page(whyai, 1)
    page_count = args.pages or int(meta.get("pageCount") or 1)
    total = int(meta.get("totalCount") or 0)
    print("拉取: 共 %d 页（服务端 totalCount=%s）" % (page_count, total))
    for p in range(2, page_count + 1):
        more, _ = run_page(whyai, p)
        items.extend(more)
        print("  page %d/%d ok (+%d)" % (p, page_count, len(more)))

    rows = build_rows(items)
    dist, score_sum, graded = summarize(rows)
    today = datetime.date.today().strftime("%Y-%m-%d")
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    print("-" * 46)
    print("本次快照: %d 条作业 | 评分合计 %d | 满分 %d | 分布 6:%d 5:%d 4:%d 3:%d 未评:%d"
          % (len(rows), score_sum, dist["6"], dist["6"], dist["5"], dist["4"], dist["3"], dist["0"]))
    if total and len(rows) != total:
        print("[WARN] 去重后 %d 条 != totalCount %d，请人工核对" % (len(rows), total))

    json_path = os.path.join(args.target, NAME + ".json")
    html_path = os.path.join(args.target, NAME + ".html")

    old = None
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as fh:
            old = json.load(fh)

    if old:
        odist, osum, ograded = summarize(old.get("rows") or [])
        print("与上一份对比: 条数 %d -> %d | 合计 %d -> %d | 满分 %d -> %d"
              % (len(old.get("rows") or []), len(rows), osum, score_sum, odist.get("6", 0), dist["6"]))
        orows = {r["id"]: r for r in (old.get("rows") or [])}
        nrows = {r["id"]: r for r in rows}
        added = sorted(set(nrows) - set(orows))
        removed = sorted(set(orows) - set(nrows))
        changed = [(i, orows[i]["score"], nrows[i]["score"], nrows[i]["title"]) for i in sorted(set(orows) & set(nrows)) if orows[i]["score"] != nrows[i]["score"]]
        if added:
            print("  新增 %d 条:" % len(added))
            for i in added[:10]:
                print("   + [%s] %s" % (nrows[i]["score"], nrows[i]["title"][:40]))
        if removed:
            print("  消失 %d 条:" % len(removed))
            for i in removed[:10]:
                print("   - %s" % orows[i]["title"][:40])
        if changed:
            print("  评分变化 %d 条:" % len(changed))
            for i, a, b, t in changed[:10]:
                print("   ~ %s -> %s  %s" % (a, b, t[:40]))

    if args.dry_run:
        print("[dry-run] 未写任何文件。去掉 --dry-run 执行真实写入。")
        return 0

    account = (old or {}).get("account") or {}
    if not account.get("score"):
        print("[WARN] 现有 JSON 无 account（账户学分），沿用空值；请在 JSON 手工补 account 后再生成报告口径")
    data = {
        "version": (old or {}).get("version", 1),
        "meta": {
            "snapshotDate": today,
            "fetchedAt": now,
            "title": (old.get("meta", {}).get("title") if old else None) or "一堂作业评分数据（真相源）",
            "source": (old.get("meta", {}).get("source") if old else None) or "whyai yitang homework list（只读分页）+ me.info + summary.current",
            "fillGuide": (old.get("meta", {}).get("fillGuide") if old else None) or (
                "以后更新：重新运行本技能脚本 refresh_homework.py 自动刷新；"
                "或手填 rows（id/title/score/excellent/commented/wordCount/date）与 account 四项——"
                "count/sum/avg/分布等全部由页面自动计算。"),
        },
        "account": account or {"score": None, "scoreExtra": None, "officialExcellent": None, "officialPerfect": None},
        "rows": rows,
    }

    os.makedirs(args.target, exist_ok=True)
    atomic_write(json_path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", backup=not args.no_backup)
    print("写入: %s (%d bytes)" % (json_path, os.path.getsize(json_path)))

    if os.path.exists(html_path):
        with open(html_path, encoding="utf-8") as fh:
            html = fh.read()
        seed = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
        new_html, n = re.subn(
            r'(<script id="seed" type="application/json">).*?(</script>)',
            lambda m: m.group(1) + seed + m.group(2),
            html, flags=re.S)
        if n != 1:
            print("[WARN] HTML 中未定位到唯一 seed 块（找到 %d 处），HTML 未改动" % n)
        else:
            atomic_write(html_path, new_html, backup=not args.no_backup)
            print("写入: %s（仅替换 seed 块，其余内容未动）" % html_path)
    else:
        # 工作台不存在：从技能自带模板实例化（首次使用即得完整工作台）
        if os.path.exists(TEMPLATE):
            with open(TEMPLATE, encoding="utf-8") as fh:
                tpl = fh.read()
            seed = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
            if "__SEED__" not in tpl or "__NAME__" not in tpl:
                print("[WARN] 模板缺少 __SEED__/__NAME__ 占位符，请检查 assets/workbench.template.html")
            else:
                inst = tpl.replace("__SEED__", seed).replace("__NAME__", NAME)
                atomic_write(html_path, inst, backup=not args.no_backup)
                print("写入: %s（自模板实例化工作台）" % html_path)
        else:
            print("[WARN] 未找到 %s 且目标无 HTML，跳过工作台生成" % TEMPLATE)

    if args.with_raw:
        seen = {}
        for it in items:
            seen[it["id"]] = it
        raw_items = sorted(seen.values(),
                           key=lambda r: (-(r.get("score") or 0), r.get("editTime") or ""))
        raw_dir = os.path.join(args.target, "raw")
        os.makedirs(raw_dir, exist_ok=True)
        raw_path = os.path.join(raw_dir, "一堂作业正文-%s.json" % today)
        raw_data = {
            "version": 1,
            "meta": {
                "snapshotDate": today,
                "fetchedAt": now,
                "title": "一堂作业正文全文（原始 API 返回归档）",
                "source": "whyai yitang homework list（只读，%d 页 /api/answer/list）" % page_count,
                "itemCount": len(raw_items),
                "note": "字段为接口原样返回（lessonName/score/isExcellentWork/answer/textCount/"
                        "commented/completed/rewardCode/editTime）。派生结构化清单见上级目录 一堂作业评分清单.json。",
            },
            "items": raw_items,
        }
        atomic_write(raw_path, json.dumps(raw_data, ensure_ascii=False, indent=1) + "\n",
                     backup=not args.no_backup)
        print("写入: %s（正文全文 %d 条，%d 字）"
              % (raw_path, len(raw_items), sum(i.get("textCount") or 0 for i in raw_items)))

    print("完成。快照 %s：%d 条作业。" % (today, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
