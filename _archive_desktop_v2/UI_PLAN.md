# Fieldnote desktop app: architecture and rebuild plan

Status:
- **Phase 1 done.** `test_hub` OK, `validate` 71/71, and live: a VS Code Claude Code tool call showed up in the pipe client.
- **Phase 2 built.** `test_channel` OK. The live test with a channel-enabled Claude Code session is pending.

Revised 21 Nov 2026.

## User decisions

- **The GUI is the interface to Claude Code.** You type in Fieldnote, Claude Code does the AWR work with AWRMWO-mcp, and Fieldnote shows the conversation, each tool call and the live AWR state.
- **Your Claude Code account, no API key.** Fieldnote uses the Claude Code already installed with the VS Code extension and the login it already has.
- **Desktop only.** No HTTP server, no port, nothing a browser can reach. The window stays pywebview with the current look, loaded from disk.
- **Both connection modes:**
  1. **Linked:** the GUI talks to the Claude Code session you have open, the same conversation.
  2. **App session:** the GUI runs its own Claude Code session on your login, a separate conversation.

## 1. What the app does today (and why it is wrong)

```
pywebview ──HTTP :8765──> ui_server.py ──import server.py──> COM ──> AWR
Claude Code ──stdio──> AWRMWO-mcp ───────────────────────> COM ──> same AWR
```

| # | Problem | Where |
|---|---|---|
| 1 | Claude is not in the loop. The GUI calls tools itself through forms | `ui_server.py:93`, `app.js` dialogs |
| 2 | Two processes can drive one AWR at once | `ui_server.py:11` |
| 3 | The unauthenticated local HTTP API exposes `save_project` to any web page (cross-site `text/plain` POST) | `ui_server.py:76-98` |
| 4 | The hand-copied tool allow-list has drifted from `server.py` | `ui_server.py:14-36` |
| 5 | The schematic drawing is fake | `app.js:186-243` |
| 6 | Every simulation leaves a `Studio_<sch>_<time>` graph | `app.js:540-546` |
| 7 | `set_frequencies(document=...)` silently changes the schematic's sweep | `app.js:538` |
| 8 | `asyncio.run` per request; health polling calls AWR | `ui_server.py:69,93` |
| 9 | Fixed port 8765 | `ui_server.py:104` |

## 2. Target architecture

**AWRMWO-mcp is the hub.** It is the only process that talks to AWR. It also opens a Windows named pipe (`\\.\pipe\AWRMWO-<username>`, current user only) that Fieldnote connects to. A pipe is local inter-process communication, not networking: there is no port and no HTTP, and browsers cannot reach it.

```
                    ┌──────────────── Claude Code (your login) ────────────────┐
                    │  Mode 1: `claude` in VS Code's terminal, channel enabled │
                    │  Mode 2: claude.exe -p started by Fieldnote             │
                    └──────────────┬─────────────────────────▲───────────────┘
                          stdio MCP│tool calls    channel msgs│ / replies
                                   ▼                          │
                    ┌───────────── AWRMWO-mcp ─────────────────┴──┐
                    │ tools ──COM thread──> AWR                     │
                    │ activity log, approvals, channel relay        │
                    └──────────────┬────────────────────────────────┘
                     named pipe    │ (GUI messages, events, approvals)
                                   ▼
                    ┌──────────── Fieldnote (pywebview) ────────────┐
                    │ chat · activity timeline · live AWR panels    │
                    │ approve/deny dialogs · settings               │
                    └───────────────────────────────────────────────┘
```

### Mode 1: linked to your open session (Claude Code "channels")

- AWRMWO-mcp declares the channel capability (`experimental["claude/channel"]`) and a `reply` tool.
- When you type in Fieldnote, the message goes over the pipe to AWRMWO-mcp. It sends `notifications/claude/channel` into the running session, and Claude sees it as a message from Fieldnote. Claude does the work, then calls `reply`, and the text shows in Fieldnote's chat.
- Tool approvals are relayed with `experimental["claude/channel/permission"]`. Claude Code sends `permission_request` (tool, description, input preview), and Fieldnote shows Allow or Deny. The first answer wins, from either Fieldnote or the terminal.
- **Limits, from the docs:**
  - **Channels are a research preview.** A custom server needs Claude Code started as `claude --dangerously-load-development-channels server:AWRMWO-mcp`, which shows a one-time confirmation.
  - **It runs in the Claude Code terminal (CLI), in VS Code's integrated terminal.** The docs do not say the VS Code chat panel supports channels, so treat the panel as unsupported until tested.
  - **It needs claude.ai login or a Console key.** You have the login.
- Fieldnote gives you a "Start linked session" button. It opens VS Code's terminal, or a terminal in the workspace, with that command and the `claude.exe` that ships with the extension.

### Mode 2: app session (headless Claude Code)

- Fieldnote starts one long-lived process:
  `claude.exe -p --input-format stream-json --output-format stream-json --verbose --model <your choice> --permission-prompt-tool mcp__AWRMWO-mcp__approve`
  with `cwd` set to the workspace, so `.mcp.json` and `../CLAUDE.md` load.
- Your prompts go in on stdin. Claude's text and tool calls stream out on stdout into the chat and the timeline. The Stop button interrupts the turn.
- Approvals: Claude Code calls AWRMWO-mcp's `approve` tool, which asks Fieldnote over the pipe and returns Allow or Deny.
- **Verified 21 Nov:** the extension's `claude.exe` answered a `-p` prompt on your login, with no `ANTHROPIC_API_KEY` set.

### Shared by both modes

