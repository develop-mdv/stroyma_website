"""GET-only local gzip proxy to measure compression without a Docker daemon.

An approximation of compression only, not a production Nginx/Gunicorn load test.
"""
import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError


class Proxy(BaseHTTPRequestHandler):
    def do_GET(self):
        upstream = Request('http://127.0.0.1:8000' + self.path,
                           headers={'Accept-Encoding': 'identity', 'Host': 'localhost',
                                    'Cookie': self.headers.get('Cookie', '')})
        try:
            response = urlopen(upstream, timeout=60)
        except HTTPError as error:
            response = error
        with response:
            body = response.read()
            compress = ('gzip' in self.headers.get('Accept-Encoding', '') and len(body) >= 1024
                        and any(kind in response.headers.get('Content-Type', '')
                                for kind in ('text/', 'javascript', 'json', 'svg')))
            if compress:
                body = gzip.compress(body, compresslevel=5)
            self.send_response(response.status)
            for name, value in response.headers.items():
                if name.lower() not in ('content-length', 'transfer-encoding', 'content-encoding', 'connection'):
                    self.send_header(name, value)
            if compress:
                self.send_header('Content-Encoding', 'gzip')
                self.send_header('Vary', 'Accept-Encoding')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    print('Compression-only preview: http://127.0.0.1:8001', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8001), Proxy).serve_forever()
