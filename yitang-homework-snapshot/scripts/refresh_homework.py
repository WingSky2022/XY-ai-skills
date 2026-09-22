#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""作业评分快照刷新：whyai CLI 只读拉取「一堂」全部作业评分 → 数据目录写 JSON + 技能内生成工作台。

目录约定（关注点分离）：
  技能目录/            程序 + 工作台前端（workbench/，不含个人数据）
  数据目录/            只有数据：一堂作业评分清单.json（可选 raw/ 正文归档）
  数据目录由技能内 config.json 的 data_dir 指定（相对路径按技能目录解析，便于跨机同步）

流程：
  0. 环境核对（版本基线 + 登录态/Gateway，可用 --skip-env-check 跳过）
  1. 发现 whyai CLI（env WHYAI_BIN > PATH > macOS ~/.local/bin > Windows %LOCALAPPDATA%\\WhyAI\\bin）
  2. 分页拉取 homework list（只读），去重组装 rows
  3. 与现有 JSON 合并：保留 account（账户学分为官方口径，不从作业列表推算）
  4. 原子写 JSON 到数据目录（默认先把旧文件备份为 .bak）
  5. 在技能内 workbench/ 生成工作台前端（空 seed，不含个人数据）；页面经本地服务读取数据目录的 JSON

只读拉取、零出境：不调用 whyai chat / 上传 / 任何写操作。
两段式流程（写入前必须过确认门禁）：
  python3 refresh_homework.py                    # 第一段：环境核对 + 只读拉取 + 出报告，**不写文件**
  python3 refresh_homework.py --confirm          # 第二段：用户确认后执行全量写入
  python3 refresh_homework.py --confirm --serve  # 写入后直接拉起后台服务并打开工作台
  python3 refresh_homework.py --confirm --with-raw   # 顺带归档作业正文全文到 数据目录/raw/
