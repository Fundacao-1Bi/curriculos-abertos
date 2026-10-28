"""Bounded Portuguese OCR with word geometry and immutable page cache.

Source bytes are never executed. Call from the isolated document worker, after
page.remove_rotation() when applicable. Coordinates use the supplied page.rect
(display coordinates), so the same words can feed native table/column adapters.
An OCR result is an extraction candidate, never a pedagogical verification.
"""
from __future__ import annotations

import contextlib
import csv
import fcntl
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
OCR_REVISION = 'tesseract-tsv-por-v1.2.1'
MAX_DIMENSION = 2200
MAX_TSV_BYTES = 16 * 1024 * 1024
MAX_WORDS = 30000
TIMEOUT_SECONDS = 60
_ENGINE_VERSION: str | None = None


class OcrError(RuntimeError):
    """Actionable failure: the caller must retain the source and pending state."""


def _engine_version() -> str:
    global _ENGINE_VERSION
    if _ENGINE_VERSION is None:
        executable = shutil.which('tesseract')
        if executable is None:
            raise OcrError('Tesseract is unavailable; install tesseract-ocr and Portuguese language data in the worker.')
        try:
            result = subprocess.run([executable, '--version'], check=True,
                                    capture_output=True, timeout=5)
        except (subprocess.SubprocessError, OSError) as error:
            raise OcrError('Cannot identify the configured Tesseract engine.') from error
        _ENGINE_VERSION = (result.stdout or result.stderr).decode('utf-8', 'replace').splitlines()[0]
    return _ENGINE_VERSION


def _configuration() -> dict[str, Any]:
    import pymupdf
    # Environment is operator configuration, never document-derived arguments.
    language = os.getenv('OCR_LANGUAGE', 'por')
    if not re.fullmatch(r'[a-z_]+(?:\+[a-z_]+)*', language):
        raise OcrError('OCR_LANGUAGE must contain installed language names, for example por or por+eng.')
    try:
        psm = int(os.getenv('OCR_PSM', '3'))
    except ValueError as error:
        raise OcrError('OCR_PSM must be one of 3, 6, 11 or 12.') from error
    if psm not in (3, 6, 11, 12):
        raise OcrError('OCR_PSM must be one of 3, 6, 11 or 12.')
    tessdata = os.getenv('TESSDATA_PREFIX')
    model_hashes: dict[str, str | None] = {}
    for name in language.split('+'):
        path = Path(tessdata) / f'{name}.traineddata' if tessdata else None
        model_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path and path.is_file() else None
    try:
        threads = int(os.getenv('OCR_THREADS', '1'))
    except ValueError as error:
        raise OcrError('OCR_THREADS must be between 1 and 4.') from error
    if threads < 1 or threads > 4:
        raise OcrError('OCR_THREADS must be between 1 and 4.')
    osd = _osd_model()
    autorotate = os.getenv('OCR_AUTOROTATE', 'true').lower() not in ('0', 'false', 'off')
    return {'revision': OCR_REVISION, 'engine': _engine_version(),
            'rasterizer': f'PyMuPDF {pymupdf.VersionBind}',
            'language': language, 'psm': psm, 'max_dimension': MAX_DIMENSION,
            'model_sha256': model_hashes, 'threads': threads,
            'autorotate': autorotate,
            'orientation_model_sha256': hashlib.sha256(osd.read_bytes()).hexdigest() if osd and autorotate else None}


def _osd_model() -> Path | None:
    candidates = [Path(os.environ['TESSDATA_PREFIX']) / 'osd.traineddata'] if os.getenv('TESSDATA_PREFIX') else []
    candidates += [Path(folder) / 'osd.traineddata' for folder in (
        '/usr/share/tesseract-ocr/5/tessdata', '/usr/share/tesseract-ocr/4.00/tessdata',
        '/usr/share/tessdata', '/opt/homebrew/share/tessdata')]
    return next((path for path in candidates if path.is_file()), None)


