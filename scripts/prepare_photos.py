#!/usr/bin/env python3
"""Prepare public gallery media without publishing private embedded metadata.

Normal builds leave source files alone and write sanitized full-size copies and
responsive WebP thumbnails. --sanitize-source explicitly updates current source
files after saving permitted shooting metadata in their JSON sidecars. JPEG
entropy-coded image data is copied byte for byte; it is never recompressed.

Location is private by default. A sidecar may opt a travel photo into approximate
location with {"isTravel": true, "shareLocation": true}, or the explicit
{"locationPrivacy": "city"} policy. Coordinates are rounded to 0.1 degree and
never embedded in public images. hideLocation:true always overrides either opt-in.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import struct
import unicodedata
import zlib
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageOps, TiffImagePlugin

ROOT = Path(__file__).resolve().parents[1]
PHOTO_DIR = ROOT / 'photo'
GENERATED = ROOT / 'assets' / 'generated' / 'photos'
MANIFEST_PATH = ROOT / '.photo-build.json'
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
VIDEO_EXTS = {'.mov', '.mp4', '.m4v'}
TEXT_FIELDS = {
    'make', 'camera', 'lens', 'software', 'description', 'title', 'artist',
    'copyright', 'timeZone', 'originalName', 'city', 'country', 'aperture',
    'shutter', 'focalLength', 'focalLength35', 'exposureCompensation', 'flash',
    'whiteBalance', 'colorSpace', 'exposureProgram', 'exposureMode',
    'meteringMode', 'sceneCaptureType', 'contrast', 'saturation', 'sharpness',
}
NUMBER_RANGES = {
    'aperture': (0.1, 256), 'shutterSeconds': (0.000001, 86400),
    'iso': (1, 10_000_000), 'focalLength': (0.1, 20000),
    'focalLength35': (0.1, 40000), 'exposureCompensation': (-30, 30),
    'flash': (0, 65535), 'whiteBalance': (0, 10), 'colorSpace': (0, 65535),
    'orientation': (1, 8), 'exposureProgram': (0, 100), 'exposureMode': (0, 100),
    'meteringMode': (0, 255), 'sceneCaptureType': (0, 100), 'contrast': (0, 10),
    'saturation': (0, 10), 'sharpness': (0, 10), 'brightnessValue': (-100, 100),
    'subjectDistance': (0, 1_000_000), 'digitalZoom': (0, 1000),
    'originalSize': (0, 1_000_000_000), 'originalLastModified': (0, 9_000_000_000_000),
}
ROOT_EXIF_FIELDS = {
    0x010f: 'make', 0x0110: 'camera', 0x0131: 'software',
    0x013b: 'artist', 0x8298: 'copyright', 0x0112: 'orientation',
}
SHOOTING_EXIF_FIELDS = {
    0xa434: 'lens', 0x829d: 'aperture', 0x829a: 'shutterSeconds',
    0x8827: 'iso', 0x920a: 'focalLength', 0xa405: 'focalLength35',
    0x9204: 'exposureCompensation', 0x9209: 'flash', 0xa403: 'whiteBalance',
    0xa001: 'colorSpace', 0x8822: 'exposureProgram', 0xa402: 'exposureMode',
    0x9207: 'meteringMode', 0xa406: 'sceneCaptureType', 0xa408: 'contrast',
    0xa409: 'saturation', 0xa40a: 'sharpness', 0x9203: 'brightnessValue',
    0x9206: 'subjectDistance', 0xa404: 'digitalZoom', 0x9011: 'timeZone',
}
RATIONAL_TAGS = {0x829d, 0x829a, 0x920a, 0x9204, 0x9203, 0x9206, 0xa404}


def clean_text(value, device=False):
    if not isinstance(value, str):
        return ''
    value = unicodedata.normalize('NFKC', value).strip().strip('\x00')
    if not value or len(value) > 300 or '\ufffd' in value:
        return ''
    if any(unicodedata.category(char) == 'Cc' for char in value):
        return ''
    value = re.sub(r'\s+', ' ', value)
    if device:
        if len(value) < 2 or re.match(r'^\d{4}[:/-]\d{2}', value):
            return ''
        if sum(32 <= ord(char) < 127 for char in value) / len(value) < .9:
            return ''
        if sum(char.isalnum() for char in value) / len(value) < .45:
            return ''
    return value


def normalize_date(value):
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value or '').strip()
    if not re.match(r'^\d{4}[:-]\d{2}[:-]\d{2}(?:[ T]|$)', text):
        return ''
    text = re.sub(r'^(\d{4}):(\d{2}):(\d{2})', r'\1-\2-\3', text)
    try:
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        if not 1900 <= parsed.year <= datetime.now().year + 2:
            return ''
        return parsed.isoformat()
    except ValueError:
        return ''


def sanitize_metadata(source):
    """Use a field allowlist, never a denylist of ever-changing serial tags."""
    if not isinstance(source, dict):
        return {}
    out = {}
    for field in sorted(TEXT_FIELDS):
        text = clean_text(source.get(field), field in {'make', 'camera', 'lens', 'software'})
        if text:
            out[field] = text
    for field, (minimum, maximum) in NUMBER_RANGES.items():
        value = source.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and minimum <= value <= maximum:
            out[field] = value
    for field in ('takenAt', 'uploadedAt'):
        value = normalize_date(source.get(field))
        if value:
            out[field] = value
    if re.fullmatch(r'[a-f0-9]{40}', str(source.get('originalSha', ''))):
        out['originalSha'] = source['originalSha']
    hidden = source.get('hideLocation') is True
    travel = source.get('isTravel') is True and source.get('shareLocation') is True
    city_policy = source.get('locationPrivacy') == 'city'
    if hidden:
        out['hideLocation'] = True
    elif travel or city_policy:
        out.update({'isTravel': True, 'shareLocation': True, 'locationPrivacy': 'city'})
        lat, lon = source.get('latitude'), source.get('longitude')
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
            out.update(latitude=round(lat, 1), longitude=round(lon, 1))
    if hidden or not (travel or city_policy):
        out.pop('city', None)
        out.pop('country', None)
    # A source filename may itself be a GPS string; never use it as a location.
    return out


def embedded_metadata(path):
    """Pillow resolves TIFF offsets and endianness, unlike the retired parser."""
    with Image.open(path) as image:
        root = image.getexif()
        try:
            exif = root.get_ifd(0x8769)
        except (KeyError, TypeError, ValueError, SyntaxError):
            exif = {}
        result = {field: root.get(tag) for tag, field in ROOT_EXIF_FIELDS.items()}
        result.update({field: exif.get(tag) for tag, field in SHOOTING_EXIF_FIELDS.items()})
        result['takenAt'] = exif.get(0x9003) or exif.get(0x9004) or root.get(0x0132)
        for field, value in list(result.items()):
            if isinstance(value, TiffImagePlugin.IFDRational):
                try:
                    result[field] = float(value)
                except (ValueError, ZeroDivisionError):
                    result.pop(field, None)
        # GPS is read locally only, then the sidecar opt-in decides publication.
        try:
            gps = root.get_ifd(0x8825)
            def decimal(values, ref):
                value = sum(float(item) / divisor for item, divisor in zip(values, (1, 60, 3600)))
                return -value if ref in ('S', 'W', b'S', b'W') else value
            if gps.get(2) and gps.get(4):
                result['latitude'] = decimal(gps[2], gps.get(1))
                result['longitude'] = decimal(gps[4], gps.get(3))
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            pass
        return result


def safe_metadata_for_photo(path):
    saved = {}
    sidecar = path.with_suffix('.json')
    if sidecar.exists():
        try:
            saved = json.loads(sidecar.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            pass
    if not isinstance(saved, dict):
        saved = {}
    # Validate first: a corrupt embedded field must not replace a valid sidecar.
    safe_saved = sanitize_metadata(saved)
    embedded = embedded_metadata(path)
    safe_embedded = sanitize_metadata({**embedded, **{key: saved[key] for key in ('isTravel', 'shareLocation', 'locationPrivacy', 'hideLocation') if key in saved}})
    merged = {**safe_saved, **safe_embedded}
    if 'uploadedAt' not in merged:
        # Retain the true Git-introduced date before sanitization changes mtime.
        import subprocess
        try:
            uploaded = subprocess.check_output(['git', 'log', '-1', '--format=%aI', '--', path.relative_to(ROOT).as_posix()], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError, ValueError):
            uploaded = ''
        merged['uploadedAt'] = normalize_date(uploaded) or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    return sanitize_metadata(merged)


def safe_exif_bytes(metadata):
    """Rebuild only documented shooting tags; no GPS, MakerNote or serial IDs."""
    exif = Image.Exif()
    for tag, field in ROOT_EXIF_FIELDS.items():
        if field in metadata:
            exif[tag] = int(metadata[field]) if field == 'orientation' else metadata[field]
    shooting = {}
    for tag, field in SHOOTING_EXIF_FIELDS.items():
        value = metadata.get(field)
        if value is None or value == '':
            continue
        if tag in RATIONAL_TAGS and isinstance(value, (int, float)):
            fraction = Fraction(str(value)).limit_denominator(1_000_000)
            value = TiffImagePlugin.IFDRational(fraction.numerator, fraction.denominator)
        elif tag not in (0xa434, 0x9011) and not isinstance(value, (int, float)):
            continue
        elif tag not in (0xa434, 0x9011):
            value = int(value)
        shooting[tag] = value
    if metadata.get('takenAt'):
        taken = datetime.fromisoformat(metadata['takenAt']).strftime('%Y:%m:%d %H:%M:%S')
        shooting[0x9003] = taken
        shooting[0x9004] = taken
        exif[0x0132] = taken
    if shooting:
        exif[0x8769] = shooting
    return exif.tobytes() if exif else b''


def orientation_only_exif(orientation):
    """Byte-identical to the Worker's lossless JPEG normalization for dedup."""
    if not isinstance(orientation, (int, float)) or orientation != int(orientation) or not 2 <= orientation <= 8:
        return b''
    return bytes([69, 120, 105, 102, 0, 0, 73, 73, 42, 0, 8, 0, 0, 0, 1, 0, 18, 1, 3, 0, 1, 0, 0, 0, int(orientation), 0, 0, 0, 0, 0, 0, 0])


