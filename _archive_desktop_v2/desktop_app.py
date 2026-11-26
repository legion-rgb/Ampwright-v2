# /// script
# requires-python = ">=3.10"
# dependencies = ["pywin32", "pywebview"]
# ///
"""Fieldnote desktop interface for AWR Microwave Office: a window onto the AWRMWO-mcp hub pipe."""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fieldnote_client as fc

UI = os.path.join(HERE, "ui")
SETTINGS = os.path.join(os.environ.get("APPDATA", HERE), "Fieldnote", "settings.json")


def build_page():
    def rd(n):
        with open(os.path.join(UI, n), encoding="utf-8") as f:
            return f.read()

    page = rd("index.html")
    css, js = rd("styles.css"), rd("app.js").replace("</script", "<\\/script")
    page = re.sub(r'<link[^>]*href="/?styles\.css"[^>]*>', lambda m: "<style>\n" + css + "\n</style>", page)
    return re.sub(r'<script[^>]*src="/?app\.js"[^>]*></script>', lambda m: "<script>\n" + js + "\n</script>", page)


def _find_claude():
    hits = sorted(glob.glob(os.path.expanduser(
        r"~\.vscode\extensions\anthropic.claude-code-*\resources\native-binary\claude.exe")))
    return hits[-1] if hits else (shutil.which("claude") or "")  # shortcut: lexical sort, not semver


def _defaults():
    return {"workspace": os.path.dirname(HERE), "claude_path": _find_claude(), "mode": "linked"}


def _safe(fn):
    def w(*a, **kw):
        try:
            return {"result": fn(*a, **kw)}
        except Exception as e:
            return {"error": str(e) or repr(e)}
    w.__name__ = fn.__name__
    return w


class Api:
    def __init__(self):  # private attrs: pywebview exposes public ones to JS and would walk the Window object
        self._window = None
        self._client = None

    def _push(self, ev):
        try:
            if self._window:
                self._window.evaluate_js("window.fieldnoteEvent && window.fieldnoteEvent(" + json.dumps(ev) + ")")
        except Exception:
            pass  # window not ready or closing

    def _req(self, call, args=None):
        if not self._client:
            raise RuntimeError("not connected")
        return self._client.request(call, args)

    @_safe
    def sessions(self):
        return fc.list_sessions()

    @_safe
    def connect(self, pid):
        s = next((s for s in fc.list_sessions() if s["pid"] == int(pid)), None)
        if not s:
            raise RuntimeError("no live session with pid %s" % pid)
        if self._client:
            self._client.close()
            self._client = None
        got, ready = [], threading.Event()

        def on_event(ev):
            if ev.get("event") == "hello" and not ready.is_set():
                got.append(ev)
                ready.set()
            else:
                self._push(ev)

        c = fc.PipeClient(s["pipe"], on_event)
        if not ready.wait(5):
            c.close()
            raise RuntimeError("no hello from the session")
        self._client = c
        return got[0]

    @_safe
    def call(self, tool, args=None):
        return self._req(tool, args or {})

    @_safe
    def chat(self, text):
        return self._req("chat", {"text": text})

    @_safe
    def permission(self, request_id, behavior):
        return self._req("permission", {"request_id": request_id, "behavior": behavior})

    @_safe
    def activity(self, since=0):
        return self._req("activity", {"since": since})

    def _settings(self):
        s = _defaults()
        try:
            with open(SETTINGS, encoding="utf-8") as f:
                s.update(json.load(f))
        except (OSError, ValueError):
            pass
        return s

    @_safe
    def settings(self):
        s = self._settings()
        s["claude_found"] = bool(s["claude_path"]) and os.path.isfile(s["claude_path"])
        return s

    @_safe
    def save_settings(self, obj):
        s = self._settings()
        s.update({k: obj[k] for k in ("workspace", "claude_path", "mode") if k in obj})
        os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
        return s

    @_safe
    def start_linked_session(self):
        s = self._settings()
        if not s["claude_path"]:
            raise RuntimeError("claude.exe not found; set claude_path in settings")
        cmd = ["cmd", "/c", "start", "Fieldnote linked session", "cmd", "/k", s["claude_path"],
               "--dangerously-load-development-channels", "server:AWRMWO-mcp"]
        subprocess.Popen(cmd, cwd=s["workspace"])
        return {"started": True, "command": subprocess.list2cmdline(cmd)}


def check():
    for n in ("index.html", "styles.css", "app.js"):
        assert os.path.isfile(os.path.join(UI, n)), n + " missing"
    page = build_page()
    assert "Fieldnote" in page, "page lacks Fieldnote"
    print("OK: ui files present, page %d bytes, %d live session(s)" % (len(page), len(fc.list_sessions())))


def main():
    if "--check" in sys.argv:
        return check()
    import webview
    api = Api()
    api._window = webview.create_window("Fieldnote — AWR Circuit Studio", html=build_page(), js_api=api,
                                       width=1440, height=960, min_size=(1024, 720), background_color="#101412")
    webview.start(http_server=False)


if __name__ == "__main__":
    main()
