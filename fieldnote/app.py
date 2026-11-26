# /// script
# requires-python = ">=3.10"
# dependencies = ["pywin32", "pywebview"]
# ///
"""Fieldnote: a desktop front-end for Claude Code doing AWR work. Starts a hidden Claude Code session on the
user's subscription, attaches to that session's AWRMWO-mcp hub pipe, and shows the open AWR project."""
import ctypes
import json
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pipe as pipe_mod
import session as session_mod

UI = os.path.join(HERE, "ui")
WORKSPACE = os.path.dirname(os.path.dirname(HERE))  # workspace: project CLAUDE.md rules load from here
SETTINGS = os.path.join(os.environ.get("APPDATA", HERE), "Fieldnote", "settings.json")
PIPE = r"\\.\pipe\AWRMWO-%s-fieldnote-%d" % (os.environ.get("USERNAME", "user"), os.getpid())
HISTORY = os.path.join(os.path.dirname(SETTINGS), "history.json")
HISTORY_MAX = 500  # items kept on disk
TOOL_PREFIX = "mcp__AWRMWO-mcp__"
APPROVE_WAIT = 120  # seconds; the server denies on its own after this (hub.APPROVE_TIMEOUT), so the dialog closes too
POLL_S = 10  # project refresh; read-only pipe call, costs no Claude tokens


class FLASHWINFO(ctypes.Structure):  # winuser.h, for FlashWindowEx
    _fields_ = [("cbSize", ctypes.c_uint), ("hwnd", ctypes.c_void_p), ("dwFlags", ctypes.c_ulong),
                ("uCount", ctypes.c_uint), ("dwTimeout", ctypes.c_ulong)]


def build_page():
    def rd(n):
        with open(os.path.join(UI, n), encoding="utf-8") as f:
            return f.read()
    page = rd("index.html")
    page = page.replace('<link rel="stylesheet" href="app.css">', "<style>\n" + rd("app.css") + "\n</style>")
    js = rd("app.js").replace("</script", "<\\/script")
    return page.replace('<script src="app.js"></script>', "<script>\n" + js + "\n</script>")


def load_settings():
    s = {"theme": "dark", "model": ""}
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            s.update(json.load(f))
    except (OSError, ValueError):
        pass
    return s


def load_history():
    try:
        with open(HISTORY, encoding="utf-8") as f:
            items = json.load(f)
    except (OSError, ValueError):
        return []
    for it in items:
        if it.get("kind") == "step" and it.get("status") == "running":
            it["status"] = "stopped"  # the app closed while this step was running
        elif it.get("kind") == "approval" and it.get("status") == "waiting":
            it["status"] = "expired"
    return items


def summarize(inp):
    """'name=rc_lpf, model=RES' for a step row; long values are cut."""
    parts = []
    for k, v in (inp or {}).items():
        v = v if isinstance(v, (str, int, float, bool)) else json.dumps(v, default=str)
        parts.append("%s=%s" % (k, str(v)[:30]))
    return ", ".join(parts)[:90]


