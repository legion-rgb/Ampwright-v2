"""Hidden Claude Code session (claude -p, stream-json) on the user's own subscription login. Stdlib only."""
import collections
import glob
import json
import os
import re
import shutil
import subprocess
import threading

SERVER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")
PROMPT = ("You are the Ampwright app's assistant for AWR Microwave Office. Do AWR work with the AWRMWO-mcp tools. "
          "Answer briefly in plain text and say what changed in AWR. Never save without the user's yes. "
          "Adding parts and wiring in AWR needs no permission. If the task gives no frequency or range, ask the user for the "
          "frequency points before simulating; one frequency f means a sweep of f/4 to 2.5 f in steps of f/8, in f's own unit. "
          "Set the sweep and equations on the schematic you are working on (set_frequencies / add_equation with document=<schematic>), "
          "never project-wide, unless the user asks for the whole project. "
          "If the user asks for the design loop, a spec or its approval, don't build it yourself: tell them to switch Ampwright to Design mode.")
DESIGN_PROMPT = ("You are the Design Lead for the Ampwright app. Follow CLAUDE.md and AGENTIC_PLAN.md in this folder: "
                 "write the spec, then show it to the user as a normal reply and stop until they approve or change it. "
                 "Never save or start a new project without the user's yes.")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def find_claude():
    """Newest claude.exe from the VS Code extension (its folder version changes on every update), else PATH."""
    hits = sorted(glob.glob(os.path.expanduser(
        r"~\.vscode\extensions\anthropic.claude-code-*\resources\native-binary\claude.exe")),
        key=lambda p: [int(n) for n in re.search(r"claude-code-([\d.]+\d)", p).group(1).split(".")])
    return hits[-1] if hits else (shutil.which("claude") or "")


def lean_args(pipe, mode="quick"):
    """Only the AWR server (told which pipe to open), no user plugins/settings/skills, few built-in tools.
    Design mode adds Write/Edit (dossier and PROGRESS.md; hub.approve allows them only inside the v2 folder), Agent (the v2 loop)
    and Bash (subagents inherit this list; hub.approve lets only the checks/ scripts run unasked); the caller runs it with cwd = the v2 folder."""
    design = mode == "design"
    server = {"command": "uv", "args": ["run", "--script", SERVER], "env": {"AMPWRIGHT_PIPE": pipe}}
    return ["--strict-mcp-config", "--mcp-config", json.dumps({"mcpServers": {"AWRMWO-mcp": server}}),
            "--setting-sources", "project,local", "--disable-slash-commands",
            "--tools", "Read,Glob,Grep,Write,Edit,Agent,Bash" if design else "Read,Glob,Grep",
            "--disallowedTools", "mcp__AWRMWO-mcp__reply",  # the app shows Claude's own answer; reply is for channel mode
            "--append-system-prompt", DESIGN_PROMPT if design else PROMPT,
            "--permission-prompt-tool", "mcp__AWRMWO-mcp__approve"]


class Session:
    def __init__(self, claude_path, workspace, pipe, on_event, model=None, extra_args=None, mode="quick"):
        self.claude_path, self.workspace, self.pipe, self.on_event, self.model = claude_path, workspace, pipe, on_event, model
        self.mode = mode
        self.extra_args = extra_args or []  # tests put a fake script here
        self.session_id = None
        self.stderr_tail = collections.deque(maxlen=50)
        self._proc = None
        self._lock = threading.Lock()

    def running(self):
        return self._proc is not None and self._proc.poll() is None

    def start(self):
        with self._lock:
            if self.running():
                return
            cmd = [self.claude_path, *self.extra_args, "-p", "--input-format", "stream-json",
                   "--output-format", "stream-json", "--verbose", *lean_args(self.pipe, self.mode)]
            if self.model:
                cmd += ["--model", self.model]
            if self.session_id:
                cmd += ["--resume", self.session_id]
            env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}  # subscription login, never the API
            p = subprocess.Popen(cmd, cwd=self.workspace or None, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                                 creationflags=NO_WINDOW)
            self._proc = p
            threading.Thread(target=self._read_out, args=(p,), daemon=True).start()
            threading.Thread(target=self._read_err, args=(p,), daemon=True).start()

    def _read_err(self, p):
        for line in p.stderr:
            self.stderr_tail.append(line.rstrip())

    def _read_out(self, p):
        for line in p.stdout:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            self._handle(m)
        code = p.wait()
        if self._proc is p:  # once, and not for a process already replaced
            self._proc = None
            self.on_event({"event": "session_exited", "code": code})

    def _handle(self, m):
        if m.get("session_id"):
            self.session_id = m["session_id"]
        t = m.get("type")
        parent = m.get("parent_tool_use_id")  # set on steps a subagent took; the id of the Agent call that started it
        if t == "assistant":
            for b in (m.get("message") or {}).get("content") or []:
                if b.get("type") == "text" and b.get("text"):
                    self.on_event({"event": "reply", "text": b["text"], "parent": parent})
                elif b.get("type") == "tool_use":
                    self.on_event({"event": "tool_use", "id": b.get("id"), "tool": b.get("name"), "input": b.get("input") or {},
                                   "parent": parent})
        elif t == "user":  # Claude Code echoes each tool's result back as a user message
            for b in (m.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    c = b.get("content")
                    text = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c or [] if isinstance(x, dict))
                    self.on_event({"event": "tool_result", "id": b.get("tool_use_id"), "is_error": bool(b.get("is_error")),
                                   "text": text[:400], "parent": parent})
        elif t == "result":
            self.on_event({"event": "turn_end", "is_error": bool(m.get("is_error")), "usage": m.get("usage")})

    def send(self, text):
        self.start()
        line = json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": text}]}})
        self._proc.stdin.write(line + "\n")
        self._proc.stdin.flush()

    def stop(self):
        with self._lock:
            p, self._proc = self._proc, None
        if p and p.poll() is None:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, creationflags=NO_WINDOW)
            try:
                p.wait(5)
            except subprocess.TimeoutExpired:
                p.kill()
