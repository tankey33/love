#!/usr/bin/env python3
from pathlib import Path
import json, re

ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / 'blog' / 'posts'
OUT = ROOT / 'blog' / 'posts.json'

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
    return meta, body

posts = []
for path in sorted(POSTS_DIR.glob('*.md')):
    text = path.read_text(encoding='utf-8')
    meta, body = parse_frontmatter(text)
    title = meta.get('title') or path.stem
    date = meta.get('date', '')
    summary = meta.get('summary') or re.sub(r'\s+', ' ', body.strip()).split('\n')[0][:120]
    posts.append({
        'slug': path.stem,
        'title': title,
        'date': date,
        'summary': summary,
        'path': f'blog/posts/{path.name}'
    })

posts.sort(key=lambda x: x.get('date', ''), reverse=True)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'generated {OUT} with {len(posts)} posts')
