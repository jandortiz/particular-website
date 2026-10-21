"""Local preview. --test enables isolated browser fixtures; never deployed."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import argparse
from copy import deepcopy
from build import load_content, render_site

ROOT = Path(__file__).resolve().parent.parent

class Preview(SimpleHTTPRequestHandler):
    fixtures = False

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_GET(self):
        path = urlsplit(self.path).path
        if self.fixtures and path.startswith('/__test__/'):
            parts = path.strip('/').split('/')
            mode = parts[1] if len(parts) > 1 else ''
            if mode not in {'no-js','blocked-storage','zoom','motion','fresh','large'}:
                self.send_error(404)
                return
            language = 'en' if len(parts) > 2 and parts[2] == 'en' else 'es'
            html = (ROOT / ('en/index.html' if language == 'en' else 'index.html')).read_text()
            if mode == 'large':
                catalog, translations = load_content()
                example = next(p for p in catalog['projects'] if p['group'] == 'other')
                for index in range(len(catalog['projects']) + 1, 101):
                    project = deepcopy(example)
                    project['id'] = f'fixture-{index}'
                    project['name'] = f'Test project {index}'
                    catalog['projects'].append(project)
                html = render_site(catalog, translations)['en/index.html' if language == 'en' else 'index.html']
            before = ''
            if mode == 'blocked-storage':
                before = '<script>Object.defineProperty(window,"localStorage",{get(){throw new DOMException("Test: storage blocked","SecurityError")}});</script>'
            elif mode == 'fresh':
                before = '<script>try{localStorage.removeItem("jandortiz-theme")}catch{}</script>'
            elif mode == 'zoom':
                before = '<style>html{zoom:2}</style>'
            elif mode == 'motion':
                css = (ROOT/'css/styles.css').read_text().split('@media (prefers-reduced-motion: reduce) {',1)[1].split('\n}',1)[0]
                before = f'<style>{css}</style>'
            if mode == 'motion':
                html = html.replace('</head>', before+'</head>')
            else:
                html = html.replace('<script src="/js/theme.js">', before+'<script src="/js/theme.js">')
            body = html.encode()
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            if mode == 'no-js': self.send_header('Content-Security-Policy', "script-src 'none'")
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=5501)
    parser.add_argument('--test',action='store_true')
    args=parser.parse_args()
    Preview.fixtures=args.test
    print(f'Preview: http://127.0.0.1:{args.port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),partial(Preview,directory=str(ROOT))).serve_forever()