def _orientation(image_path: Path, config: Mapping[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    if not config['autorotate']:
        return 0, []
    model = _osd_model()
    if model is None:
        return 0, [{'issue': 'ocr_orientation_detection_unavailable',
                    'status': 'install_tesseract_osd_for_sideways_scanned_tables'}]
    command = [shutil.which('tesseract') or 'tesseract', str(image_path), 'stdout',
               '--tessdata-dir', str(model.parent), '-l', 'osd', '--psm', '0']
    try:
        result = subprocess.run(command, capture_output=True, timeout=15,
                                env={**os.environ, 'OMP_THREAD_LIMIT': str(config['threads'])})
    except (subprocess.SubprocessError, OSError):
        return 0, [{'issue': 'ocr_orientation_detection_failed', 'status': 'requires_documentary_review'}]
    text = result.stdout.decode('utf-8', 'replace')
    rotate = re.search(r'^Rotate:\s*(0|90|180|270)\s*$', text, re.MULTILINE)
    confidence = re.search(r'^Orientation confidence:\s*([0-9.]+)', text, re.MULTILINE)
    if result.returncode != 0 or rotate is None or confidence is None:
        return 0, [{'issue': 'ocr_orientation_inconclusive', 'status': 'requires_documentary_review'}]
    value = float(confidence.group(1))
    if value < 1.5:
        return 0, [{'issue': 'ocr_orientation_low_confidence', 'confidence': value,
                    'suggested_rotation': int(rotate.group(1)), 'status': 'requires_documentary_review'}]
    return int(rotate.group(1)), []


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _load_cache(path: Path, expected_key: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        if path.stat().st_size > MAX_TSV_BYTES * 2:
            return None
        result = json.loads(path.read_text())
        if result.get('cache_key') != expected_key or result.get('revision') != OCR_REVISION:
            return None
        if not isinstance(result.get('text'), str) or not isinstance(result.get('words'), list):
            return None
        if len(result['words']) > MAX_WORDS or result.get('word_count') != len(result['words']):
            return None
        digest = result.get('result_sha256')
        unsigned = {key: value for key, value in result.items() if key not in ('result_sha256', 'cache_hit')}
        if digest != hashlib.sha256(_canonical(unsigned)).hexdigest():
            return None
        return {**result, 'cache_hit': True}
    except (OSError, ValueError, TypeError):
        return None


@contextlib.contextmanager
def _page_lock(path: Path):
    # A worker restart releases the OS lock. A second worker reuses the completed
    # immutable cache instead of performing the same OCR operation concurrently.
    with path.open('a+b') as lock:
        os.chmod(path, 0o600)
        deadline = time.monotonic() + TIMEOUT_SECONDS + 15
        while True:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise OcrError('Timed out waiting for the OCR page lease; retry the durable source job.')
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def ocr_page(page: Any, source: Mapping[str, Any], page_number: int) -> dict[str, Any]:
    """Return OCR text and word boxes in original supplied page display units.

    Keys required by ingest: text, words, warnings, method. Additional metadata
    identifies engine/model, coordinates, source hash, page and cache integrity.
    No result here asserts that code/text pairs or full tables were reconciled.
    """
    if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
        raise OcrError('page_number must be a positive 1-based integer.')
    rectangle = page.rect
    if not all(math.isfinite(value) for value in (rectangle.x0, rectangle.y0, rectangle.width, rectangle.height)):
        raise OcrError('PDF page has invalid dimensions.')
    if rectangle.width <= 0 or rectangle.height <= 0:
        raise OcrError('PDF page has empty dimensions.')
    config = _configuration()
    digest = source.get('sha256')
    if digest is not None and not re.fullmatch(r'[0-9a-fA-F]{64}', str(digest)):
        raise OcrError('Source sha256 is invalid; validate source integrity before OCR.')
    digest = str(digest).lower() if digest else None
    identity = {'artifact_sha256': digest, 'page': page_number,
                'rect': [rectangle.x0, rectangle.y0, rectangle.width, rectangle.height],
                'rotation': page.rotation, 'configuration': config}
    image = None
    factor = min(2.5, MAX_DIMENSION / max(rectangle.width, rectangle.height))
    # Normal ingestion has an already verified source hash and can reuse the
    # page cache before rasterization. Standalone callers fall back to pixel hash.
    if digest is None:
        import pymupdf
        image = page.get_pixmap(matrix=pymupdf.Matrix(factor, factor), alpha=False)
        identity['pixel_sha256'] = hashlib.sha256(image.samples).hexdigest()
    key = hashlib.sha256(_canonical(identity)).hexdigest()
    cache_root = ROOT / 'data' / 'extracted' / 'ocr'
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_path = cache_root / f'{key}.json'
    cached = _load_cache(cache_path, key)
    if cached is not None:
        return {**cached, 'source_id': source.get('id')}
    with _page_lock(cache_root / f'{key}.lock'):
        cached = _load_cache(cache_path, key)
        if cached is not None:
            return {**cached, 'source_id': source.get('id')}
        if image is None:
            import pymupdf
            image = page.get_pixmap(matrix=pymupdf.Matrix(factor, factor), alpha=False)
        if image.width > MAX_DIMENSION + 1 or image.height > MAX_DIMENSION + 1:
            raise OcrError('Rasterized page exceeds the OCR dimension bound.')
        executable = shutil.which('tesseract')
        if executable is None:
            raise OcrError('Tesseract disappeared from the worker runtime.')
        with tempfile.TemporaryDirectory(prefix='curriculos-ocr-') as temporary:
            image_path = Path(temporary) / 'page.png'
            output_path = Path(temporary) / 'words.tsv'
            image.save(image_path)
            rotation, orientation_warnings = _orientation(image_path, config)
            import pymupdf
            render_matrix = pymupdf.Matrix(factor, factor).prerotate(rotation)
            if rotation:
                image = page.get_pixmap(matrix=render_matrix, alpha=False)
                image.save(image_path)
            command = [executable, str(image_path), 'stdout', '-l', config['language'],
                       '--psm', str(config['psm']), '-c', 'tessedit_create_tsv=1']
            try:
                with output_path.open('wb') as output:
                    completed = subprocess.run(command, stdout=output,
                                               stderr=subprocess.PIPE,
                                               timeout=TIMEOUT_SECONDS, check=False,
                                               env={**os.environ, 'OMP_THREAD_LIMIT': str(config['threads'])})
            except subprocess.TimeoutExpired as error:
                raise OcrError('Tesseract exceeded the 60-second page bound; retain source and retry with a targeted OCR configuration.') from error
            except OSError as error:
                raise OcrError('Tesseract could not start in the document worker.') from error
            if completed.returncode != 0:
                # Tesseract stderr contains filenames/language diagnostics, never
                # source text or operator environment/credentials.
                detail = completed.stderr.decode('utf-8', 'replace')[:600]
                raise OcrError(f'Tesseract failed for this page (exit {completed.returncode}): {detail}')
            if output_path.stat().st_size > MAX_TSV_BYTES:
                raise OcrError('OCR output exceeded the bounded TSV size.')
            tsv = output_path.read_text(encoding='utf-8', errors='replace')
        warnings: list[dict[str, Any]] = [dict(warning, page=page_number) for warning in orientation_warnings]
        if completed.stderr.strip():
            warnings.append({'page': page_number, 'issue': 'ocr_engine_diagnostic',
                             'detail': completed.stderr.decode('utf-8', 'replace')[:600]})
        words: list[dict[str, Any]] = []
        layout_words: list[dict[str, Any]] = []
        layout_to_original = pymupdf.Matrix(factor, 0, 0, factor, image.x, image.y) * ~render_matrix
        lines: dict[tuple[int, int, int], list[str]] = {}
        low_confidence = 0
        reader = csv.DictReader(io.StringIO(tsv), delimiter='\t', quoting=csv.QUOTE_NONE)
        required_columns = {'level', 'left', 'top', 'width', 'height', 'conf', 'text'}
        if not required_columns.issubset(reader.fieldnames or []):
            raise OcrError('Tesseract did not produce a valid TSV header; check output configuration and language data.')
        for row in reader:
            if row.get('level') != '5' or not (row.get('text') or '').strip():
                continue
            try:
                left, top, width, height, confidence = (float(row[name]) for name in ('left', 'top', 'width', 'height', 'conf'))
                block, paragraph, line = (int(row[name]) for name in ('block_num', 'par_num', 'line_num'))
            except (ValueError, KeyError, TypeError) as error:
                raise OcrError('Tesseract produced an invalid word geometry row.') from error
            if not all(math.isfinite(value) for value in (left, top, width, height, confidence)) or width < 0 or height < 0:
                raise OcrError('Tesseract produced non-finite or negative geometry.')
            # Pixmap x/y include the rotated rendering origin. Inverting the
            # exact matrix maps every word box back to the supplied PDF space.
            mapped = pymupdf.Rect(left + image.x, top + image.y,
                                  left + width + image.x, top + height + image.y) * ~render_matrix
            x0, x1 = max(rectangle.x0, mapped.x0), min(rectangle.x1, mapped.x1)
            y0, y1 = max(rectangle.y0, mapped.y0), min(rectangle.y1, mapped.y1)
            text = row['text']
            words.append({'x0': x0, 'top': y0, 'x1': x1, 'bottom': y1,
                          'text': text, 'confidence': confidence,
                          'block': block, 'paragraph': paragraph, 'line': line})
            layout_words.append({'x0': max(0, min(image.width, left)) / factor,
                                 'top': max(0, min(image.height, top)) / factor,
                                 'x1': max(0, min(image.width, left + width)) / factor,
                                 'bottom': max(0, min(image.height, top + height)) / factor,
                                 'text': text, 'confidence': confidence,
                                 'block': block, 'paragraph': paragraph, 'line': line})
            lines.setdefault((block, paragraph, line), []).append(text)
            if confidence < 60:
                low_confidence += 1
            if len(words) > MAX_WORDS:
                raise OcrError('OCR page exceeded the bounded word count.')
        text = '\n'.join(' '.join(parts) for parts in lines.values())
        if not words:
            warnings.append({'page': page_number, 'issue': 'ocr_no_words',
                             'status': 'source_page_requires_review'})
        if low_confidence:
            warnings.append({'page': page_number, 'issue': 'ocr_low_confidence_words',
                             'count': low_confidence, 'denominator': len(words),
                             'status': 'requires_documentary_review'})
        result: dict[str, Any] = {'revision': OCR_REVISION,
            'method': 'tesseract-tsv-por', 'cache_key': key,
            'artifact_sha256': digest,
            'page': page_number, 'text': text, 'words': words,
            'layout_words': layout_words,
            'layout_rect': [0, 0, image.width / factor, image.height / factor],
            'layout_coordinate_space': 'upright_ocr_page_points',
            'layout_to_original': list(layout_to_original),
            'word_count': len(words), 'warnings': warnings,
            'coordinate_space': 'supplied_page.rect_display_units',
            'page_rect': [rectangle.x0, rectangle.y0, rectangle.x1, rectangle.y1],
            'raster_dimensions': [image.width, image.height],
            'ocr_rotation_applied': rotation,
            'pdf_to_raster_matrix': list(render_matrix),
            'configuration': config,
            'actor_type': 'automated',
            'review_status': 'ocr_candidate_not_documentary_reconciliation'}
        result['result_sha256'] = hashlib.sha256(_canonical(result)).hexdigest()
        descriptor, temporary_name = tempfile.mkstemp(prefix=key + '-', suffix='.tmp', dir=cache_root)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(_canonical(result))
            os.replace(temporary_name, cache_path)
        finally:
            Path(temporary_name).unlink(missing_ok=True)
        return {**result, 'cache_hit': False, 'source_id': source.get('id')}
