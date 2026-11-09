# Mobile and remote review with Sites

Read whenever the user asks to open the Studio editor. Default to the available Sites workflow so the same editor can open on desktop and mobile. A responsive page at `localhost` or `127.0.0.1` is still reachable only from its host. WSL loopback forwarding does not make it a mobile URL.

## Choose the destination

- Explicit local-only/offline or no-upload instruction: use `artifact.py open ID` without Sites publication.
- Otherwise discover Sites in the current session and read its skill. Continue to private hosting automatically; the user does not need to ask for Sites separately. Native tool approvals still apply. Keep an existing Site's identity and audience; never broaden access because the editor was reopened.
- If Sites is unavailable, say which capability is missing and open the local editor. Do not label it mobile access. If an available Sites operation fails, preserve its identity and records, report the failure and offer the usable local editor; never claim publication succeeded or create duplicate Sites to bypass the error.

## Carry the opening request into Sites

The installer puts this route in the target repository's AGENTS.md and CLAUDE.md. The active agent executes it in the same conversation; there is no second prompt to send or background model session to start.

Use the following internal task brief with the real selected project values. Do not ask the user to copy it:

> Open the selected Studio artifact as an editor. Resolve its source path, artifact ID, current revision, captions and saved review requests. Reuse its recorded Sites project when present; otherwise create an owner-private Site following the available Sites skill. Include only the selected review assets, durable authenticated cloud saving, revision-conflict handling, mobile layout and UTF-8 text. Preserve existing unsaved edits and completed revisions. Verify the deployed result and open its actual HTTPS URL. Keep media rendering in the existing local production environment.

Before creation, inspect the selected project's existing Site metadata and handoff records. Record the artifact-to-Site association under `.codex-artifacts/sites/<artifact-id>.json` using the registered safe artifact ID: `artifact_id`, `source_revision`, `project_id`, `checkout_path`, and verified `url` when available. Never store credentials there. Persist the project ID immediately after creation, before publication, so an interrupted attempt can resume. Read and verify the association with Sites tools on later opens; do not create a new Site on every request. An unchanged, successfully deployed matching revision can be reopened without republishing. Pending or changed work resumes through the Sites skill, preserving cloud edits.

Return the literal successful HTTPS URL and the same-account sign-in requirement. A saved metadata URL alone is not proof of a current successful deployment.

This reference is a hosting workflow, not an implemented `artifact.py deploy` command. Sites requires its own plugin/account. Installing Codex Studio alone does not install Sites or provision hosting.

## Prepare only the selected work

1. Read the selected registration, saved review and revision before exporting. Keep the originals and previous rendered versions. Copy only the selected video/image, captions, allowed dependencies and required review data into a separate Site checkout; never upload the complete media repository, handoffs, credentials or unrelated drafts.
2. Use a mobile-sized review proxy for large videos, preserving the original duration, frame timing and audio sync. Record its source artifact/revision and the proxy-to-source mapping. A proxy is not the final master.
3. Keep useful existing controls and terminology: frame seeking, timestamped comments, caption edits, completion state. Give every caption/cut/comment a stable unique ID; repeated labels such as `tele` are not IDs.
4. A static upload of the local Studio HTML cannot save to the Python backend. Implement real hosted endpoints and durable D1 records (or R2 for files) following the Sites skill. Device-local storage may cache a draft but must not be advertised as cross-device saving. Never silently fall back to it after a failed cloud save.
5. Scope records to the selected artifact and revision. Use expected-revision checks and return a conflict when another device saved first. Preserve unsaved text during polling; do not rebuild a focused input on every refresh. Retain text on failed saves and provide retry. Use appropriate authentication and origin checks for writes.

## Sync and render boundaries

A hosted edit is an edit request, not a changed MP4. Keep cloud records separate from the local `.codex-artifacts/` store until imported through the existing revision-aware review/request commands. Do not overwrite local drafts from an older cloud snapshot. A mobile save does not wake an idle Codex/Claude session. On the user's request to apply edits, read the hosted changes, reconcile the source revision, render locally with the established toolchain, verify the output, publish a new local revision, then update the Site's media and completion status through the Sites workflow. Cloudflare Workers are not a general FFmpeg/Blender/Python render host.

## Verify the handoff

For Korean or other non-ASCII text, write UTF-8 files, put `<meta charset="utf-8">` within the first 1024 bytes, set the document language, and serve the correct `Content-Type` with UTF-8. Check `document.characterSet` and representative labels in the hosted/static delivery path; a local development server can mask missing encoding metadata. Preserve the user's text rather than re-encoding mojibake. Avoid caching the editable HTML across a corrective deployment.

Check desktop and approximately 390 px mobile widths, video metadata/playback/seeking, keyboard/touch editing, save → reload persistence, two independently loaded clients, and failed-save/conflict behavior. Ensure comments stay inside the viewport and long labels do not force horizontal scrolling. State exactly which checks passed; an emulated mobile viewport is not a physical phone test. The Sites deployment result verifies publication; do not claim hosted save behavior solely from a successful deployment.

Keep the site private unless the user explicitly requests another audience. Report the final clickable HTTPS address and any sign-in requirement. Preserve existing tabs and stop only preview processes started for this deployment.

## Media and editing acceptance checks

A locally passing editor is not evidence that its hosted media can seek. On the deployed origin, inspect a nonzero byte-range request for the media and test a jump to an unbuffered middle/end frame. If the host ignores Range, use a bounded review proxy loaded into a Blob URL (show loading progress and retain queued seeks), or implement a range-capable media route. Keep playback time, displayed frame and timeline position consistent. Do not imply the file is ready while download is incomplete.

For any added move/resize control, use the real source layer and a clean background. Dragging only a border is not a visual edit preview. Verify the content follows during the drag, the old location is cleared, numeric input agrees, and save/reload/playback preserves the transform. If no layer data exists, omit that capability or state the actual limitation before presenting the editor.

Use an isolated QA artifact/record and clean up only that test data. Exercise create/edit/save/reload/complete/reopen/delete, focused-text preservation during polling, two-client conflicts, and failed-save retry. Include image/HTML/version/audio paths when offered. Preserve unsent comment text on navigation and use distinct labels for sliders and buttons. Report failures and untested environments; viewport emulation does not verify physical touch or another AI client's automatic skill selection.