def sanitize_jpeg(data, exif=b''):
    if data[:2] != b'\xff\xd8':
        raise ValueError('Invalid JPEG signature')
    parts = [data[:2]]
    if exif:
        parts.append(b'\xff\xe1' + struct.pack('>H', len(exif) + 2) + exif)
    pos = 2
    while pos < len(data):
        start = pos
        if data[pos] != 0xff:
            raise ValueError('Invalid JPEG marker')
        while pos < len(data) and data[pos] == 0xff:
            pos += 1
        marker = data[pos]
        pos += 1
        if marker in (0xda, 0xd9):
            end = data.find(b'\xff\xd9', pos)
            parts.append(data[start:end + 2] if end >= 0 else data[start:])
            break
        if marker == 0x01 or 0xd0 <= marker <= 0xd8:
            parts.append(data[start:pos])
            continue
        length = int.from_bytes(data[pos:pos + 2], 'big')
        end = pos + length
        if length < 2 or end > len(data):
            raise ValueError('Invalid JPEG segment')
        # APP1 includes EXIF/XMP, APP13 includes IPTC. COM may contain private text.
        payload = data[pos + 2:end]
        render_app = (marker == 0xe0 and payload.startswith((b'JFIF\0', b'JFXX\0'))) or (marker == 0xe2 and payload.startswith(b'ICC_PROFILE\0')) or (marker == 0xee and payload.startswith(b'Adobe'))
        if marker != 0xfe and (not 0xe0 <= marker <= 0xef or render_app):
            parts.append(data[start:end])
        pos = end
    return b''.join(parts)