"""
import argparse
import datetime
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse

DATA_NAME = "一堂作业评分清单"
PAGE_NAME = "一堂作业评分清单.html"
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.abspath(os.path.join(SKILL_DIR, ".."))
TEMPLATE = os.path.join(SKILL_ROOT, "assets", "workbench.template.html")
WORKBENCH_DIR = os.path.join(SKILL_ROOT, "workbench")
CONFIG_PATH = os.path.join(SKILL_ROOT, "config.json")
DEFAULT_DATA_DIR = os.path.expanduser("~/Documents/一堂作业工作台")

# 环境核对基线：与本技能核对时的 whyai CLI 版本。版本变化可能意味着行为边界变化，
# 不一致时脚本默认拒绝执行；人工确认版本变化无碍后可加 --skip-env-check。
BASELINE_VERSION = "0.5.8"
GATEWAY = "https://ai.yitang.top"

sys.path.insert(0, SKILL_DIR)
try:
    import start_workbench as wb
except Exception:
    wb = None


def resolve_data_dir(cli_target):
    """数据目录优先级：--target > 环境变量 YITANG_HOMEWORK_DATA_DIR > config.json 的 data_dir > 内置默认。

    config.json 里的相对路径按技能目录解析 —— 技能随仓库同步时，数据目录也跟着走，无需改配置。
    """
    if cli_target:
        return os.path.abspath(os.path.expanduser(cli_target))
    env = os.environ.get("YITANG_HOMEWORK_DATA_DIR")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    cfg_dir = None
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as fh:
                cfg_dir = (json.load(fh) or {}).get("data_dir")
        except Exception as e:
            print("[WARN] config.json 解析失败（%s），改用内置默认目录" % e)
    if cfg_dir:
        cfg_dir = os.path.expanduser(str(cfg_dir))
        if not os.path.isabs(cfg_dir):
            cfg_dir = os.path.join(SKILL_ROOT, cfg_dir)
        return os.path.abspath(cfg_dir)
    return DEFAULT_DATA_DIR


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


# ---- 入库清洗（v1.2.2）：不可见字符 ----
# 背景：接口返回的课程标题里出现过 U+2028（行分隔符 LS），VS Code 会弹「检测到异常行终止符」，
# 且 splitlines()/grep 等按行处理工具会把标题切成两行、表格导入会错行。
# 原则：只清理「不可见且无语义」的字符；emoji 的组成字符一律保留，避免组合 emoji（如 🙋♂️）散架。
_LS_PS = {0x2028, 0x2029}                                        # 行/段分隔符 → 半角空格
_ZW_DROP = {0x200B, 0x200E, 0x200F, 0x2060, 0xFEFF} | set(range(0x202A, 0x202F))
#          ZWSP / LRM / RLM / WORD JOINER / ZWNBSP / 双向控制符 → 直接删除
# 刻意保留：U+200C ZWNJ、U+200D ZWJ（emoji 组成）、U+FE0F 变体选择符、U+20E3 键帽、U+00A0 NBSP（有排版语义）


def sanitize_text(s):
    if not isinstance(s, str) or not s:
        return s
    return "".join(" " if ord(ch) in _LS_PS else ch
                   for ch in s if ord(ch) not in _ZW_DROP)


def sanitize_deep(obj):
    """递归清洗字符串；dict/list 逐层下钻，其余类型原样返回。"""
    if isinstance(obj, str):
        return sanitize_text(obj)
    if isinstance(obj, list):
        return [sanitize_deep(x) for x in obj]
    if isinstance(obj, dict):
        return {k: sanitize_deep(v) for k, v in obj.items()}
    return obj


def find_latest_raw(data_dir):
    """数据目录 raw/ 下最新的正文归档相对路径（文件名含日期，取排序最大者）。"""
    rd = os.path.join(data_dir, "raw")
    if not os.path.isdir(rd):
        return None
    cands = sorted(f for f in os.listdir(rd)
                   if f.startswith("一堂作业正文-") and f.endswith(".json"))
    return "raw/" + cands[-1] if cands else None


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
    return sorted(rows.values(), key=lambda r: (-r["score"], r["date"]))


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
        # 备份放隐藏子目录，保持数据目录顶层干净（只留数据文件本身）
        bak_dir = os.path.join(os.path.dirname(path), ".backup")
        os.makedirs(bak_dir, exist_ok=True)
        bak = os.path.join(bak_dir, os.path.basename(path) + ".bak")
        shutil.copy2(path, bak)
        print("  备份: %s -> .backup/%s" % (os.path.basename(path), os.path.basename(bak)))
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_workbench(backup=True):
    """在技能内 workbench/ 生成工作台前端（空 seed：个人数据只存在于数据目录的 JSON）。"""
    if not os.path.exists(TEMPLATE):
        print("[WARN] 未找到模板 %s，跳过工作台生成" % TEMPLATE)
        return None
    with open(TEMPLATE, encoding="utf-8") as fh:
        tpl = fh.read()
    if "__SEED__" not in tpl or "__NAME__" not in tpl:
        print("[WARN] 模板缺少 __SEED__/__NAME__ 占位符，跳过工作台生成")
        return None
    empty_seed = json.dumps({
        "version": 1,
        "meta": {"snapshotDate": ""},
        "account": {},
        "rows": [],
    }, ensure_ascii=False, separators=(",", ":"))
    inst = tpl.replace("__SEED__", empty_seed).replace("__NAME__", DATA_NAME)
    os.makedirs(WORKBENCH_DIR, exist_ok=True)
    page_path = os.path.join(WORKBENCH_DIR, PAGE_NAME)
    atomic_write(page_path, inst, backup=backup)
    gi = os.path.join(WORKBENCH_DIR, ".gitignore")
    with open(gi, "w", encoding="utf-8") as fh:
        fh.write(".workbench-server.pid\n.workbench-server.log\n.backup/\n*.bak\n")
    print("工作台前端：%s（空 seed；页面经本地服务读取数据目录 JSON）" % page_path)
    return page_path


def write_launchers():
    """在技能内 workbench/ 生成双击启动入口（按 config.json 定位数据目录，不写任何数据）。"""
    starter = os.path.join(SKILL_DIR, "start_workbench.py")
    cmd = os.path.join(WORKBENCH_DIR, "start-workbench.command")
    bat = os.path.join(WORKBENCH_DIR, "start-workbench.bat")
    try:
        os.makedirs(WORKBENCH_DIR, exist_ok=True)
        with open(cmd, "w", encoding="utf-8") as fh:
            fh.write('#!/bin/bash\ncd "$(dirname "$0")"\nexec python3 "%s"\n' % starter)
        os.chmod(cmd, 0o755)
        with open(bat, "w", encoding="ascii", errors="ignore") as fh:
            fh.write('@echo off\r\npython "%s"\r\npause\r\n' % starter)
        print("启动入口：workbench/start-workbench.command（macOS 双击）、workbench/start-workbench.bat（Windows）")
    except Exception as e:
        print("[WARN] 生成启动入口失败：%s" % e)


def serve_in_background(data_dir):
    """拉起后台静态服务（双根：技能内工作台 + 数据目录），并打开浏览器。

    父进程自选端口并把子进程输出写入日志文件（不接管道）：否则父进程退出后管道断裂，
    子进程后续写日志会触发 BrokenPipe 而崩溃。
    """
    starter = os.path.join(SKILL_DIR, "start_workbench.py")
    if wb is None or not os.path.exists(starter):
        print("[WARN] 启动器不可用（%s），已跳过拉起服务" % starter)
        return
    os.makedirs(WORKBENCH_DIR, exist_ok=True)
    port = wb.free_port()
    log_path = os.path.join(WORKBENCH_DIR, ".workbench-server.log")
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    with open(log_path, "a", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [sys.executable, starter, "--data", os.path.abspath(data_dir),
             "--port", str(port), "--no-browser", "--quiet"],
            stdout=log, stderr=log, stdin=subprocess.DEVNULL, **kwargs)

    ok = False
    for _ in range(40):
        try:
            with socket.create_connection(("127.0.0.1", port), 0.2):
                ok = True
                break
        except OSError:
            time.sleep(0.1)
    url = "http://127.0.0.1:%d/%s" % (port, urllib.parse.quote(PAGE_NAME))
    if ok:
        import webbrowser
        webbrowser.open(url)
        print("后台服务已启动（PID %d）：%s" % (proc.pid, url))
        print("停止服务：python3 %s --stop" % starter)
        print("服务日志：%s" % log_path)
    else:
        print("[WARN] 后台服务未就绪，可手动运行：python3 %s --data %s" % (starter, data_dir))
        print("       日志见：%s" % log_path)


def main():
    ap = argparse.ArgumentParser(description="作业评分快照刷新（whyai CLI 只读拉取 → 数据目录 JSON + 技能内工作台）")
    ap.add_argument("--confirm", action="store_true",
                    help="用户已确认：执行全量写入。未加此参数时等同 dry-run（只报告，不写文件）")
    ap.add_argument("--dry-run", action="store_true", help="显式只报告不写文件（默认行为，冗余保留）")
    ap.add_argument("--serve", action="store_true", help="写入完成后拉起后台服务并打开工作台")
    ap.add_argument("--pages", type=int, default=0, help="限定页数（默认按 meta.pageCount 自动）")
    ap.add_argument("--target", default=None, help="数据目录（默认读技能内 config.json 的 data_dir）")
    ap.add_argument("--no-backup", action="store_true", help="覆盖前不生成 .bak")
    ap.add_argument("--skip-env-check", action="store_true",
                    help="跳过版本基线与登录态核对（人工确认环境无碍后使用）")
    ap.add_argument("--with-raw", action="store_true",
                    help="同时归档原始 API 返回（含作业正文全文）到 数据目录/raw/一堂作业正文-<日期>.json")
    args = ap.parse_args()
    dry = args.dry_run or not args.confirm

    data_dir = resolve_data_dir(args.target)

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

    items = sanitize_deep(items)  # 入库清洗：去不可见字符（规则见 sanitize_text 上方注释）

    rows = build_rows(items)
    dist, score_sum, graded = summarize(rows)
    today = datetime.date.today().strftime("%Y-%m-%d")
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    print("-" * 46)
    print("本次快照: %d 条作业 | 评分合计 %d | 满分 %d | 分布 6:%d 5:%d 4:%d 3:%d 未评:%d"
          % (len(rows), score_sum, dist["6"], dist["6"], dist["5"], dist["4"], dist["3"], dist["0"]))
    if total and len(rows) != total:
        print("[WARN] 去重后 %d 条 != totalCount %d，请人工核对" % (len(rows), total))

    json_path = os.path.join(data_dir, DATA_NAME + ".json")

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
        changed = [(i, orows[i]["score"], nrows[i]["score"], nrows[i]["title"])
                   for i in sorted(set(orows) & set(nrows)) if orows[i]["score"] != nrows[i]["score"]]
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

    # 正文归档指针：写进清单 meta.rawFile，工作台详情视图按它加载 raw JSON、按 id 取正文全文
    if args.with_raw:
        raw_ptr = "raw/一堂作业正文-%s.json" % today
    else:
        raw_ptr = find_latest_raw(data_dir) or ((old or {}).get("meta") or {}).get("rawFile")

    if dry:
        print("-" * 46)
        print("[待确认] 全量下载与写入请求（本次仅只读检查，未写任何文件）")
        print("  数据目录：%s" % data_dir)
        print("  技能目录：%s（工作台前端与程序，不含个人数据）" % SKILL_ROOT)
        print("  已读取：%d 页 / %d 条作业" % (page_count, len(rows)))
        print("  将写入：")
        print("    %s（%d 条，account 保留人工口径）" % (json_path, len(rows)))
        print("    workbench/%s（技能内工作台前端，空 seed）" % PAGE_NAME)
        print("    meta.rawFile 正文指针：%s" % (raw_ptr or "（无，未发现 raw 归档）"))
        if args.with_raw:
            print("    raw/一堂作业正文-%s.json（正文全文）" % today)
        print("  确认后执行：python3 %s --confirm%s" % (
            os.path.basename(__file__), " --serve" if args.serve else ""))
        print("  （数据未落盘；此步已完成只读拉取，确认只决定是否写入本地）")
        return 0

    account = (old or {}).get("account") or {}
    if not account.get("score"):
        print("[WARN] 数据文件无 account（账户学分），沿用空值；请在 JSON 手工补 account 后再生成报告口径")
    data = {
        "version": (old or {}).get("version", 1),
        "meta": {
            "snapshotDate": today,
            "fetchedAt": now,
            "title": (old.get("meta", {}).get("title") if old else None) or "一堂作业评分数据（真相源）",
            "source": (old.get("meta", {}).get("source") if old else None)
                      or "whyai yitang homework list（只读分页）+ me.info + summary.current",
            "fillGuide": (old.get("meta", {}).get("fillGuide") if old else None) or (
                "以后更新：重新运行本技能脚本 refresh_homework.py 自动刷新；"
                "或手填 rows（id/title/score/excellent/commented/wordCount/date）与 account 四项——"
                "count/sum/avg/分布等全部由页面自动计算。"),
        },
        "account": account or {"score": None, "scoreExtra": None, "officialExcellent": None, "officialPerfect": None},
        "rows": rows,
    }
    if raw_ptr:
        data["meta"]["rawFile"] = raw_ptr

    os.makedirs(data_dir, exist_ok=True)
    atomic_write(json_path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", backup=not args.no_backup)
    print("写入: %s (%d bytes)" % (json_path, os.path.getsize(json_path)))

    write_workbench(backup=not args.no_backup)
    write_launchers()

    if args.with_raw:
        seen = {}
        for it in items:
            seen[it["id"]] = it
        raw_items = sorted(seen.values(),
                           key=lambda r: (-(r.get("score") or 0), r.get("editTime") or ""))
        raw_dir = os.path.join(data_dir, "raw")
        os.makedirs(raw_dir, exist_ok=True)
        raw_path = os.path.join(raw_dir, "一堂作业正文-%s.json" % today)
        raw_data = {
            "version": 1,
            "meta": {
                "snapshotDate": today,
                "fetchedAt": now,
                "title": "一堂作业正文全文（API 返回归档，已清理不可见字符）",
                "source": "whyai yitang homework list（只读，%d 页 /api/answer/list）" % page_count,
                "itemCount": len(raw_items),
                "note": "字段为接口返回值（lessonName/score/isExcellentWork/answer/textCount/"
                        "commented/completed/rewardCode/editTime）。入库清洗仅针对不可见字符："
                        "U+2028/2029（行/段分隔符）→半角空格；零宽与双向控制残留（ZWSP/WJ/ZWNBSP/"
                        "LRM/RLM/BiDi）移除；emoji 组成字符（ZWJ/ZWNJ/变体选择符/键帽）与 NBSP 原样保留。"
                        "派生结构化清单见上级目录 %s.json。" % DATA_NAME,
            },
            "items": raw_items,
        }
        atomic_write(raw_path, json.dumps(raw_data, ensure_ascii=False, indent=1) + "\n",
                     backup=not args.no_backup)
        print("写入: %s（正文全文 %d 条，%d 字）"
              % (raw_path, len(raw_items), sum(i.get("textCount") or 0 for i in raw_items)))

    if args.serve:
        serve_in_background(data_dir)

    print("完成。快照 %s：%d 条作业 → %s" % (today, len(rows), data_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
