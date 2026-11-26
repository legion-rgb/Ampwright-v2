# Fieldnote 2: plan

Status (22 Nov 2026):
- **Phase 1 done.** `tests/test_fieldnote_ui.py` passes. Live, the app started Claude Code hidden, attached to its fixed pipe and showed the open AWR project in 4.4 s. No prompt was sent, so no usage was spent, and no process was left behind on close. Run it with `Fieldnote.bat`.
- **Phase 2 done (24 Nov, in v1):** chat, step timeline, Stop, saved history, the approval dialog (only save, new project and delete ask), and frequency sweeps in the sweep's own unit. Tests: `test_fieldnote_chat`, `test_fieldnote_chat_ui`, `test_fieldnote_approval`, `test_session`.
- **Moved into v2 on 25 Nov.** All 18 AWR-free tests pass here. Phases 3 and 4 are not started. The first app is archived in v1's `_archive_fieldnote_v1/`, and v2's older window in `_archive_desktop_v2/`.

## What it is

A desktop app that is the front-end for Claude Code in AWR work. You type a design task in the app. Claude Code, running hidden on your subscription, designs the circuit in AWR through AWRMWO-mcp. The app shows the AWR project, Claude's replies and every step. It is the base for version 3, where basic RF circuits become templates.

## Rules (user decisions)

- **Subscription, never the API.** The app starts the installed Claude Code (`claude -p`, headless) on your login. No API key is set or stored. These turns count against your subscription's usage limits.
- **Claude Code stays hidden.** The app is the only interface you see.
- **Desktop only.** One window, no web server, no port.
- **Approvals:** Claude builds in AWR without asking. Only `save_project`, `new_project` and `delete_*` need your Allow.
- **Look:** RF-style icons and animations. A dark "lab instrument" theme (VNA-screen style, glowing traces) and a light, clean theme, with a small icon to switch between them. Dark is the default.
- Personal use on your PC only: an app shared with others can't use a claude.ai login.

## How it works

```
Fieldnote window ──prompt──▶ app backend ──stdin──▶ claude -p (hidden, your login)
      ▲                          │  ▲                     │ starts
      │ events                   │  └──stdout: replies, tool calls
      │                          │                        ▼
      └── project details ◀── pipe (fixed name) ◀── AWRMWO-mcp ──COM──▶ AWR
          approvals                                   (the only AWR owner)
```

- When the app opens, it starts one hidden Claude Code session with a lean setup: only the AWR server, no user plugins or skills, and a short AWR instruction. It measured 19k tokens per turn, against 61k with the full setup.
- The app gives that session's MCP server a **fixed pipe name**, so it always talks to its own server. That removes v1's session list and guessing, which caused most of its failures.
- **Project details** come straight from the server over the pipe, through read-only tools only, so reading them uses no Claude tokens.
- **Approvals:** Claude Code asks the server's `approve` tool, and the server asks the window. This was tested live in v1.
- **Errors are visible:** a status bar shows AWR, Claude and the turn state, and any failure shows as a banner with the message.

### Reused from v1 (proven parts)

- the headless session manager with lean flags;
- the pipe client;
- the hub and the `approve` tool in `server.py`;
- the safe markdown renderer;
- the hidden-window UI test.

The window, the styles and the layout are new.

## Phases

### Phase 1: shell and AWR connection (the "initial phase")
- **Window:** RF-themed layout, the dark and light themes, the theme icon, and the status bar.
- **Startup:** the hidden Claude session starts in the background. The app attaches to its pipe and shows the project card:
  - name, file, and saved or unsaved;
  - schematics, graphs, EM structures and netlists.
- **Animation:** a signal pulse runs along a transmission-line icon while it connects. The link lights up when AWR answers.
- **Done when:**
  - with AWR open, the project name shows within about 5 s;
  - with AWR closed, a clear message shows instead;
  - the theme switch works and is remembered;
  - the hidden-window test passes.

### Phase 2: chat that designs in AWR
- **Chat:** the chat box sends to Claude Code, and replies stream back with formatting.
- **Activity feed:** each tool call is a row with an RF icon for its kind (schematic, part, wire, graph, simulate, EM).
- **While Claude works:** a sweeping-trace animation runs, with a Stop button.
- **After AWR changes:** the project card refreshes.
- **Approvals:** a dialog for save, new project and delete.
- **Done when:**
  - "build an RC low-pass with a 1 GHz cutoff and plot S21" builds it in AWR, and the card shows the new schematic and graph;
  - asking Claude to delete a graph shows the dialog, and Deny is respected.

### Phase 3: viewers and polish
- **Viewers:** the graph image and trace summary; parts and wires for the selected schematic.
- **Settings:** usage per turn, a model picker, and resuming the last conversation.
- **Start-up checks:** AWR not running, Claude Code not found, signed out, or another session driving AWR.
- **Shipping:** a launcher and a README.
- **Done when:** the NE3508M04 bias demo works end to end from the window.

### Phase 4: version 3 foundation
- **Templates gallery:** cards for basic RF circuits (RC low-pass, L-match, transistor bias, Chebyshev low-pass, Wilkinson divider). A card opens a short spec form and sends the task to Claude.
- **Later:** v2's agent loop behind the templates (spec, theory, build, check, fix), after your v3 plan.

## Files

```
AWRMWO-mcp/fieldnote/
  app.py        window + backend (js_api), settings
  session.py    hidden claude -p session (from v1)
  pipe.py       pipe client (from v1)
  ui/index.html, ui/app.css, ui/app.js, ui/icons.svg   (inlined into the window)
AWRMWO-mcp/hub.py            + fixed pipe name from an environment variable
AWRMWO-mcp/tests/test_fieldnote_ui.py
```
