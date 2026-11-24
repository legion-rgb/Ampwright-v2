"""Manual tool: connect to a running AWRMWO-mcp hub pipe and print its events.
Usage: python tests/pipe_client.py [--pid N] [--seconds 30] [--chat "text"] [--answer allow|deny]
  --chat    sends the text into the linked Claude Code session (channel)
  --answer  replies to every permission_request with allow or deny (default: just print it)"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pywintypes
import win32file
import win32pipe

ap = argparse.ArgumentParser()
ap.add_argument("--pid", type=int)
ap.add_argument("--seconds", type=int, default=30)
ap.add_argument("--chat")
ap.add_argument("--answer", choices=["allow", "deny"])
a = ap.parse_args()

pipes = [p for p in os.listdir("\\\\.\\pipe\\\\") if p.startswith("AWRMWO-")]
if a.pid:
    pipes = [p for p in pipes if p.endswith("-%d" % a.pid)]
if not pipes:
    raise SystemExit("no AWRMWO pipe found")
name = "\\\\.\\pipe\\" + max(pipes, key=lambda p: int(p.rsplit("-", 1)[1]))  # highest pid is a guess; use --pid
print("pipe", name, flush=True)
h = win32file.CreateFile(name, win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None,
                         win32file.OPEN_EXISTING, 0, None)


def send(i, call, **args):
    win32file.WriteFile(h, (json.dumps({"id": i, "call": call, "args": args}) + "\n").encode())


send(1, "project_info")
if a.chat:
    send(2, "chat", text=a.chat)
buf, end, n = b"", time.time() + a.seconds, 10
while time.time() < end:
    try:
        avail = win32pipe.PeekNamedPipe(h, 0)[1]  # poll: a blocking read would block our writes
    except pywintypes.error:
        print("server closed the pipe", flush=True)
        break
    if not avail:
        time.sleep(0.05)
        continue
    buf += bytes(win32file.ReadFile(h, avail)[1])
    while b"\n" in buf:
        line, buf = buf.split(b"\n", 1)
        m = json.loads(line)
        print(json.dumps(m)[:600], flush=True)
        if m.get("event") == "permission_request" and a.answer:
            n += 1
            send(n, "permission", request_id=m["request_id"], behavior=a.answer)
