#!/usr/bin/env python3
from pathlib import Path
import json, re, html, struct, subprocess, unicodedata
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / 'blog' / 'posts'
POSTS_OUT = ROOT / 'blog' / 'posts.json'
RENDER_DIR = ROOT / 'blog' / 'rendered'
PHOTO_DIR = ROOT / 'photo'
PHOTO_OUT = ROOT / 'assets' / 'js' / 'photo-data.js'
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
VIDEO_EXTS = {'.mov', '.mp4', '.m4v'}


def parse_frontmatter(text: str):
    meta = {}
    body = text
    if text.startswith('---'):
        m = re.match(r'^---\n([\s\S]*?)\n---\n?([\s\S]*)$', text)
        if m:
            raw, body = m.groups()
            for line in raw.splitlines():
                if ':' in line:
                    k, v = line.split(':', 1)
                    meta[k.strip()] = v.strip()
    return meta, body.strip()


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def inline_md(text: str) -> str:
    text = esc(text)
    text = re.sub(r'&lt;(https?://[^&]+)&gt;', r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', text)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    def repl_link(m):
        label, href = m.group(1), m.group(2)
        if href.startswith('http://') or href.startswith('https://'):
            return f'<a href="{href}" target="_blank" rel="noopener noreferrer">{label}</a>'
        return f'<a href="{href}">{label}</a>'
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', repl_link, text)
    return text


def parse_table(lines, start):
    if start + 1 >= len(lines):
        return None, start
    head = lines[start]
    sep = lines[start + 1]
    if '|' not in head or not re.match(r'^\s*\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$', sep):
        return None, start
    rows = [head]
    i = start + 2
    while i < len(lines) and '|' in lines[i].strip() and lines[i].strip():
        rows.append(lines[i])
        i += 1
    def split_row(line):
        return [p.strip() for p in line.strip().strip('|').split('|')]
    headers = split_row(rows[0])
    body_rows = [split_row(r) for r in rows[1:]]
    html_out = ['<table><thead><tr>']
    html_out += [f'<th>{inline_md(c)}</th>' for c in headers]
    html_out += ['</tr></thead><tbody>']
    for row in body_rows:
        html_out.append('<tr>')
        html_out += [f'<td>{inline_md(c)}</td>' for c in row]
        html_out.append('</tr>')
    html_out.append('</tbody></table>')
    return ''.join(html_out), i


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out = []
    i = 0
    in_code = False
    code_lang = ''
    code_buf = []
    para = []
    list_type = None
    list_items = []
    quote_buf = []

    def flush_para():
        nonlocal para
        if para:
            out.append(f"<p>{inline_md(' '.join(x.strip() for x in para))}</p>")
            para = []

    def flush_list():
        nonlocal list_items, list_type
        if list_items:
            tag = 'ol' if list_type == 'ol' else 'ul'
            out.append(f'<{tag}>')
            for item in list_items:
                out.append(f'<li>{inline_md(item)}</li>')
            out.append(f'</{tag}>')
            list_items = []
            list_type = None

    def flush_quote():
        nonlocal quote_buf
        if quote_buf:
            out.append(f"<blockquote><p>{inline_md(' '.join(x.strip() for x in quote_buf))}</p></blockquote>")
            quote_buf = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if in_code:
            if stripped.startswith('```'):
                out.append(f'<pre><code class="language-{code_lang}">{html.escape(chr(10).join(code_buf))}</code></pre>')
                in_code = False
                code_lang = ''
                code_buf = []
            else:
                code_buf.append(line)
            i += 1
            continue

        if stripped.startswith('```'):
            flush_para(); flush_list(); flush_quote()
            in_code = True
            code_lang = stripped[3:].strip()
            i += 1
            continue

        table_html, new_i = parse_table(lines, i)
        if table_html:
            flush_para(); flush_list(); flush_quote()
            out.append(table_html)
            i = new_i
            continue

        if not stripped:
            flush_para(); flush_list(); flush_quote()
            i += 1
            continue

        if re.fullmatch(r'---+', stripped):
            flush_para(); flush_list(); flush_quote()
            out.append('<hr>')
            i += 1
            continue

        m = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if m:
            flush_para(); flush_list(); flush_quote()
            level = len(m.group(1))
            out.append(f'<h{level}>{inline_md(m.group(2))}</h{level}>')
            i += 1
            continue

        m = re.match(r'^>\s?(.*)$', stripped)
        if m:
            flush_para(); flush_list()
            quote_buf.append(m.group(1))
            i += 1
            continue

        m = re.match(r'^[-*]\s+(.*)$', stripped)
        if m:
            flush_para(); flush_quote()
            if list_type not in (None, 'ul'):
                flush_list()
            list_type = 'ul'
            list_items.append(m.group(1))
            i += 1
            continue

        m = re.match(r'^\d+\.\s+(.*)$', stripped)
        if m:
            flush_para(); flush_quote()
            if list_type not in (None, 'ol'):
                flush_list()
            list_type = 'ol'
            list_items.append(m.group(1))
            i += 1
            continue

        para.append(line)
        i += 1

    flush_para(); flush_list(); flush_quote()
    return '\n'.join(out)


def parse_date(v: str):
    try:
        return datetime.strptime(v, '%Y-%m-%d')
    except Exception:
        return datetime.min


def jpg_size(path: Path):
    with path.open('rb') as f:
        data = f.read(24)
        if data[:2] != b'\xff\xd8':
            return None
        f.seek(2)
        while True:
            byte = f.read(1)
            if not byte:
                return None
            while byte == b'\xff':
                byte = f.read(1)
            marker = byte[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                f.read(3)
                h, w = struct.unpack('>HH', f.read(4))
                return w, h
            else:
                size = struct.unpack('>H', f.read(2))[0]
                f.seek(size - 2, 1)


def png_size(path: Path):
    with path.open('rb') as f:
        header = f.read(24)
        if header[:8] != b'\x89PNG\r\n\x1a\n':
            return None
        return struct.unpack('>II', header[16:24])


def gif_size(path: Path):
    with path.open('rb') as f:
        header = f.read(10)
        if header[:3] != b'GIF':
            return None
        return struct.unpack('<HH', header[6:10])


def webp_size(path: Path):
    with path.open('rb') as f:
        header = f.read(40)
        if header[:4] != b'RIFF' or header[8:12] != b'WEBP':
            return None
        chunk = header[12:16]
        if chunk == b'VP8 ':
            return struct.unpack('<HH', header[26:30])
        if chunk == b'VP8L':
            b0, b1, b2, b3 = header[21:25]
            width = 1 + (((b1 & 0x3F) << 8) | b0)
            height = 1 + (((b3 & 0x0F) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6))
            return width, height
        if chunk == b'VP8X':
            width = 1 + int.from_bytes(header[24:27], 'little')
            height = 1 + int.from_bytes(header[27:30], 'little')
            return width, height
        return None


def image_size(path: Path):
    ext = path.suffix.lower()
    try:
        if ext in {'.jpg', '.jpeg'}:
            return jpg_size(path)
        if ext == '.png':
            return png_size(path)
        if ext == '.gif':
            return gif_size(path)
        if ext == '.webp':
            return webp_size(path)
    except Exception:
        return None
    return None


def jpeg_exif(path: Path):
    """Read the small EXIF subset used by the gallery without extra packages."""
    if path.suffix.lower() not in {'.jpg', '.jpeg'}:
        return {}
    try:
        data = path.read_bytes()
        if data[:2] != b'\xff\xd8':
            return {}
        pos = 2
        tiff = None
        while pos + 4 < len(data):
            if data[pos] != 0xff:
                pos += 1
                continue
            marker = data[pos + 1]
            if marker in (0xd8, 0xd9):
                pos += 2
                continue
            length = int.from_bytes(data[pos + 2:pos + 4], 'big')
            if marker == 0xe1 and data[pos + 4:pos + 10] == b'Exif\x00\x00':
                tiff = data[pos + 10:pos + 2 + length]
                break
            pos += 2 + max(length, 2)
        if not tiff or tiff[:2] not in (b'II', b'MM'):
            return {}
        order = 'little' if tiff[:2] == b'II' else 'big'
        u16 = lambda o: int.from_bytes(tiff[o:o + 2], order)
        u32 = lambda o: int.from_bytes(tiff[o:o + 4], order)
        type_sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}

        def value(entry):
            typ, count = u16(entry + 2), u32(entry + 4)
            size = type_sizes.get(typ, 1) * count
            start = entry + 8 if size <= 4 else u32(entry + 8)
            raw = tiff[start:start + size]
            if typ == 2:
                return raw.split(b'\x00', 1)[0].decode('utf-8', 'ignore').strip()
            if typ == 3:
                return int.from_bytes(raw[:2], order)
            if typ in (4, 9):
                return int.from_bytes(raw[:4], order, signed=typ == 9)
            if typ in (5, 10) and len(raw) >= 8:
                n = int.from_bytes(raw[:4], order, signed=typ == 10)
                d = int.from_bytes(raw[4:8], order, signed=typ == 10)
                return n / d if d else None
            return None

        def directory(offset):
            if offset < 0 or offset + 2 > len(tiff):
                return {}
            count = u16(offset)
            out = {}
            for i in range(min(count, 256)):
                entry = offset + 2 + i * 12
                if entry + 12 <= len(tiff):
                    out[u16(entry)] = value(entry)
            return out

        root = directory(u32(4))
        exif = directory(root.get(0x8769, 0)) if root.get(0x8769) else {}
        taken = exif.get(0x9003) or exif.get(0x9004) or root.get(0x0132)
        result = {
            'takenAt': taken,
            'make': root.get(0x010f),
            'camera': root.get(0x0110),
            'lens': exif.get(0xa434),
            'aperture': exif.get(0x829d),
            'shutterSeconds': exif.get(0x829a),
            'iso': exif.get(0x8827),
            'focalLength': exif.get(0x920a),
            'focalLength35': exif.get(0xa405),
            'exposureCompensation': exif.get(0x9204),
            'flash': exif.get(0x9209),
            'whiteBalance': exif.get(0xa403),
            'software': root.get(0x0131),
        }
        return {k: v for k, v in result.items() if v not in (None, '')}
    except Exception:
        return {}


def normalize_photo_date(value):
    if not value:
        return ''
    text = str(value).strip()
    for fmt in ('%Y:%m:%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(text[:19], fmt).isoformat()
        except ValueError:
            pass
    return ''


def clean_metadata_text(value, device=False):
    """Keep useful EXIF text while hiding damaged byte-decoding artifacts."""
    if value is None:
        return ''
    if not isinstance(value, str):
        return value
    text = unicodedata.normalize('NFKC', value)
    text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Cc')
    text = re.sub(r'\s+', ' ', text).strip()
    if not text or len(text) > 180 or '\ufffd' in text:
        return ''
    if device:
        compact = [ch for ch in text if not ch.isspace()]
        meaningful = sum(ch.isalnum() for ch in compact)
        if len(text) < 2 or not compact or meaningful / len(compact) < .58:
            return ''
        if re.match(r'^\d{4}[:/-]\d{2}[:/-]\d{2}\s+\d{2}:\d{2}', text):
            return ''
    return text


def git_upload_date(path: Path, fallback: float):
    """Use the commit that introduced/last replaced the file as its upload date."""
    try:
        relative = path.relative_to(ROOT).as_posix()
        value = subprocess.check_output(
            ['git', 'log', '-1', '--format=%aI', '--', relative],
            cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
        if value:
            return value
    except Exception:
        pass
    return datetime.fromtimestamp(fallback, timezone.utc).isoformat()


def pretty_title(stem: str):
    s = re.sub(r'[-_]+', ' ', stem).strip()
    return s if s else stem


def strip_duplicate_leading_title(body: str, title: str) -> str:
    """Remove a leading Markdown H1 when the page template already renders it."""
    lines = body.splitlines()
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first is None:
        return body
    match = re.match(r'^\s*#\s+(.+?)\s*#*\s*$', lines[first])
    if not match:
        return body
    heading = re.sub(r'[*_`~]+', '', match.group(1)).strip()
    if heading != title.strip():
        return body
    del lines[first]
    while first < len(lines) and not lines[first].strip():
        del lines[first]
    return '\n'.join(lines)


def generate_posts():
    posts = []
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    expected_rendered = set()
    for path in sorted(POSTS_DIR.glob('*.md')):
        if path.name == 'README.md' or path.name.startswith('_') or path.name.startswith('draft-'):
            continue
        text = path.read_text(encoding='utf-8')
        meta, body = parse_frontmatter(text)
        title = meta.get('title') or path.stem
        body = strip_duplicate_leading_title(body, title)
        date = meta.get('date', '')
        summary = meta.get('summary') or re.sub(r'\s+', ' ', body.strip()).split('\n')[0][:120]
        rendered_name = f'{path.stem}.html'
        expected_rendered.add(rendered_name)
        rendered_path = RENDER_DIR / rendered_name
        rendered_path.write_text(md_to_html(body) + '\n', encoding='utf-8')
        pinned = str(meta.get('pinned', '')).lower() in ('true', '1', 'yes', 'on')
        cover = meta.get('cover', '').strip()
        posts.append({
            'slug': path.stem,
            'title': title,
            'date': date,
            'summary': summary,
            'path': f'blog/posts/{path.name}',
            'renderedPath': f'blog/rendered/{rendered_name}',
            'pinned': pinned,
            'cover': cover
        })
    for old in RENDER_DIR.glob('*.html'):
        if old.name not in expected_rendered:
            old.unlink()
    posts.sort(key=lambda x: (not x.get('pinned', False), -parse_date(x.get('date', '')).toordinal()))
    POSTS_OUT.parent.mkdir(parents=True, exist_ok=True)
    POSTS_OUT.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'generated {POSTS_OUT} with {len(posts)} posts')


def generate_photos():
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    photos = []
    files = [p for p in PHOTO_DIR.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for i, path in enumerate(files, start=1):
        size = image_size(path) or (0, 0)
        st = path.stat()
        sidecar = path.with_suffix('.json')
        saved = {}
        if sidecar.exists():
            try:
                saved = json.loads(sidecar.read_text(encoding='utf-8'))
            except Exception:
                saved = {}
        # Prefer the image's own standard EXIF over older sidecars. Early browser
        # uploads could misread big-endian TIFF offsets; sidecars still supply
        # fields that are no longer embedded after client-side compression.
        embedded = jpeg_exif(path)
        exif = {**saved, **{k: v for k, v in embedded.items() if v not in (None, '')}}
        taken_at = normalize_photo_date(exif.get('takenAt'))
        uploaded_at = exif.get('uploadedAt') or git_upload_date(path, st.st_mtime)
        live_video = next((path.with_suffix(ext) for ext in VIDEO_EXTS if path.with_suffix(ext).exists()), None)
        make = clean_metadata_text(exif.get('make', ''), True)
        camera = clean_metadata_text(exif.get('camera', ''), True)
        if re.match(r'^(?:ILCE|NEX|DSC)(?:-|$)', str(make), re.I) and not camera:
            camera, make = make, 'SONY'
        photos.append({
            'id': path.stem,
            'file': path.name,
            'full': f'photo/{path.name}',
            'width': size[0],
            'height': size[1],
            'size': st.st_size,
            'title': pretty_title(path.stem),
            'description': clean_metadata_text(exif.get('description', '')),
            'takenAt': taken_at,
            'uploadedAt': uploaded_at,
            'dateSource': 'exif' if taken_at else 'upload',
            'make': make,
            'camera': camera,
            'lens': clean_metadata_text(exif.get('lens', ''), True),
            'aperture': ('f/' + ('%.1f' % exif['aperture']).rstrip('0').rstrip('.')) if isinstance(exif.get('aperture'), (int, float)) else exif.get('aperture', ''),
            'shutter': (('1/%d s' % round(1 / exif['shutterSeconds'])) if exif.get('shutterSeconds', 0) and exif['shutterSeconds'] < 1 else ('%.2f s' % exif['shutterSeconds'])) if isinstance(exif.get('shutterSeconds'), (int, float)) else exif.get('shutter', ''),
            'iso': exif.get('iso', ''),
            'focalLength': (('%.1f mm' % exif['focalLength']).replace('.0 ', ' ')) if isinstance(exif.get('focalLength'), (int, float)) else exif.get('focalLength', ''),
            'focalLength35': (str(exif['focalLength35']) + ' mm') if isinstance(exif.get('focalLength35'), (int, float)) else exif.get('focalLength35', ''),
            'exposureCompensation': (('%+.1f EV' % exif['exposureCompensation'])) if isinstance(exif.get('exposureCompensation'), (int, float)) else exif.get('exposureCompensation', ''),
            'flash': ('闪光' if int(exif['flash']) & 1 else '未闪光') if isinstance(exif.get('flash'), (int, float)) else exif.get('flash', ''),
            'whiteBalance': ('手动' if int(exif['whiteBalance']) else '自动') if isinstance(exif.get('whiteBalance'), (int, float)) else exif.get('whiteBalance', ''),
            'software': clean_metadata_text(exif.get('software', ''), True),
            'colorSpace': exif.get('colorSpace', ''),
            'artist': exif.get('artist', ''),
            'copyright': exif.get('copyright', ''),
            'latitude': exif.get('latitude', ''),
            'longitude': exif.get('longitude', ''),
            'timeZone': exif.get('timeZone', ''),
            'orientation': exif.get('orientation', ''),
            'exposureProgram': exif.get('exposureProgram', ''),
            'exposureMode': exif.get('exposureMode', ''),
            'meteringMode': exif.get('meteringMode', ''),
            'sceneCaptureType': exif.get('sceneCaptureType', ''),
            'contrast': exif.get('contrast', ''),
            'saturation': exif.get('saturation', ''),
            'sharpness': exif.get('sharpness', ''),
            'brightnessValue': exif.get('brightnessValue', ''),
            'subjectDistance': exif.get('subjectDistance', ''),
            'digitalZoom': exif.get('digitalZoom', ''),
            'isLivePhoto': bool(live_video),
            'liveVideo': f'photo/{live_video.name}' if live_video else '',
            'mtime': int(st.st_mtime)
        })
    content = 'window.PHOTO_DATA = ' + json.dumps(photos, ensure_ascii=False, indent=2) + ';\n'
    PHOTO_OUT.parent.mkdir(parents=True, exist_ok=True)
    PHOTO_OUT.write_text(content, encoding='utf-8')
    print(f'generated {PHOTO_OUT} with {len(photos)} photos')


if __name__ == '__main__':
    generate_posts()
    generate_photos()