class Api:
    def __init__(self, claude_path=None, extra_args=None):  # private attrs: pywebview exposes public ones to JS
        self._window = None
        self._claude_path = claude_path
        self._extra_args = extra_args
        self._session = None
        self._client = None
        self._lock = threading.Lock()
        self._state = {"claude": "off", "awr": "off", "detail": "Starting…", "project": None, "turn": "idle"}
        self._stop = threading.Event()
        self._history = load_history()
        self._hlock = threading.Lock()
        self._refreshing = False

    # ---- state shared with the page: the page pulls it on load and gets every change pushed ----
    def _set(self, **kw):
        with self._lock:
            self._state.update(kw)
            snap = dict(self._state)
        if self._window:
            try:
                self._window.evaluate_js("window.fieldnote && window.fieldnote.onState(%s)" % json.dumps(snap))
            except Exception:
                pass  # window not ready or closing; the page pulls state() on load

    def state(self):
        with self._lock:
            return dict(self._state)

    # ---- history: the chat and every step, saved so the next start shows what happened ----
    def _push_history(self):
        if self._window:
            try:
                self._window.evaluate_js("window.fieldnote && window.fieldnote.onHistory(%s)" % json.dumps(self._history))
            except Exception:
                pass

    def _commit(self):  # call with _hlock held
        self._history = self._history[-HISTORY_MAX:]
        try:
            os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
            with open(HISTORY, "w", encoding="utf-8") as f:
                json.dump(self._history, f)
        except OSError:
            pass  # shortcut: a full disk loses history, never the running task
        self._push_history()

    def _add(self, item):
        item["t"] = time.strftime("%H:%M:%S")
        with self._hlock:
            self._history.append(item)
            self._commit()

    def _update_step(self, sid, **kw):
        with self._hlock:
            for it in reversed(self._history):
                if it.get("kind") == "step" and it.get("id") == sid:
                    it.update(kw)
                    break
            self._commit()

    def _stop_running_steps(self):
        with self._hlock:
            for it in self._history:
                if it.get("kind") == "step" and it.get("status") == "running":
                    it["status"] = "stopped"
            self._commit()

    # ---- approvals: save, new project and delete ask the user; the hub denies if nobody answers ----
    def _resolve(self, rid, status):
        """Close a waiting approval. True if it was still waiting."""
        with self._hlock:
            for it in self._history:
                if it.get("kind") == "approval" and it.get("id") == rid and it.get("status") == "waiting":
                    it["status"] = status
                    self._commit()
                    return True
        return False

    def _expire_all(self):
        with self._hlock:
            waiting = [it["id"] for it in self._history if it.get("kind") == "approval" and it.get("status") == "waiting"]
        for rid in waiting:
            self._resolve(rid, "expired")

    def _ask(self, ev):
        rid = ev.get("request_id")
        if not rid:
            return
        self._add({"kind": "approval", "id": rid, "tool": ev.get("tool_name") or "", "preview": ev.get("input_preview") or "",
                   "status": "waiting"})
        t = threading.Timer(APPROVE_WAIT, self._resolve, (rid, "expired"))
        t.daemon = True
        t.start()
        if self._window:  # the user is probably in AWR. Own thread: a stuck window call must never block the pipe reader
            threading.Thread(target=self._call_attention, args=(self._window,), daemon=True).start()

    @staticmethod
    def _call_attention(w):
        # Not w.on_top: pywebview sets TopMost off the UI thread, which froze the window (25 Nov 2026)
        try:
            w.restore()  # pywebview marshals this onto the UI thread
            hwnd = ctypes.windll.user32.FindWindowW(None, w.title)
            if hwnd:  # flash caption and taskbar button until the window comes to the front (FLASHW_ALL | FLASHW_TIMERNOFG)
                fi = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, 0x3 | 0xC, 0, 0)
                ctypes.windll.user32.FlashWindowEx(ctypes.byref(fi))
        except Exception:
            pass

    def answer(self, rid, behavior):
        if behavior not in ("allow", "deny"):
            return {"ok": False, "error": "Answer must be allow or deny."}
        with self._hlock:
            waiting = any(it.get("kind") == "approval" and it.get("id") == rid and it.get("status") == "waiting"
                          for it in self._history)
        if not waiting:
            return {"ok": False, "error": "That request already ended."}
        if not self._client:
            return {"ok": False, "error": "Not connected to the AWR server."}
        try:
            self._client.request("permission", {"request_id": rid, "behavior": behavior}, timeout=10)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        self._resolve(rid, "allowed" if behavior == "allow" else "denied")
        return {"ok": True}

    def history(self):
        with self._hlock:
            return list(self._history)

    def clear_history(self):
        with self._hlock:
            self._history = []
            self._commit()
        return True

    # ---- chat ----
    def send(self, text):
        text = (text or "").strip()
        st = self.state()
        if not text:
            return {"ok": False, "error": "Type a task first."}
        if st["claude"] != "up" or not self._session:
            return {"ok": False, "error": "Claude Code isn't running yet. Select Reconnect."}
        if st["turn"] == "working":
            return {"ok": False, "error": "Claude is still working on the last task."}
        self._add({"kind": "user", "text": text})
        self._set(turn="working")
        try:
            self._session.send(text)
        except Exception as e:
            self._set(turn="idle")
            self._add({"kind": "note", "text": "Could not send the task: %s" % e})
            return {"ok": False, "error": str(e)}
        return {"ok": True}

    def stop_turn(self):
        if self._state["turn"] != "working":
            return False
        self._stop_running_steps()
        self._expire_all()
        self._add({"kind": "note", "text": "Stopped. AWR may still finish the step it was on."})
        self._set(turn="idle")
        threading.Thread(target=self._restart, daemon=True).start()
        return True

    def _restart(self):  # Stop kills Claude Code and its AWR server; start both again, same conversation
        self._close_client()
        if self._session:
            self._session.stop()
        self._boot()

    # ---- connection ----
    def _boot(self):
        path = self._claude_path or session_mod.find_claude()
        if not (path and os.path.isfile(path)):
            return self._set(claude="error", detail="Claude Code wasn't found. Install the Claude Code extension in VS Code.")
        self._set(claude="connecting", awr="off", detail="Starting Claude Code…")
        sid = self._session.session_id if self._session else None  # keep the conversation across restarts
        self._session = session_mod.Session(path, WORKSPACE, PIPE, self._on_session, load_settings()["model"] or None,
                                            self._extra_args)
        self._session.session_id = sid
        self._session.start()
        end = time.time() + 45
        while time.time() < end and not self._stop.is_set():
            if not self._session.running():
                tail = " ".join(list(self._session.stderr_tail)[-3:])
                return self._set(claude="error", detail="Claude Code stopped while starting. " + tail)
            try:
                self._client = pipe_mod.PipeClient(PIPE, self._on_pipe)
                break
            except Exception:
                time.sleep(0.4)  # the AWR server is still starting
        else:
            return self._set(claude="error", detail="The AWR server didn't start. Check that uv is installed.")
        self._set(claude="up", awr="connecting", detail="Reading the AWR project…")
        self._refresh()

    def _refresh(self):
        if not self._client:
            return
        try:
            info = self._client.request("project_info", {}, timeout=60)
            self._set(awr="up", project=info, detail="")
        except Exception as e:
            msg = str(e)
            if "not running" in msg:
                msg = "AWR Microwave Office isn't running. Open your project in AWR, then select Reconnect."
            self._set(awr="error", project=None, detail=msg)

    def _poll(self):
        while not self._stop.wait(POLL_S):
            if self._client and self._state["claude"] == "up":
                self._refresh()

    def _refresh_async(self):  # after Claude changed AWR; one at a time so slow AWR calls don't pile up
        if self._refreshing or not self._client:
            return
        self._refreshing = True

        def go():
            try:
                self._refresh()
            finally:
                self._refreshing = False
        threading.Thread(target=go, daemon=True).start()

    def _on_session(self, ev):
        k = ev.get("event")
        if k == "reply":
            self._add({"kind": "claude", "text": ev["text"]})
        elif k == "tool_use":
            self._add({"kind": "step", "id": ev.get("id"), "tool": (ev.get("tool") or "").removeprefix(TOOL_PREFIX),
                       "summary": summarize(ev.get("input")), "status": "running"})
        elif k == "tool_result":
            bad = ev.get("is_error")
            self._update_step(ev.get("id"), status="failed" if bad else "done", **({"error": ev.get("text")} if bad else {}))
            if not bad:
                self._refresh_async()
        elif k == "turn_end":
            self._stop_running_steps()
            self._expire_all()
            if ev.get("is_error"):
                self._add({"kind": "note", "text": "Claude Code ended the task with an error."})
            self._set(turn="idle")
            self._refresh_async()
        elif k == "session_exited" and not self._stop.is_set():
            self._stop_running_steps()
            self._expire_all()
            self._add({"kind": "note", "text": "Claude Code stopped during the task."})
            self._close_client()
            self._set(claude="error", awr="off", turn="idle", detail="Claude Code stopped. Select Reconnect to start it again.")

    def _on_pipe(self, ev):
        if ev.get("event") == "permission_request":
            return self._ask(ev)
        if ev.get("event") == "disconnected" and not self._stop.is_set():
            self._expire_all()
            self._set(claude="error", awr="off", detail="Lost the AWR server. Select Reconnect.")

    def _close_client(self):
        c, self._client = self._client, None
        if c:
            c.close()

    def start(self):
        threading.Thread(target=self._boot, daemon=True).start()
        threading.Thread(target=self._poll, daemon=True).start()

    def reconnect(self):
        if self._state["claude"] == "up":  # only AWR needs another look
            threading.Thread(target=self._refresh, daemon=True).start()
            return True
        self._close_client()
        if self._session:
            self._session.stop()
        threading.Thread(target=self._boot, daemon=True).start()
        return True

    def shutdown(self):
        self._stop.set()
        self._close_client()
        if self._session:
            self._session.stop()  # no orphan claude.exe or server

    # ---- settings ----
    def settings(self):
        return load_settings()

    def save_settings(self, obj):
        s = load_settings()
        s.update({k: obj[k] for k in ("theme", "model") if k in obj})
        os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
        return s


def main():
    import webview
    api = Api()
    api._window = webview.create_window("Fieldnote", html=build_page(), js_api=api, width=1360, height=880,
                                       min_size=(980, 640), background_color="#0c1a1f")
    api._window.events.closed += api.shutdown
    webview.start(api.start, http_server=False)
    api.shutdown()


if __name__ == "__main__":
    main()
