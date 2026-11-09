"""Optional image-region interchange; generation belongs to the active client."""
from __future__ import annotations

import math
from pathlib import Path
import tempfile

from media import destination
from model import Conflict, image_selection, relative, write_json


def pillow():
    try:
        from PIL import Image, ImageOps
    except ImportError as error:
        raise ValueError('Image prepare/apply requires Pillow: python -m pip install Pillow') from error
    return Image, ImageOps


def load_image(path):
    Image, ImageOps = pillow()
    with Image.open(path) as image:
        if getattr(image, 'n_frames', 1) != 1:
            raise ValueError('Region edits require a still image; export the intended frame first')
        return ImageOps.exif_transpose(image).convert('RGBA')


def selected_request(project, key, ident):
    item = project.request_item(key, ident)
    art = project.artifact(key)
    selection = image_selection(item.get('selection'), art)
    if selection['kind'] != 'rect':
        raise ValueError('A point is a reference, not an edit mask. Select a rectangle first.')
    source = load_image(project.asset(art, 'file'))
    width, height = source.size
    if (selection['image_width'], selection['image_height']) != source.size:
        raise Conflict('The selected image dimensions do not match the decoded source')
    bounds = (math.floor(selection['x'] * width), math.floor(selection['y'] * height),
              min(width, math.ceil((selection['x'] + selection['width']) * width)),
              min(height, math.ceil((selection['y'] + selection['height']) * height)))
    return item, source, bounds


def prepare_image(project, key, ident, out):
    Image, _ = pillow()
    with project.lock():
        item, source, box = selected_request(project, key, ident)
        target = destination(project, out)
        if target.suffix:
            raise ValueError('--out must be a new directory for source, crop, mask and request files')
        with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
            folder = Path(temporary)
            source.save(folder / 'source.png')
            source.crop(box).save(folder / 'crop.png')
            mask = Image.new('L', source.size, 0)
            mask.paste(255, box)
            mask.save(folder / 'mask.png')
            manifest = {**item, 'pixel_bounds': list(box),
                        'mask_convention': 'white=editable; black=preserve',
                        'coordinate_system': 'EXIF-oriented source pixels; right/bottom exclusive'}
            write_json(folder / 'request.json', manifest)
            if target.exists() or target.is_symlink():
                raise Conflict('Output directory already exists')
            folder.rename(target)
    return {'directory': relative(out), 'request_version': item['request_version'], 'pixel_bounds': list(box)}


def apply_image(project, key, ident, edited, out, request_version):
    with project.lock():
        item, source, box = selected_request(project, key, ident)
        if item['request_version'] != request_version:
            raise Conflict('The request changed after image preparation. Prepare the current selection again.')
        candidate = load_image(project.local(edited))
        if candidate.size == source.size:
            patch = candidate.crop(box)
        elif candidate.size == (box[2] - box[0], box[3] - box[1]):
            patch = candidate
        else:
            raise ValueError('Edited image must match the full source or selected crop dimensions; no automatic resizing')
        output = destination(project, out)
        if output.suffix.lower() != '.png':
            raise ValueError('Save the result as PNG to preserve pixels outside the selection')
        result = source.copy()
        result.paste(patch, box[:2])
        with output.open('xb') as handle:
            result.save(handle, format='PNG')
    return {'file': relative(out), 'request_version': request_version,
            'pixel_bounds': list(box), 'outside_selection': 'original decoded RGBA pixels preserved'}
