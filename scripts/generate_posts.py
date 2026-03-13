#!/usr/bin/env python3
from pathlib import Path
import json, re, html, struct
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / 'blog' / 'posts'
POSTS_OUT = ROOT / 'blog' / 'posts.json'
RENDER_DIR = ROOT / 'blog' / 'rendered'
PHOTO_DIR = ROOT / 'photo'
PHOTO_OUT = ROOT / 'assets' / 'js' / 'photo-data.js'
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}


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


def pretty_title(stem: str):
    s = re.sub(r'[-_]+', ' ', stem).strip()
    return s if s else stem


def generate_posts():
    posts = []
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(POSTS_DIR.glob('*.md')):
        if path.name == 'README.md' or path.name.startswith('_') or path.name.startswith('draft-'):
            continue
        text = path.read_text(encoding='utf-8')
        meta, body = parse_frontmatter(text)
        title = meta.get('title') or path.stem
        date = meta.get('date', '')
        summary = meta.get('summary') or re.sub(r'\s+', ' ', body.strip()).split('\n')[0][:120]
        rendered_name = f'{path.stem}.html'
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
    posts.sort(key=lambda x: (not x.get('pinned', False), -parse_date(x.get('date', '')).timestamp()))
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
        photos.append({
            'id': path.stem,
            'file': path.name,
            'full': f'photo/{path.name}',
            'width': size[0],
            'height': size[1],
            'size': st.st_size,
            'title': pretty_title(path.stem),
            'description': '',
            'mtime': int(st.st_mtime)
        })
    content = 'window.PHOTO_DATA = ' + json.dumps(photos, ensure_ascii=False, indent=2) + ';\n'
    PHOTO_OUT.parent.mkdir(parents=True, exist_ok=True)
    PHOTO_OUT.write_text(content, encoding='utf-8')
    print(f'generated {PHOTO_OUT} with {len(photos)} photos')


if __name__ == '__main__':
    generate_posts()
    generate_photos()
