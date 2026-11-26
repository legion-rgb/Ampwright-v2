# /// script
# dependencies = ["pywin32", "pywebview"]
# ///
"""Ampwright window without Claude or AWR: the page renders backend states, shows faults, and saves the theme."""
import os, sys, tempfile, time
os.environ["APPDATA"] = tempfile.mkdtemp()  # never touch the user's settings
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ampwright"))
import app
import webview

PROJECT = {"project": "Demo.emp", "file": r"C:\work\Demo.emp", "saved": False, "schematics": ["v2_rc_lpf"],
           "graphs": ["v2_rc_lpf_s"], "em_structures": [], "netlists": []}
api, out = app.Api(claude_path=r"C:\nowhere\claude.exe"), {}
w = webview.create_window("test_ampwright", html=app.build_page(), js_api=api, hidden=True)
api._window = w
q = lambda code: w.evaluate_js(code)


def run():
    time.sleep(3)
    try:
        out["started"] = q("typeof window.ampwright === 'object'")
        api._set(claude="up", awr="up", project=PROJECT, detail="")
        time.sleep(0.3)
        out["up"] = q("[$('projectName').textContent, $('awrState').textContent, $('nSchematics').textContent,"
                      " document.querySelector('.seg[data-seg=awr]').dataset.state, $('banner').hidden,"
                      " $('projectSaved').textContent].join('|')")
        api._set(awr="error", project=None, detail="AWR Microwave Office isn't running. Open your project in AWR, then select Reconnect.")
        time.sleep(0.3)
        out["awr_down"] = q("[$('banner').hidden, $('bannerText').textContent.includes('isn\\'t running'), $('projectCard').hidden].join('|')")
        api._boot()  # no claude.exe at that path: must say so, not hang
        time.sleep(0.3)
        out["no_claude"] = q("$('bannerText').textContent")
        q("$('theme').click(); 1")
        time.sleep(0.8)
        out["theme"] = q("document.documentElement.dataset.theme")
        out["errors"] = q("$('bannerText').textContent.includes('window hit an error')")
    except Exception as e:
        out["error"] = repr(e)
    w.destroy()


webview.start(run)
assert "error" not in out, out
assert out["started"] is True, out
assert out["up"] == "Demo|Demo|1|up|true|Unsaved changes in AWR", out
assert out["awr_down"] == "false|true|true", out
assert "wasn't found" in out["no_claude"], out
assert out["theme"] == "light" and app.load_settings()["theme"] == "light", out
assert out["errors"] is False, out
print("OK: states render, faults show in the banner, missing Claude Code is reported, theme saved")