- **Activity timeline.** AWRMWO-mcp records every tool call (time, tool, short arguments, result or error) and pushes it to Fieldnote. It shows everything Claude does, from either mode.
- **Live panels.** Project tree, graphs, status messages and EM info. Fieldnote asks AWRMWO-mcp over the pipe, which runs the read tools on its COM thread. No `import server`, and no second COM owner.
- **Approvals.** `save_project`, `new_project` and `delete_*` always need Allow in Fieldnote. The server's `user_confirmed` guard stays as a second layer.
- **If no Claude Code session is running**, Fieldnote shows "Not connected" with the two start buttons. It never touches AWR by itself.

## 3. Settings

| Setting | Default |
|---|---|
| Claude Code binary | Found automatically in `%USERPROFILE%\.vscode\extensions\anthropic.claude-code-*\resources\native-binary\claude.exe` (newest), else `claude` on PATH |
| Account | Shows signed-in or signed-out. "Sign in" opens `claude` in a terminal so you run `/login` there. Fieldnote never handles your credentials |
| Mode | Linked or App session |
| Model (app session) | Your choice, never changed by the app |
| Workspace folder | `workspace` (where `.mcp.json` and `CLAUDE.md` live) |

Stored in `%APPDATA%\Fieldnote\settings.json`. No secrets are stored.

Note: this is for your own use on your own PC. Anthropic does not allow apps built for distribution to offer claude.ai login, so don't package Fieldnote for others with this setup.

## 4. What stays, what changes

| Part | Decision |
|---|---|
| `styles.css`, layout, theme, sidebar, toasts, modals | **Keep** |
| `app.js` `fetch('/api/...')` | **Replace** with `window.pywebview.api.*` (pywebview's built-in bridge) |
| Design view | **Rework** into chat, activity timeline and a live project panel |
| Schematic canvas | **Replace** with a parts-and-nets list from `list_elements`/`list_wires`. Use an AWR picture later, if COM can export one |
| Simulation view | **Rework** into a results viewer for existing graphs. New measurements are asked for in chat |
| Library view | **Keep the UI**, wired to `search_models`. "Use this part" sends a chat message |
| Settings view | **New**, as in section 3 |
| `ui_server.py` | **Delete** |
| `desktop_app.py` | **Rewrite**: the pipe client, the Mode 2 process manager, and the window |
| `server.py` | **Add**: the pipe server, the activity log, the channel capability with `reply`, permission relay, and the `approve` tool. Existing tools are unchanged |

## 5. Phases

### Phase 0: spikes (done)
- `mcp` 1.30.0: the low-level `Server.create_initialization_options(experimental_capabilities=...)` exists, so the channel capability can be declared. FastMCP needs a small hook to pass it, to be confirmed in Phase 1.
- The Claude Code binary is at the extension path above (v2.1.329), and the login is present. Headless `-p` works on it.
- Channels facts are in Mode 1 above. Open questions: whether the VS Code panel supports channels, and the exact JSON that `--permission-prompt-tool` returns. Both are tested in Phases 2 and 3.
- pywin32 is already a dependency and provides named pipes (`win32pipe`). No new packages are needed.

### Phase 1: hub in AWRMWO-mcp
- Correction, found while reading the code: every Claude Code session (VS Code panel, terminal, Mode 2) starts its own AWRMWO-mcp, so a global lock would break linked mode. Instead, each server opens its own pipe, `\\.\pipe\AWRMWO-<user>-<pid>`. Fieldnote lists the running sessions and lets you pick one. Use one Claude session per AWR task at a time, as today.
- `hub.py`: a pipe server thread with a current-user-only DACL and remote clients rejected. Messages are JSON lines.
- Activity log: a `FastMCP` subclass overrides `call_tool`, so every call is recorded and pushed to pipe clients.
- Pipe calls run only tools marked `readOnlyHint=True` in `server.py`. That marking is the single source of truth, so there is no copied list.
- **Done when:** a small test client lists the project and receives an activity event while Claude Code (VS Code) runs a tool, and the 71 schematic checks still pass.

### Phase 2: Mode 1, linked
- Channel capability, the `reply` tool, permission relay, and a "Start linked session" helper.
- **Done when:** a message typed into the test client reaches the terminal Claude Code session, Claude's reply comes back, and an Allow/Deny from the client decides a `save_project` approval.

### Phase 3: Fieldnote GUI
- Delete `ui_server.py`, load `ui/` from disk, and switch `app.js` to `js_api`.
- Chat, timeline, live panels, approval dialogs and settings. Remove problems 6 and 7.
- **Done when:** from Fieldnote, in linked mode, "plot the I-V curves of the NE3508M04 and bias it in the linear region" gives the same result as the terminal demo, and `netstat` shows no listening socket for Fieldnote.

### Phase 4: Mode 2, app session
- Process manager for `claude.exe -p` with stream-json, Stop, and the `approve` tool.
- **Done when:** the same I-V demo works with no terminal open.

### Phase 5: views and hardening
- Results viewer, library view, and the parts-and-nets schematic.
- Start-up checks: AWR not running, no Claude Code binary, signed out, no session, AWR modal dialog.
- Tests without AWR: pipe protocol, approval routing, settings. README update.

## 6. Risks

- **Channels are a research preview.** Flags or behaviour may change. Mode 2 is the fallback and does not depend on them.
- **VS Code panel.** Linked mode is documented for the CLI only. If the panel does not support channels, use `claude` in VS Code's integrated terminal.
- **Usage.** Both modes use your Claude Code plan's limits. Fieldnote shows each turn's usage from Claude Code's output.
- **One COM thread.** A long EM simulation blocks the live panels. The GUI shows "AWR busy".
- **AWR modal dialogs** block COM. The GUI shows the timeout and points you to AWR.
