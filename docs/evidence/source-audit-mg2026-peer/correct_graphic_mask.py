"""Versioned correction of a blind pixel mask; original blind file is immutable.

The SEI badge's right border extended six pixels past the initial graphic mask.
It was merged into the first three electronic-signature text lines. Removing the
badge border changes no text, line count, source image or source candidate.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
blind_path = HERE / 'blind-visual-line-inventory.json'
assert hashlib.sha256(blind_path.read_bytes()).hexdigest() == '335a27d65c75eddfbc74bd30c0ee2642058c1a4805e5227bb1a7433083b5b2a1'
blind = json.loads(blind_path.read_text())
image_path = ROOT / 'var/private-evidence/source-audit-southeast-completeness/mg-matrizes2026-ocr13/page-13-original-raster.png'
image = Image.open(image_path).convert('L')
mask = image.point(lambda v: 255 if v < 160 else 0)
draw = ImageDraw.Draw(mask)
draw.rectangle((0, 570, 260, 719), fill=0)
draw.rectangle((0, 720, 254, 909), fill=0)
changes = []
for band in blind[12]['visual_text_line_bands']:
    old = band['pixel_bbox']
    ink = mask.crop((0, old[1], image.width, old[3])).getbbox()
    new = [ink[0], old[1] + ink[1], ink[2], old[1] + ink[3]]
    if old != new:
        changes.append({'page': 13, 'blind_visual_line': band['visual_line'],
                        'old_pixel_bbox': old, 'corrected_pixel_bbox': new,
                        'reason': 'Graphic badge border, not source textual ink, removed from blind text-line mask'})
assert len(changes) == 3
report = {'status': 'corrected_inventory_geometry_only',
          'original_blind_path': str(blind_path.relative_to(ROOT)),
          'original_blind_sha256': hashlib.sha256(blind_path.read_bytes()).hexdigest(),
          'primary_image_path': str(image_path.relative_to(ROOT)),
          'primary_image_sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(),
          'old_badge_mask': [0, 570, 254, 719], 'corrected_badge_mask': [0, 570, 260, 719],
          'text_line_count_before_and_after': 545, 'changes': changes,
          'source_candidate_transcription_modified': False}
(HERE / 'pixel-line-geometry-correction-v2.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(changes))