def png_chunk(kind, payload):
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)


def sanitize_png(data, exif=b''):
    parts, pos = [data[:8]], 8
    while pos + 12 <= len(data):
        length = int.from_bytes(data[pos:pos + 4], 'big')
        kind, end = data[pos + 4:pos + 8], pos + length + 12
        if end > len(data):
            raise ValueError('Invalid PNG chunk')
        if kind in {b'IHDR', b'PLTE', b'IDAT', b'IEND', b'tRNS', b'gAMA', b'cHRM', b'sRGB', b'iCCP', b'sBIT', b'bKGD', b'pHYs', b'hIST', b'sPLT', b'acTL', b'fcTL', b'fdAT'}:
            parts.append(data[pos:end])
        if kind == b'IHDR' and exif:
            parts.append(png_chunk(b'eXIf', exif.removeprefix(b'Exif\0\0')))
        pos = end
        if kind == b'IEND':
            break
    return b''.join(parts)


def sanitize_webp(data, exif=b''):
    parts, pos = [], 12
    while pos + 8 <= len(data):
        kind = data[pos:pos + 4]
        length = int.from_bytes(data[pos + 4:pos + 8], 'little')
        end = pos + 8 + length + (length & 1)
        if end > len(data):
            raise ValueError('Invalid WebP chunk')
        if kind in {b'VP8X', b'VP8 ', b'VP8L', b'ALPH', b'ANIM', b'ANMF', b'ICCP'}:
            chunk = bytearray(data[pos:end])
            if kind == b'VP8X':
                chunk[8] &= ~0x0c
                if exif:
                    chunk[8] |= 0x08
            parts.append(bytes(chunk))
        pos = end
    if exif:
        parts.append(b'EXIF' + len(exif).to_bytes(4, 'little') + exif + (b'\0' if len(exif) & 1 else b''))
    payload = b'WEBP' + b''.join(parts)
    return b'RIFF' + len(payload).to_bytes(4, 'little') + payload


