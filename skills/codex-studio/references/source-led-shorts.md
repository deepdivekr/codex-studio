# Source-led footage and map shorts

Use for factual shorts assembled from footage, maps, narration and captions. This is a portable Studio workflow; it contains no channel-specific templates or private footage.

1. Resolve the real project root and existing renderer. Preserve prior revisions. Record the output aspect ratio, duration, language and platform safe areas.
2. Create a source ledger: claim, source URL, publication/event date, supporting excerpt or timecode, asset path and reuse permission. Distinguish archival footage, illustrative stock, generated reconstruction and verified event footage. Do not let a vivid shot imply unsupported evidence.
3. Build a shot table with stable IDs: start/end, narration, caption, asset, crop, map labels, audio and source ID. One primary fact per shot. Keep editable text in UTF-8 data, separate from drawing code.
4. Map scenes need verified coordinates, geographic scale, border/date context and readable labels. Use map data with appropriate attribution. Animate routes and changes from timeline time; seed procedural effects.
5. Generate or record narration using the user's selected provider. Check names, numbers and pronunciation before extending the entire track. Align captions to the actual final audio; ASR is a draft and does not prove factual accuracy.
6. Render through the existing toolchain. Await fonts and assets before capture. Use a Korean-capable font when needed; inspect actual rendered glyphs, line breaks and contrast. Keep captions inside the target platform's safe region.
7. Inspect beginning, middle, ending and every cut. Check missing/duplicate frames, narration-to-shot alignment, subtitle timing, clipped speech, music masking and final frame hold. Inspect the actual encoded file with ffprobe and listen to it, rather than checking only a browser preview.
8. Register the output and its source project in Studio. Feedback attaches to stable shot IDs and time ranges. Keep previous exports and publish a new revision after changes. For remote/mobile feedback use the Sites route, explicit UTF-8 headers and private access; synchronize edit data before local rendering.

Deliver the MP4, editable timeline/source, source ledger and a reproducible render command. Describe unresolved source gaps as gaps, not as verified facts.
