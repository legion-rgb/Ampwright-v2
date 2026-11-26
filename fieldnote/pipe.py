"""Client for the AWRMWO hub named pipe (see ../hub.py): JSON lines, requests by id, pushed events."""
import itertools
import json
import threading
import time

import pywintypes
import win32file
import win32pipe


class PipeClient:
    def __init__(self, pipe_name, on_event):
        self.on_event = on_event
        self.h = win32file.CreateFile(pipe_name, win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None,
                                      win32file.OPEN_EXISTING, 0, None)
        self._wlock = threading.Lock()
        self._ids = itertools.count(1)
        self._waiting = {}  # id -> [Event, message]
        self._closed = False
        self._lost = False
        threading.Thread(target=self._reader, daemon=True).start()

    def _lose(self):
        with self._wlock:
            if self._lost:
                return
            self._lost = True
        for w in list(self._waiting.values()):
            w[1] = {"error": "pipe disconnected"}
            w[0].set()
        if not self._closed:
            self.on_event({"event": "disconnected"})

    def _reader(self):
        buf = b""
        try:
            while not self._closed:
                n = win32pipe.PeekNamedPipe(self.h, 0)[1]  # poll: a blocking read would block our writes
                if not n:
                    time.sleep(0.03)
                    continue
                buf += bytes(win32file.ReadFile(self.h, n)[1])
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    m = json.loads(line.decode("utf-8"))
                    w = self._waiting.get(m.get("id")) if "event" not in m else None
                    if w:
                        w[1] = m
                        w[0].set()
                    else:
                        self.on_event(m)
        except (pywintypes.error, ValueError):
            pass
        self._lose()

    def request(self, call, args=None, timeout=900):
        rid = next(self._ids)
        w = [threading.Event(), None]
        self._waiting[rid] = w
        try:
            data = (json.dumps({"id": rid, "call": call, "args": args or {}}) + "\n").encode("utf-8")
            with self._wlock:
                win32file.WriteFile(self.h, data)
            if not w[0].wait(timeout):
                raise RuntimeError("timed out waiting for %s" % call)
        except pywintypes.error as e:
            raise RuntimeError("pipe error: %s" % e) from None
        finally:
            self._waiting.pop(rid, None)
        if "error" in w[1]:
            raise RuntimeError(w[1]["error"])
        return w[1]["result"]

    def close(self):
        self._closed = True
        try:
            win32file.CloseHandle(self.h)
        except pywintypes.error:
            pass