def sanitize_gif(data):
    """Strip comment/XMP extensions while copying every animation frame intact."""
    if len(data) < 13:
        raise ValueError('Invalid GIF')
    pos = 13 + (3 * (2 ** ((data[10] & 7) + 1)) if data[10] & 0x80 else 0)
    parts = [data[:pos]]
    def subblocks(at):
        while at < len(data):
            length = data[at]
            at += length + 1
            if not length:
                return at
        raise ValueError('Invalid GIF subblock')
    while pos < len(data):
        start, marker = pos, data[pos]
        if marker == 0x3b:
            parts.append(data[pos:pos + 1])
            break
        if marker == 0x21:
            label = data[pos + 1]
            pos = subblocks(pos + 2)
            # Graphic control and Netscape loop extensions affect playback.
            app = data[start + 3:start + 14]
            if label == 0xf9 or (label == 0xff and app in (b'NETSCAPE2.0', b'ANIMEXTS1.0')):
                parts.append(data[start:pos])
        elif marker == 0x2c:
            packed = data[pos + 9]
            pos += 10 + (3 * (2 ** ((packed & 7) + 1)) if packed & 0x80 else 0)
            pos = subblocks(pos + 1)  # LZW code size before image data
            parts.append(data[start:pos])
        else:
            raise ValueError('Invalid GIF block')
    return b''.join(parts)


def sanitize_video(data):
    """Remove MOV/MP4 metadata atoms in place, preserving sample byte offsets."""
    result = bytearray(data)
    containers = {b'moov', b'trak', b'mdia', b'minf', b'stbl', b'edts', b'dinf', b'mvex', b'moof', b'traf'}
    def atoms(start, limit, depth=0):
        pos = start
        if depth > 12:
            raise ValueError('Invalid video atom nesting')
        while pos + 8 <= limit:
            length = int.from_bytes(result[pos:pos + 4], 'big')
            kind, header = bytes(result[pos + 4:pos + 8]), 8
            if length == 1:
                length, header = int.from_bytes(result[pos + 8:pos + 16], 'big'), 16
            elif length == 0:
                length = limit - pos
            if length < header or pos + length > limit:
                raise ValueError('Invalid video atom size')
            if kind in (b'udta', b'meta', b'uuid', b'XMP_'):
                result[pos + 4:pos + 8] = b'free'
                result[pos + header:pos + length] = b'\0' * (length - header)
            elif kind in containers:
                atoms(pos + header, pos + length, depth + 1)
            pos += length
    atoms(0, len(result))
    return bytes(result)


def sanitize_media_bytes(path, metadata=None):
    data = path.read_bytes()
    ext = path.suffix.lower()
    exif = safe_exif_bytes(metadata or {})
    if ext in ('.jpg', '.jpeg'):
        return sanitize_jpeg(data, exif)
    if ext == '.png':
        return sanitize_png(data, exif)
    if ext == '.webp':
        return sanitize_webp(data, exif)
    if ext == '.gif':
        return sanitize_gif(data)
    if ext in VIDEO_EXTS:
        return sanitize_video(data)
    raise ValueError(f'Unsupported media: {path.name}')


