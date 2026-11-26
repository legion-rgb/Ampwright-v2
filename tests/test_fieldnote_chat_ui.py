# /// script
# dependencies = ["pywin32", "pywebview"]
# ///
"""Chat page in a hidden window with the fake claude: type a task, watch steps, Stop, history, Clear. No AWR."""
import os
import sys
import tempfile
import time

os.environ["APPDATA"] = tempfile.mkdtemp()
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "fieldnote"))
import app
import session
import webview

api = app.Api(claude_path=sys.executable, extra_args=[os.path.join(HERE, "fake_claude.py")])
api._session = session.Session(sys.executable, HERE, "pipe", api._on_session, None, api._extra_args)
api._boot = lambda: None  # a restart after Stop needs no AWR server here
w = webview.create_window("test_chat", html=app.build_page(), js_api=api, hidden=True)
api._window = w
out = {}
q = w.evaluate_js


def until(js, what, s=10):
    end = time.time() + s
    while time.time() < end:
        v = q(js)
        if v:
            return v
        time.sleep(0.1)
    raise AssertionError("timed out: " + what)


def say(text):
    q("$('task').value = %r; $('send').click(); 1" % text)


def run():
    time.sleep(3)
    try:
        out["off"] = q("$('task').disabled")  # Claude not up yet: can't type
        api._set(claude="up", awr="up")
        until("!$('task').disabled", "input enabled")
        out["empty"] = q("$('feed').hidden && !$('feedEmpty').hidden")

        say("hello")
        until("document.querySelectorAll('.step[data-status=done]').length == 1", "done step")
        out["turn1"] = q("[$('feed').hidden, document.querySelector('.msg.user').textContent, document.querySelector('.msg.claude').textContent,"
                         " document.querySelector('.step .tool').textContent, document.querySelector('.step .sum').textContent,"
                         " $('working').hidden, $('task').value].join('|')")

        say("fail it")
        until("document.querySelectorAll('.step[data-status=failed]').length == 1", "failed step")
        out["failed"] = q("document.querySelector('.step[data-status=failed] .err').textContent")

        say("hang")
        until("document.querySelector('.step[data-status=running]')", "running step")
        out["working"] = q("[!$('working').hidden, !$('stop').hidden, $('send').hidden, $('task').disabled].join('|')")
        q("$('stop').click(); 1")
        until("document.querySelector('.step[data-status=stopped]')", "stopped step")
        out["stopped"] = q("[$('working').hidden, $('stop').hidden, !$('send').hidden, document.querySelector('.note').textContent].join('|')")

        before = q("document.querySelectorAll('#feed > *').length")
        q("$('clear').click(); 1")  # first click only arms it
        time.sleep(0.5)
        out["armed"] = q("[!$('feed').hidden, $('clear').textContent, $('clear').dataset.armed].join('|')")
        q("$('clear').click(); 1")
        until("$('feed').hidden", "cleared")
        out["disarmed"] = q("$('clear').textContent")
        out["cleared"] = [before > 8, q("!$('feedEmpty').hidden")]
        out["errors"] = q("$('bannerText').textContent")
    except Exception as e:
        out["error"] = repr(e)
    api._session.stop()
    w.destroy()


webview.start(run)
assert "error" not in out, out
assert out["off"] is True and out["empty"] is True, out
assert out["turn1"] == "false|hello|echo hello resume=False|create schematic|name=rc_lpf|true|", out
assert out["failed"] == "no such schematic", out
assert out["working"] == "true|true|true|true", out
assert out["stopped"].startswith("true|true|true|Stopped."), out
assert out["cleared"] == [True, True] and out["errors"] == "", out
assert out["armed"] == "true|Clear all?|1" and out["disarmed"] == "Clear", out
print("OK: type a task, steps show done/failed/stopped, working bar and Stop, Clear needs a second click")
