"""
Igor Petersson Agent — GUI backend server.
Usage: python gui/server.py
Opens http://localhost:7680 in the browser.
"""
import datetime
import json
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PORT = 8765
GUI_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = GUI_DIR.parent
LOG_FILE = GUI_DIR / 'session_logs.json'
MAX_LOGS = 50


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def parse_dotenv(path):
    """Parse a .env file into a dict. Returns {} if file missing."""
    config = {}
    try:
        for line in Path(path).read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, val = line.partition('=')
            config[key.strip()] = val.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return config


def mask_secret(val):
    """Mask API keys: sk-proj-abc... → sk-pro••••••••"""
    if val.startswith('sk-') and len(val) > 6:
        return val[:6] + '•' * 8
    return val


def load_logs(log_file):
    """Load session log list from JSON file."""
    try:
        return json.loads(Path(log_file).read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def append_log(log_file, entry):
    """Append a log entry, keeping at most MAX_LOGS entries."""
    logs = load_logs(log_file)
    logs.append(entry)
    if len(logs) > MAX_LOGS:
        logs = logs[-MAX_LOGS:]
    Path(log_file).write_text(json.dumps(logs, indent=2), encoding='utf-8')


# ---------------------------------------------------------------------------
# HTTP Handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silence default per-request logging

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path in ('/', '/index.html'):
            self._serve_file(GUI_DIR / 'index.html', 'text/html')
        elif path == '/api/run-tests':
            test_class = qs.get('class', [None])[0]
            self._stream_tests(test_class)
        elif path == '/api/config':
            self._serve_json(self._get_config())
        elif path == '/api/logs':
            self._serve_json(load_logs(LOG_FILE))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/run-agent':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            self._stream_agent(body.get('task', ''))
        elif parsed.path == '/api/logs/clear':
            LOG_FILE.unlink(missing_ok=True)
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    # --- helpers ---

    def _serve_file(self, path, content_type):
        try:
            data = path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', content_type + '; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_response(404)
            self.send_header('Connection', 'close')
            self.end_headers()

    def _serve_json(self, data):
        body = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)

    def _start_stream(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Transfer-Encoding', 'chunked')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def _write_chunk(self, data):
        try:
            encoded = data.encode('utf-8') if isinstance(data, str) else data
            self.wfile.write(f'{len(encoded):X}\r\n'.encode())
            self.wfile.write(encoded)
            self.wfile.write(b'\r\n')
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _end_stream(self):
        self._write_chunk('')

    def _stream_tests(self, test_class=None):
        self._start_stream()
        cmd = [
            'docker', 'compose', 'run', '--rm',
            '-v', f'{PROJECT_ROOT}/test_vg_requirements.py:/agent/test_vg_requirements.py',
            'react-agent', 'python', 'test_vg_requirements.py',
        ]
        if test_class:
            cmd.append(test_class)
        self._run_and_stream(cmd)

    def _stream_agent(self, task):
        self._start_stream()
        # Bypass main.py's interactive loop — call run_agent() directly so there
        # is no second input() call and no EOFError after the task completes.
        one_shot = (
            'import sys; sys.path.insert(0,"/agent/app"); '
            'from agent import run_agent; '
            f'run_agent({repr(task)})'
        )
        cmd = [
            'docker', 'compose', 'run', '--rm',
            '-e', 'DEBUG_RUNTIME_TRACING=true',
            '-e', 'ESTIMATED_COST_PER_1K_TOKENS=0.0010',
            'react-agent',
            'python', '-c', one_shot,
        ]
        start = datetime.datetime.now()
        output_lines = []

        try:
            proc = subprocess.Popen(
                cmd, cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )

            for line in proc.stdout:
                self._write_chunk(line)
                output_lines.append(line.rstrip())
            proc.wait()
        except Exception as e:
            err = f'Error running agent: {e}\n'
            self._write_chunk(err)
            output_lines.append(err.rstrip())

        self._end_stream()

        duration = (datetime.datetime.now() - start).total_seconds()
        append_log(LOG_FILE, {
            'timestamp': start.isoformat(),
            'task': task[:120],
            'duration_s': round(duration, 1),
            'lines': len(output_lines),
            'output': output_lines[-100:],
        })

    def _run_and_stream(self, cmd):
        try:
            proc = subprocess.Popen(
                cmd, cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            for line in proc.stdout:
                self._write_chunk(line)
            proc.wait()
        except Exception as e:
            self._write_chunk(f'Error: {e}\n')
        self._end_stream()

    def _get_config(self):
        env = parse_dotenv(PROJECT_ROOT / '.env')
        SECRET_KEYS = {'OPENAI_API_KEY', 'HUB_PASSWORD'}
        return {k: (mask_secret(v) if k in SECRET_KEYS else v) for k, v in env.items()}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    httpd = HTTPServer(('localhost', PORT), Handler)
    url = f'http://localhost:{PORT}'
    print(f'Igor Agent GUI — {url}')
    print(f'Project root: {PROJECT_ROOT}')
    print('Press Ctrl+C to stop.\n')
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')


if __name__ == '__main__':
    main()
