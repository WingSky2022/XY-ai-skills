#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""启动本地静态服务并打开工作台（前端由此能真正读到同名 JSON，而不是只看内嵌快照）。

为什么需要它：浏览器在 file:// 下会拦截页面读取同目录 JSON（CORS）。经本地 http 服务打开后，
工作台会自动 fetch 数据文件，数据源与 JSON 始终一致。

用法：
  python3 start_workbench.py                    # 服务当前目录（前台，Ctrl+C 停止）
  python3 start_workbench.py --dir 某目录        # 服务指定目录
  python3 start_workbench.py --port 8791        # 固定端口（默认自动选空闲端口）
  python3 start_workbench.py --no-browser       # 不起浏览器
  python3 start_workbench.py --quiet            # 不打印每条请求日志（后台运行时用）
  python3 start_workbench.py --dir 某目录 --stop  # 停止该目录下已启动的后台服务
"""
import argparse
import http.server
import os
import signal
import socket
import socketserver
import sys
import threading
import urllib.parse
import webbrowser

DEFAULT_PAGE = "一堂作业评分清单.html"
PID_FILE = ".workbench-server.pid"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def pick_page(directory):
    p = os.path.join(directory, DEFAULT_PAGE)
    if os.path.exists(p):
        return DEFAULT_PAGE
    htmls = sorted(f for f in os.listdir(directory) if f.lower().endswith(".html"))
    return htmls[0] if htmls else None


def stop_server(directory):
    """停止该目录下由本脚本启动的后台服务（按 PID 文件）。"""
    pf = os.path.join(os.path.abspath(directory), PID_FILE)
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


def serve(directory, port=None, open_browser=True, print_url=False, quiet=False):
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        print("[STOP] 目录不存在：%s" % directory)
        return 2
    page = pick_page(directory)
    if not page:
        print("[STOP] %s 下没有 HTML 工作台；请先运行 refresh_homework.py 生成。" % directory)
        return 2

    port = port or free_port()
    base = QuietHandler if quiet else http.server.SimpleHTTPRequestHandler
    handler = lambda *a, **kw: base(*a, directory=directory, **kw)
    socketserver.TCPServer.allow_reuse_address = True
    try:
        httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    except OSError as e:
        print("[STOP] 端口 %d 不可用：%s（可换 --port 或省略以自动选端口）" % (port, e))
        return 2

    url = "http://127.0.0.1:%d/%s" % (port, urllib.parse.quote(page))
    try:
        with open(os.path.join(directory, PID_FILE), "w", encoding="utf-8") as fh:
            fh.write(str(os.getpid()))
    except OSError:
        pass
    if print_url:
        print(url, flush=True)
    print("后台服务已就绪：%s" % url, flush=True)
    print("数据源：%s（页面将自动读取同名 JSON）" % os.path.join(directory, os.path.splitext(page)[0] + ".json"), flush=True)
    print("停止：Ctrl+C（或 python3 start_workbench.py --dir %s --stop）" % directory, flush=True)
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        httpd.server_close()
        try:
            os.unlink(os.path.join(directory, PID_FILE))
        except OSError:
            pass
    return 0


def main():
    ap = argparse.ArgumentParser(description="启动工作台本地服务（前端读取同名 JSON）")
    ap.add_argument("--dir", default=os.getcwd(), help="数据所在目录（默认当前目录）")
    ap.add_argument("--port", type=int, default=0, help="端口（默认 0 = 自动选空闲端口）")
    ap.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    ap.add_argument("--print-url", action="store_true", help="启动前先打印 URL（供程序读取）")
    ap.add_argument("--quiet", action="store_true", help="不打印每条请求日志")
    ap.add_argument("--stop", action="store_true", help="停止该目录下已启动的后台服务")
    args = ap.parse_args()
    if args.stop:
        return stop_server(args.dir)
    return serve(args.dir, args.port, not args.no_browser, args.print_url, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
