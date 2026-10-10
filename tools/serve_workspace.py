# -*- coding: utf-8 -*-
"""
即梦分镜师 · 工作台本地服务
启动一个本地 HTTP 服务，提供:
  - 静态文件服务（可打开所有分镜 HTML 视图）
  - /refresh 接口：重新扫描并刷新工作台.html
用法: python tools/serve_workspace.py [端口，默认 8731]
"""
import os
import functools
import http.server
import socketserver
import sys
import urllib.parse
import importlib
import socket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_workspace

ROOT = gen_workspace.ROOT
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8731


def already_running(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        return s.connect_ex(("127.0.0.1", port)) == 0


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/refresh":
            try:
                importlib.reload(gen_workspace)
                path, plays, eps, done = gen_workspace.generate()
                body = ("工作台已刷新: %d 个剧本, %d 集, %d 集已完成" % (plays, eps, done)).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            except Exception as e:  # noqa: BLE001
                body = ("刷新失败: %s" % e).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        super().do_GET()

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.address_string(), fmt % args))


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    if already_running(PORT):
        print("工作台服务已在运行，不再重复启动")
        sys.exit(0)
    Handler = functools.partial(Handler)
    Server.allow_reuse_address = False
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        print("工作台服务已启动: http://127.0.0.1:%d/工作台.html" % PORT)
        print("按 Ctrl+C 停止")
        httpd.serve_forever()
