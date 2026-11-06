# ShipRoom

**Release decisions backed by executable evidence, coordinated in one Switch room.**

Small engineering teams often scatter release reviews, failed checks, fixes and
approvals across terminals and private conversations. ShipRoom gives one Codex
agent a reproducible local verification toolkit while humans coordinate in a
shared Switch room. Mattermost is the initial interface. There is no dashboard,
chatbot backend, database, deployment service, or second agent.

## Architecture

```text
Human developers in Mattermost
             ↕
Switch room: shared context, identity and human decisions
             ↕  Switch Console runtime / MCP tools
Exactly one OpenAI Codex CLI agent (SHIPROOM.md)
             ↓  local subprocess CLI
Git inspection → pytest / Ruff / whitespace / compile / optional pip-audit
             ↓
Evidence-based readiness → JSON release state → approved Markdown/JSON package
```

Switch is essential: the one agent receives requests, publishes findings, assigns
human action items conversationally, and obtains both approvals in the same room.
The Python CLI is its deterministic tool, not a second AI or another chat system.
Switch Console supplies the transport; ShipRoom does not reimplement or simulate it.

`git_inspector.py` captures checked-out candidate/base commits, branch, changed
files, diff and working-tree status. `checks.py` captures real command exit codes,
stdout, stderr, UTC timestamps and elapsed time with argument arrays and timeouts.
`risk_engine.py` explains BLOCKED, READY_WITH_WARNINGS or READY_FOR_APPROVAL.
`release_manager.py` enforces transitions and approval gates, retains verification
history, and detects stale evidence. `report_generator.py` emits the six-file
package. `cli.py` exposes review/show/verify/propose/decide/apply/package.

## Installation

Python 3.11+ and Git must be installed. Run from this checkout:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Optional audit tool; network access is required for vulnerability data:
.\.venv\Scripts\python.exe -m pip install pip-audit
```

On Linux/macOS replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.
No OpenAI API SDK or extra model API is used. Install and authenticate Codex CLI
as described in the [official OpenAI documentation](https://learn.chatgpt.com/docs/codex/cli).

## Configure the single agent in Switch

1. Start Switch Console and a Switch server; connect Mattermost. Bundled
   Mattermost requires Docker. See [Switch deployment](https://docs.switchagents.ai/switch-rooms/deploy/index)
   and [Mattermost setup](https://docs.switchagents.ai/switch-rooms/deploy/messaging-apps/mattermost).
2. Confirm Codex is signed in and its CLI installed under agent providers.
3. In **Your Agents**, add exactly one agent named `shiproom`, provider **Codex**,
   run location **This computer**, directory this checkout's absolute path.
   Set its instructions to: `Read SHIPROOM.md and follow it for all release work.
   Use the project .venv Python. Never create or delegate to other agents.`
4. Keep **Bypass permissions** off. Configure **Who can talk to your agent** for
   the human release team; link each human's Mattermost identity. Do not grant
   other agents approval authority. See [onboarding](https://docs.switchagents.ai/switch-rooms/getting-started/onboard-your-agents).
5. Add the `shiproom` bot account to a Mattermost team channel. This creates its
   Switch room. Keep only this one AI agent in the room. Address it with
   `@shiproom`. Mattermost Switch commands use `!`, including `!agents-status`.
6. Console starts/manages the Codex session and supplies Switch operations as
   MCP tools. A manually started `codex` session alone is not room connectivity.
   If using a terminal session, `!run-cmd @shiproom` shows the deployment-specific
   start command; execute the real returned command, not an invented one.
   See [room commands](https://docs.switchagents.ai/switch-rooms/resources/room-commands#run-cmd)
   and [connection architecture](https://docs.switchagents.ai/switch-rooms/internals/index#how-agents-connect).
7. Ask the agent to read the room and identify the actual room ID. Confirm its
   reply appears in Mattermost before starting the live demo.

No live Switch server was configured during development. Do not claim that a
message or approval reached Switch until you observe it there.

## Reproducible live demo

Create a new isolated regression repository (this explicitly authorizes its two
local demonstration commits):

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_demo --target .demo/run-1
```

For reset, use a fresh name such as `.demo/run-2`. The script refuses an existing
directory and never deletes data or resets Git. Every fresh run has identical
source and regression; commit timestamps/IDs may differ. `demo-base` is always
the correct baseline. The candidate adds rather than subtracts a 10% discount:
`total_cents(10000, 1000)` yields 11000 instead of 9000.

In the real Mattermost room send:

