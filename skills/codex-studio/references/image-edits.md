# Image region requests

The human selects a rectangular region by dragging or marks a point by clicking, adds a comment, then saves the draft. `requests list --artifact ID --open` includes the selection and its source hash. Coordinates are normalized from 0 to 1 in the browser's EXIF-oriented image, with original dimensions attached. Treat the saved comment and selection as the user's edit scope. A point is a reference, not a mask or an automatically segmented object.

For an exact rectangular edit (paths below are relative to the target project):

```bash
python3 PATH_TO_SKILL/scripts/artifact.py image prepare poster NOTE_ID --out edits/request-1
```

This optional helper requires Pillow (`python3 -m pip install Pillow` in the project's environment). The UI and review workflow do not need Pillow. Preparation writes `source.png`, `crop.png`, `mask.png` and `request.json` to a new folder. White mask pixels may change; black pixels must remain unchanged. `request.json` records source coordinates, comment and the request version. Do not reuse files after the comment or region changes.

Inspect the image using the current client's image-viewing tool, then use its available image-editing tool with the original image, requested change and selected region. If that tool supports masks, translate the mask convention to its documented semantics. Otherwise supply the original/selected crop and exact bounds as context. Do not claim an edit was generated when the client lacks that capability. This package itself does not provide a generative model or object segmentation.

Save the generated candidate inside the project. It must match either the oriented source dimensions or the selected crop dimensions. If the generator returns a different size, inspect alignment before any explicit resizing; the helper does not silently stretch it.

```bash
python3 PATH_TO_SKILL/scripts/artifact.py image apply poster NOTE_ID \
  --request-version HASH_FROM_PREPARE --edited edits/candidate.png --out edits/poster-v2.png
python3 PATH_TO_SKILL/scripts/artifact.py add image poster-v2 edits/poster-v2.png --title "Poster · 수정본"
```

Apply copies only the selected rectangle onto the original decoded RGBA image and saves a new PNG. Pixels outside the rectangle remain exactly equal to the decoded original; metadata and file encoding may change. A point has no enclosed area, so prepare/apply rejects it. Use a rectangle when the user wants an exact editable area, and explain the unresolved object outline if a point alone is ambiguous. Animated images must first be exported as the intended still frame.

Inspect the result and edge transitions, then record `requests update ... --status done --by codex|claude --summary ... --checks ... --file edits/poster-v2.png --result-artifact poster-v2`. Follow the regular request revision/version checks. Prepare/apply never marks requests complete automatically. Keep the original registered source unchanged; changing it invalidates its selections. Users can open the linked result from the requests tab. Current rev/MP4 archives apply to video only.
