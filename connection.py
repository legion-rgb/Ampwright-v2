"""Attach to the running AWR and run COM calls on the one thread that owns it."""
import asyncio
import subprocess
from concurrent.futures import ThreadPoolExecutor

import pythoncom
import win32com.client

# COM objects must stay on the thread that created them: one worker thread owns AWR.
_com = ThreadPoolExecutor(1, initializer=pythoncom.CoInitialize)
_app = None


def awr():
    global _app
    if _app is not None:
        try:
            _app.Version
            return _app
        except Exception:
            _app = None
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq MWOffice.exe"], capture_output=True, text=True).stdout
    if "MWOffice.exe" not in out:
        # Dispatch would silently launch a new, empty AWR instead of failing.
        raise RuntimeError("AWR Microwave Office is not running. Open your project in AWR first.")
    # shortcut: attaches to whichever instance AWR hands out; with several AWR windows open, close the extras.
    _app = win32com.client.Dispatch("AWR.MWOffice")
    return _app


def find(coll, name):
    for item in coll:
        if item.Name == name:
            return item
    raise ValueError(f"'{name}' not found. Available: {[i.Name for i in coll]}")


async def run(fn, *args, timeout=900):
    """Run fn on the COM thread. A COM call cannot be interrupted: on timeout the caller gets an error at once,
    but the thread stays busy until the call returns, and later calls queue behind it."""
    try:
        return await asyncio.wait_for(asyncio.get_running_loop().run_in_executor(_com, fn, *args), timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"{fn.__name__} did not finish within {timeout}s; AWR may still be busy (check for a dialog or the Simulation Jobs window)") from None