```text
@shiproom Review .demo/run-1, base demo-base, candidate HEAD, version 1.0.0.
```

The agent runs this command using the real room ID:

```powershell
.\.venv\Scripts\python.exe -m shiproom.cli review --repo .demo/run-1 --base demo-base --ref HEAD --version 1.0.0 --room ACTUAL_ROOM_ID
```

Copy the returned release ID as `RELEASE_ID` in the following commands. The
agent publishes the failing test and other evidence. A human then sends:

```text
@shiproom Prepare a minimal proposed fix for RELEASE_ID. Do not apply it.
```

The agent writes the one-line subtraction patch under `artifacts/fix.patch`,
without modifying the target, and runs:

```powershell
.\.venv\Scripts\python.exe -m shiproom.cli propose RELEASE_ID --patch artifacts/fix.patch --reason "Restore discount subtraction"
```

After reviewing the exact diff, a human sends `APPROVE_PATCH RELEASE_ID` addressed
to the agent. The agent records actual metadata in `artifacts/patch-approval.json`
using the schema in SHIPROOM.md, then runs:

```powershell
.\.venv\Scripts\python.exe -m shiproom.cli decide RELEASE_ID --evidence artifacts/patch-approval.json
.\.venv\Scripts\python.exe -m shiproom.cli apply RELEASE_ID
.\.venv\Scripts\python.exe -m shiproom.cli verify RELEASE_ID
```

The agent shows the resulting diff and real rerun results. Audit is NOT RUN for
this dependency-free demo (no requirements.txt), so readiness has a warning.
After a human sends `APPROVE_RELEASE RELEASE_ID` in Switch, the agent records
real metadata in `artifacts/release-approval.json`, then runs:

```powershell
.\.venv\Scripts\python.exe -m shiproom.cli decide RELEASE_ID --evidence artifacts/release-approval.json
.\.venv\Scripts\python.exe -m shiproom.cli package RELEASE_ID
.\.venv\Scripts\python.exe -m shiproom.cli show RELEASE_ID
```

The agent publishes the summary and package location back to the same room.
`artifacts/releases/RELEASE_ID/` contains `release_notes.md`,
`verification_report.json`, `verification_report.md`, `approval_record.json`,
`rollback_plan.md` and `changed_files.txt`. No deployment occurs.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m compileall -q shiproom scripts demo_service tests
```

The integration suite executes actual Git, pytest, Ruff, compilation and patch
commands in temporary repositories. It detects a genuine regression, rejects
release approval, records **test fixture** human decisions, applies the patch,
reruns all mandatory checks and validates all six package files. Fixture decisions
are not Switch activity. Final validation: **29 tests passed**, Ruff passed, and
Python compilation passed (Python 3.12, Windows). Actual pytest output is recorded in `artifacts/test-results.txt`
after the final validation run; optional dependency auditing is not claimed passed.

## Security and limitations

- Normal review never edits application source. Proposal is separate from apply;
  explicit patch approval and separate final release approval are required.
- Approvals require exact release ID, room, message ID, author ID, human actor
  type and exact decision text. The connected agent must verify these against
  the real room. Offline JSON is an attestation, not cryptographic authentication;
  an operator with filesystem access can tamper with state. No fake connector exists.
- Candidate must be checked out. Untracked files are rejected. Patches remain
  uncommitted unless a human separately authorizes committing. A changed candidate
  invalidates approval freshness. Git metadata and working tree are both recorded.
  Compilation covers existing Git-tracked Python files; ignored local files are excluded.
- Only simple text patch paths are supported. Secret paths, escaping paths,
  symlinks/submodules in patches and binary patches are refused. Secret detection
  is path-based, not a content scanner. Keep all secrets outside reviewed repos.
- Repository test code executes with the operator's permissions. Use trusted,
  isolated demo repositories without credentials. No OS sandbox is implemented.
- Single local writer; no multi-process state locking or distributed storage.
  JSON writes are atomically replaced. Interrupted verification may be rerun.
- pip-audit is optional and audits a requirements.txt when present; absent tool,
  missing manifest, network failure or vulnerabilities remain warnings. Other
  dependency manifests and transitive/environment audits are outside this MVP.
- No automatic deployments, commits, pushes, destructive resets or extra services.
  Switch itself has its own infrastructure; ShipRoom adds no database.

## Screenshot placeholders

- TODO: Mattermost shared room with the failed payment assertion.
- TODO: Human patch approval alongside the exact proposed diff.
- TODO: Successful mandatory verification and separate release approval.
- TODO: Generated package directory and verification report.
