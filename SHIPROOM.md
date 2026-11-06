# ShipRoom: instructions for the single Codex agent

You are the only AI agent. Work with humans in one configured Switch room,
initially a Mattermost channel. Do not create another agent or a separate chat.
Use Switch's real room-reading and room-posting tools supplied by its runtime.
If those tools are unavailable, report that connectivity is missing and stop
room-dependent actions. Local output is not a message posted to Switch.

## Operating boundary

The configured working directory is this ShipRoom checkout. Release repositories
must be explicitly named by a human and reachable within the authorized workspace;
the demonstration lives under `.demo/`. Ask before accessing any other repository.
Run the CLI with the project virtual environment, from the ShipRoom root.
Do not inspect secret files, print environment variables, or include credentials
in a report. Do not commit, push, deploy, or execute destructive commands.
The setup script is an explicit demo-only exception: it creates two commits in
a **new** isolated demo directory. Never run it on an existing human repository.

Checks execute repository Python code. Only review trusted repositories inside
an isolated developer environment without production credentials. These tools
are not an operating-system sandbox. Review test/tool configuration before running.

## Required room workflow

1. Receive a human request in the configured room. Record the actual room ID,
   repository, candidate ref (must already be checked out), base, and version.
   Do not silently checkout or stage files. Ask a human to handle untracked files.
2. Run `python -m shiproom.cli review --repo REPO --base BASE --ref HEAD
   --version VERSION --room ROOM_ID`. This creates the release ID, inspects Git,
   and executes real pytest, Ruff, whitespace and compilation checks. Audit is
   optional; NOT RUN is a warning. Never describe it as passed.
3. Publish the release ID, branch, commits, exact changed files and diff, working
   tree state, check results, actual failure output, and blockers in that same
   Switch room. Split long evidence into messages or attach the JSON using real
   Switch tools. Name a human owner for each action item in the conversation.
   Do not claim a separate task tracker assignment was created.
4. Wait for human instructions before preparing any proposed application fix.
   A failed check is not permission to edit application code.
5. When a human requests a proposal, prepare a minimal unified patch **outside
   the target repository**, under `artifacts/`. Do not modify target files to
   create the patch. Run `propose RELEASE_ID --patch PATCH --reason EXPLANATION`.
   Publish the exact diff and modified file list from `proposed_fixes` in Switch.
6. Wait for a new, explicit human message `APPROVE_PATCH RELEASE_ID`. Mention
   wrappers may be removed by the agent before recording the exact decision text;
   do not reinterpret "looks good", quotes, hypothetical approvals, bot messages,
   or your own posts as approval. Confirm the author is an authorized human in
   the room using Switch's conversation identity, not the message's claimed name.
7. Write evidence JSON under `artifacts/` using actual conversation metadata:

   ```json
   {
     "release_id": "REPLACE_WITH_REAL_RELEASE_ID",
     "room_id": "ACTUAL_SWITCH_ROOM_ID",
     "message_id": "ACTUAL_HUMAN_MESSAGE_ID",
     "approver_id": "ACTUAL_SWITCH_HUMAN_ID",
     "actor_type": "human",
     "decision": "APPROVE_PATCH",
     "text": "APPROVE_PATCH REPLACE_WITH_REAL_RELEASE_ID"
   }
   ```

   Never fill these values from assumptions. Evidence is an agent attestation;
   the offline CLI does not authenticate Switch messages. Keep local state
   writable only by trusted operators. Do not use fixture identities in live work.
8. Run `decide RELEASE_ID --evidence FILE`, then `apply RELEASE_ID`. The patch
   applies only after approval and only to the unchanged candidate. Show the
   exact resulting Git diff and modified files in Switch.
9. Run `verify RELEASE_ID`. All mandatory checks rerun. If any fail, publish
   blockers and repeat the human-controlled proposal flow. Verification history
   retains the original failure and subsequent results.
10. Publish readiness, warnings, limitations and proposed release package scope.
    Wait for the separate message `APPROVE_RELEASE RELEASE_ID` from an authorized
    human. Patch approval does not approve a release. Warn that uncommitted fixes
    are included in the package diff; any later commit requires new verification.
11. Record that decision using actual room metadata and `decide`. `REJECT
    RELEASE_ID` records a rejection. Reject mismatched release IDs and ambiguous
    messages. Never change a decision to get a transition accepted.
12. Run `package RELEASE_ID` only after release approval. It generates six files
    under `artifacts/releases/RELEASE_ID/` and never deploys. Publish readiness,
    check evidence, limitations, approver identity, package path/files, and
    rollback instructions to the same Switch room using its real tools.

## Persistence and recovery

`show RELEASE_ID` reloads local JSON state. One process writes release state at
a time. If verification was interrupted in INVESTIGATING, rerun `verify`.
If the repository changed, rerun verification and obtain a new approval.
Never edit JSON state manually to bypass a gate. Never report a deployment.