def write_changed(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def prepare(sanitize_source=False):
    GENERATED.mkdir(parents=True, exist_ok=True)
    manifest, expected, changed_sources, upload_index = {}, set(), 0, {}
    images = sorted(path for path in PHOTO_DIR.iterdir() if path.suffix.lower() in IMAGE_EXTS and path.is_file())
    for path in images:
        metadata = safe_metadata_for_photo(path)
        if sanitize_source and not metadata.get('originalSha'):
            original = path.read_bytes()
            metadata['originalSha'] = hashlib.sha1(f'blob {len(original)}\0'.encode() + original).hexdigest()
        safe_data = sanitize_media_bytes(path, metadata)
        if sanitize_source:
            changed_sources += int(path.read_bytes() != safe_data)
            write_changed(path, safe_data)
            sidecar = json.dumps(metadata, ensure_ascii=False, indent=2).encode() + b'\n'
            write_changed(path.with_suffix('.json'), sidecar)
            upload_index[metadata['originalSha']] = path.relative_to(ROOT).as_posix()
            if path.suffix.lower() in ('.jpg', '.jpeg'):
                normalized = sanitize_jpeg(safe_data, orientation_only_exif(metadata.get('orientation')))
                normalized_sha = hashlib.sha1(f'blob {len(normalized)}\0'.encode() + normalized).hexdigest()
                upload_index[normalized_sha] = path.relative_to(ROOT).as_posix()
        digest = hashlib.sha256(safe_data).hexdigest()[:12]
        name = f'{path.stem}-{digest}'
        full_name = name + path.suffix.lower()
        write_changed(GENERATED / full_name, safe_data)
        expected.add(full_name)
        with Image.open(io.BytesIO(safe_data)) as original:
            oriented = ImageOps.exif_transpose(original)
            width, height = oriented.size
            variants = []
            for target in (400, 800, 1600):
                target_name = f'{name}-{target}.webp'
                expected.add(target_name)
                # Skip byte-identical rebuilds. A source hash invalidates all sizes.
                if not (GENERATED / target_name).exists():
                    thumb = oriented.copy()
                    thumb.thumbnail((target, max(1, round(height * target / width))), Image.Resampling.LANCZOS)
                    if thumb.mode not in ('RGB', 'RGBA'):
                        thumb = thumb.convert('RGBA' if 'transparency' in thumb.info else 'RGB')
                    thumb.save(GENERATED / target_name, 'WEBP', quality=84, method=5, exif=b'', xmp=b'')
                variants.append((f'assets/generated/photos/{target_name}', min(target, width)))
        unique_variants = {actual_width: url for url, actual_width in variants}
        manifest[path.name] = {
            'full': f'assets/generated/photos/{full_name}',
            'thumb': variants[1][0],
            'srcset': ', '.join(f'{url} {actual_width}w' for actual_width, url in sorted(unique_variants.items())),
            'width': width, 'height': height, 'size': len(safe_data), 'metadata': metadata,
        }
    # Sanitized public videos preserve live companions without leaking GPS atoms.
    for path in sorted(PHOTO_DIR.iterdir()):
        if path.suffix.lower() not in VIDEO_EXTS or not path.is_file():
            continue
        safe_data = sanitize_media_bytes(path)
        if sanitize_source:
            original = path.read_bytes()
            upload_index[hashlib.sha1(f'blob {len(original)}\0'.encode() + original).hexdigest()] = path.relative_to(ROOT).as_posix()
            changed_sources += int(path.read_bytes() != safe_data)
            write_changed(path, safe_data)
        filename = f'{path.stem}-{hashlib.sha256(safe_data).hexdigest()[:12]}{path.suffix.lower()}'
        expected.add(filename)
        write_changed(GENERATED / filename, safe_data)
        manifest[path.name] = {'full': f'assets/generated/photos/{filename}'}
    for old in GENERATED.iterdir():
        if old.is_file() and old.name not in expected:
            old.unlink()
    write_changed(MANIFEST_PATH, (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode())
    if sanitize_source:
        write_changed(PHOTO_DIR / '_upload-index.json', (json.dumps(upload_index, sort_keys=True) + '\n').encode())
    print(f'Prepared {len(images)} photos; generated sanitized public copies and 400/800/1600 WebP variants.')
    if sanitize_source:
        print(f'Sanitized {changed_sources} current source media files; allowed EXIF saved in same-name JSON sidecars. Git history was not changed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sanitize-source', action='store_true', help='Explicitly sanitize current source media and sidecars after backup; does not rewrite Git history.')
    prepare(parser.parse_args().sanitize_source)
