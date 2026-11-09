# Mobile and remote review with Sites

Read when the user wants to open Studio on a phone or another computer, or explicitly asks for Sites hosting. A responsive page at `localhost` or `127.0.0.1` is still reachable only from its host. WSL loopback forwarding does not make it a mobile URL.

## Choose the destination

- Same computer: keep the existing `artifact.py open ID` workflow.
- Another device through Sites: use the available Sites skill and tools to build and deploy an owner-private review site. Keep an existing Site's identity and audience. Open the literal successful HTTPS deployment URL; explain that the owner signs in with the same ChatGPT account.
- If Sites is unavailable, say which capability is missing. Do not present a local URL as remote access, expose the local server on all interfaces, or create a tunnel as an unrequested substitute.

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
