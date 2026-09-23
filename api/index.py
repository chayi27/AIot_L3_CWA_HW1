"""
Vercel Serverless Function Entrypoint: api/index.py
依據 Vercel 官方文檔標準：實作 BaseHTTPRequestHandler 與 handler 類別及 WSGI 支援
(https://vercel.com/docs/functions/runtimes/python)
"""

from http.server import BaseHTTPRequestHandler
import sys
import os

# 加入專案根目錄至 sys.path 以便匯入模組
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import generate_vercel_html


class handler(BaseHTTPRequestHandler):
    """Vercel BaseHTTPRequestHandler 入口點"""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'public, max-age=60')
        self.end_headers()
        try:
            html_content = generate_vercel_html()
            self.wfile.write(html_content.encode('utf-8'))
        except Exception as e:
            err_html = f"<html><body><h2>Error generating weather map</h2><pre>{e}</pre></body></html>"
            self.wfile.write(err_html.encode('utf-8'))
        return


def wsgi_app(environ, start_response):
    """Vercel WSGI 入口點"""
    status = '200 OK'
    headers = [
        ('Content-type', 'text/html; charset=utf-8'),
        ('Cache-Control', 'public, max-age=60')
    ]
    start_response(status, headers)
    try:
        body = generate_vercel_html()
        return [body.encode('utf-8')]
    except Exception as e:
        err_html = f"<html><body><h2>Error generating weather map</h2><pre>{e}</pre></body></html>"
        return [err_html.encode('utf-8')]


# 頂級別名導出
app = wsgi_app
application = wsgi_app
