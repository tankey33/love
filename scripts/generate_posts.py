#!/usr/bin/env python3
from pathlib import Path
import json, re, html

ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / 'blog' / 'posts'
OUT = ROOT / 'blog' / 'posts.json'
RENDER_DIR = ROOT / 'blog' / 'rendered'


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
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
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


posts = []
RENDER_DIR.mkdir(parents=True, exist_ok=True)
for path in sorted(POSTS_DIR.glob('*.md')):
    text = path.read_text(encoding='utf-8')
    meta, body = parse_frontmatter(text)
    title = meta.get('title') or path.stem
    date = meta.get('date', '')
    summary = meta.get('summary') or re.sub(r'\s+', ' ', body.strip()).split('\n')[0][:120]
    rendered_name = f'{path.stem}.html'
    rendered_path = RENDER_DIR / rendered_name
    rendered_path.write_text(md_to_html(body) + '\n', encoding='utf-8')
    posts.append({
        'slug': path.stem,
        'title': title,
        'date': date,
        'summary': summary,
        'path': f'blog/posts/{path.name}',
        'renderedPath': f'blog/rendered/{rendered_name}'
    })

posts.sort(key=lambda x: x.get('date', ''), reverse=True)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'generated {OUT} with {len(posts)} posts')
