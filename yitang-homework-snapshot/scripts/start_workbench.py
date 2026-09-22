#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""启动本地静态服务并打开工作台（前端由此能真正读到数据目录的 JSON，而不是只看内嵌快照）。

为什么需要它：浏览器在 file:// 下会拦截页面读取 JSON（CORS）。经本地 http 服务打开后，
工作台会自动 fetch 数据文件，数据源与 JSON 始终一致。

双根服务：工作台前端在**技能内** `<技能>/workbench/`，数据在**数据目录**（config.json 的 data_dir）。
请求先在工作台根找，找不到再回落到数据根 —— 因此页面与数据无需放在同一目录。

用法：
  python3 start_workbench.py                    # 前台服务 + 自动开浏览器，Ctrl+C 停止
  python3 start_workbench.py --data 某目录       # 指定数据目录（默认读技能内 config.json）
  python3 start_workbench.py --port 8791        # 固定端口（默认自动选空闲端口）
  python3 start_workbench.py --no-browser       # 不起浏览器
  python3 start_workbench.py --quiet            # 不打印每条请求日志（后台运行时用）
  python3 start_workbench.py --stop             # 停止已启动的后台服务
"""
import argparse
import http.server
import json
import os
import signal
import socket
import socketserver
import sys
import threading
import urllib.parse
import webbrowser

PAGE_NAME = "一堂作业评分清单.html"
DATA_NAME = "一堂作业评分清单"
PID_FILE = ".workbench-server.pid"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
WORKBENCH_DIR = os.path.join(SKILL_ROOT, "workbench")
CONFIG_PATH = os.path.join(SKILL_ROOT, "config.json")
DEFAULT_DATA_DIR = os.path.expanduser("~/Documents/一堂作业工作台")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


def resolve_data_dir(cli_target):
    """数据目录：--data > 环境变量 > config.json 的 data_dir（相对路径按技能目录解析）> 内置默认。"""
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
        except Exception:
            cfg_dir = None
    if cfg_dir:
        cfg_dir = os.path.expanduser(str(cfg_dir))
        if not os.path.isabs(cfg_dir):
            cfg_dir = os.path.join(SKILL_ROOT, cfg_dir)
        return os.path.abspath(cfg_dir)
    return DEFAULT_DATA_DIR


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def pick_page(workbench_dir):
    """工作台目录里的 HTML（优先约定文件名）。"""
    p = os.path.join(workbench_dir, PAGE_NAME)
    if os.path.exists(p):
        return PAGE_NAME
    if os.path.isdir(workbench_dir):
        htmls = sorted(f for f in os.listdir(workbench_dir) if f.lower().endswith(".html"))
        if htmls:
            return htmls[0]
    return None


def make_handler(roots, quiet):
    """roots：按顺序查找的目录列表（工作台根在前、数据根在后）。"""
    base_cls = QuietHandler if quiet else http.server.SimpleHTTPRequestHandler

    class TwoRootHandler(base_cls):
        def translate_path(self, path):
            """按 roots 顺序找第一个存在的文件；去掉 .. 防目录穿越。"""
            p = urllib.parse.urlparse(path).path
            p = urllib.parse.unquote(p, errors="surrogatepass")
            parts = [seg for seg in p.split("/") if seg and seg not in (".", "..")]
            rel = os.path.join(*parts) if parts else ""
            for root in roots:
                cand = os.path.join(root, rel)
                if os.path.exists(cand):
                    return cand
            return os.path.join(roots[0], rel)

        def log_message(self, fmt, *args):
            if not quiet:
                base_cls.log_message(self, fmt, *args)

    return TwoRootHandler


def stop_server():
    pf = os.path.join(WORKBENCH_DIR, PID_FILE)
    if not os.path.exists(pf):
        print("没有找到服务记录（%s），可能未启动或已停止。" % pf)
        return 1
    try:
        with open(pf, encoding="utf-8") as fh:
            pid = int(fh.read().strip())
    except Exception as e:
        print("[STOP] PID 文件无法解析：%s" % e)
        return 2
    try:
        os.kill(pid, signal.SIGTERM)
        print("已发送停止信号：PID %d" % pid)
    except ProcessLookupError:
        print("进程 %d 已不存在。" % pid)
    except Exception as e:
        print("[STOP] 停止失败：%s（可手动 kill %d）" % (e, pid))
        return 2
    try:
        os.unlink(pf)
    except OSError:
        pass
    return 0


def serve(data_dir, port=None, open_browser=True, print_url=False, quiet=False):
    data_dir = os.path.abspath(data_dir)
    if not os.path.isdir(WORKBENCH_DIR):
        print("[STOP] 技能内没有 workbench/ 目录；请先运行 refresh_homework.py --confirm 生成工作台。")
        return 2
    page = pick_page(WORKBENCH_DIR)
    if not page:
        print("[STOP] %s 下没有 HTML 工作台；请先运行 refresh_homework.py --confirm 生成。" % WORKBENCH_DIR)
        return 2
    if not os.path.isdir(data_dir):
        print("[WARN] 数据目录尚不存在：%s（页面会提示未读到数据；先跑一次 --confirm 即可）" % data_dir)

    roots = [WORKBENCH_DIR, data_dir]
    port = port or free_port()
    handler = make_handler(roots, quiet)
    socketserver.TCPServer.allow_reuse_address = True
    try:
        httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    except OSError as e:
        print("[STOP] 端口 %d 不可用：%s（可换 --port 或省略以自动选端口）" % (port, e))
        return 2

    url = "http://127.0.0.1:%d/%s" % (port, urllib.parse.quote(page))
    try:
        os.makedirs(WORKBENCH_DIR, exist_ok=True)
        with open(os.path.join(WORKBENCH_DIR, PID_FILE), "w", encoding="utf-8") as fh:
            fh.write(str(os.getpid()))
    except OSError:
        pass
    if print_url:
        print(url, flush=True)
    print("工作台服务已就绪：%s" % url, flush=True)
    print("  工作台前端：%s" % WORKBENCH_DIR, flush=True)
    print("  数据目录：%s（页面将自动读取 %s.json）" % (data_dir, DATA_NAME), flush=True)
    print("停止：Ctrl+C（或 python3 start_workbench.py --stop）", flush=True)
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        httpd.server_close()
        try:
            os.unlink(os.path.join(WORKBENCH_DIR, PID_FILE))
        except OSError:
            pass
    return 0


def main():
    ap = argparse.ArgumentParser(description="启动工作台本地服务（前端读取数据目录的 JSON）")
    ap.add_argument("--data", default=None, help="数据目录（默认读技能内 config.json 的 data_dir）")
    ap.add_argument("--port", type=int, default=0, help="端口（默认 0 = 自动选空闲端口）")
    ap.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    ap.add_argument("--print-url", action="store_true", help="启动前先打印 URL（供程序读取）")
    ap.add_argument("--quiet", action="store_true", help="不打印每条请求日志")
    ap.add_argument("--stop", action="store_true", help="停止已启动的后台服务")
    args = ap.parse_args()
    if args.stop:
        return stop_server()
    return serve(resolve_data_dir(args.data), args.port, not args.no_browser, args.print_url, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
