(() => {
  'use strict';
  const listPage = document.body.classList.contains('page-notes');
  const articlePage = document.body.classList.contains('page-note');
  if (!listPage && !articlePage) return;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = String(text);
    return node;
  }

  function safeURL(value, localOnly = false) {
    if (typeof value !== 'string' || !value.trim()) return '';
    try {
      const url = new URL(value, location.href);
      if (!['https:', 'http:'].includes(url.protocol) || (localOnly && url.origin !== location.origin)) return '';
      return url.href;
    } catch (_) { return ''; }
  }

  async function request(path, json = true) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(path, {cache: 'no-cache', signal: controller.signal});
      if (!response.ok) throw new Error('内容暂时无法打开');
      return json ? await response.json() : await response.text();
    } finally { clearTimeout(timer); }
  }

  async function posts() {
    const data = await request('blog/posts.json');
    if (!Array.isArray(data)) throw new Error('手记目录暂时无法打开');
    return data.filter(post => post && typeof post === 'object' && typeof post.slug === 'string' && post.slug !== 'README');
  }

  function error(container, message, retry) {
    const box = element('div', 'empty', message);
    box.setAttribute('role', 'status');
    if (retry) {
      const button = element('button', 'retry-button', '重新加载');
      button.type = 'button';
      button.addEventListener('click', retry);
      box.append(button);
    }
    container.replaceChildren(box);
    container.setAttribute('aria-busy', 'false');
  }

  function pickCover(post, index) {
    const fallback = ['photo/06.jpg', 'photo/21.jpg', 'photo/19.jpg', 'photo/04.jpg', 'photo/05.jpg'];
    const value = safeURL(post.cover) || safeURL(fallback[index % fallback.length]);
    const url = new URL(value);
    if (url.hostname === 'images.unsplash.com') {
      url.searchParams.set('w', innerWidth < 640 ? '800' : '1200');
      url.searchParams.set('q', '75');
      url.searchParams.set('auto', 'format');
    }
    return url.href;
  }

  if (listPage) {
    const lead = document.getElementById('lead');
    const grid = document.getElementById('grid');
    const input = document.getElementById('search-input');
    const status = document.getElementById('notes-status');
    const more = document.getElementById('notes-more');
    const pageSize = 12;
    let all = [], shown = pageSize, query = '';
    const coverObserver = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.src = entry.target.dataset.src;
        coverObserver.unobserve(entry.target);
      });
    }, {rootMargin: '300px'}) : null;
    const quotes = [
      '我们把世界看错了，反说它欺骗我们。—— 泰戈尔',
      '月色与雪色之间，你是第三种绝色。—— 余光中',
      '凌晨四点钟，看到海棠花未眠。—— 川端康成',
      '我明白你会来，所以我等。—— 沈从文',
      '岁月不饶人，我亦未曾饶过岁月。—— 木心',
      '有些事只适合收藏，不能说，也不能想，却又不能忘。—— 史铁生',
      '我曾踏月而来，只因你在山中。—— 席慕蓉',
      '凡是过去，皆为序章。—— 莎士比亚'
    ];
    document.getElementById('page-quote').textContent = quotes[Math.floor(Math.random() * quotes.length)];

    function card(post, index, featured = false) {
      const link = element('a', featured ? 'lead-card' : 'news-card');
      link.href = 'note.html?slug=' + encodeURIComponent(post.slug);
      const media = element('div', featured ? 'lead-media' : 'news-media');
      const image = element('img');
      image.alt = '';
      image.loading = featured ? 'eager' : 'lazy';
      image.decoding = 'async';
      image.width = 1200;
      image.height = 750;
      const source = pickCover(post, index);
      if (featured || !coverObserver) image.src = source;
      else { image.dataset.src = source; coverObserver.observe(image); }
      image.addEventListener('error', () => image.remove(), {once: true});
      media.append(image);
      const copy = element('div', featured ? 'lead-copy' : 'news-copy');
      const words = element('div');
      if (featured) words.append(element('div', 'kicker', post.pinned ? '置顶' : '最近更新'));
      words.append(element(featured ? 'h2' : 'h3', featured ? 'lead-title' : 'news-title', post.title || '未命名手记'));
      if (post.summary) words.append(element('p', featured ? 'lead-summary' : 'news-summary', post.summary));
      const date = element('time', featured ? 'date-row' : 'news-date', post.date || '未标注日期');
      if (/^\d{4}-\d{2}-\d{2}/.test(String(post.date))) date.dateTime = String(post.date).slice(0, 10);
      copy.append(words, date);
      link.append(media, copy);
      return link;
    }

    function render() {
      const term = query.toLocaleLowerCase();
      const filtered = all.filter(post => !term || [post.title, post.summary, post.date, post.slug].join(' ').toLocaleLowerCase().includes(term));
      status.textContent = query ? '找到 ' + filtered.length + ' 篇手记' : '共 ' + filtered.length + ' 篇手记';
      [...lead.querySelectorAll('img'), ...grid.querySelectorAll('img')].forEach(image => coverObserver?.unobserve(image));
      lead.replaceChildren();
      grid.replaceChildren();
      grid.setAttribute('aria-busy', 'false');
      if (!filtered.length) {
        grid.append(element('p', 'empty', query ? '没有找到匹配的文章，换个关键词试试。' : '还没有发布手记。'));
        more.hidden = true;
        return;
      }
      const first = filtered.find(post => post.pinned) || filtered[0];
      const rest = filtered.filter(post => post.slug !== first.slug);
      lead.append(card(first, 0, true));
      const fragment = document.createDocumentFragment();
      rest.slice(0, shown - 1).forEach((post, index) => fragment.append(card(post, index + 1)));
      grid.append(fragment);
      more.hidden = filtered.length <= shown;
      more.textContent = '再看一些（还剩 ' + Math.max(0, filtered.length - shown) + ' 篇）';
    }

    async function load() {
      status.textContent = '正在打开手记…';
      grid.setAttribute('aria-busy', 'true');
      try { all = await posts(); render(); }
      catch (_) { status.textContent = '手记加载未完成'; error(grid, '手记暂时未能打开，请再试一次。', load); }
    }

    let inputTimer;
    input.addEventListener('input', () => {
      clearTimeout(inputTimer);
      inputTimer = setTimeout(() => { query = input.value.trim(); shown = pageSize; render(); }, 120);
    });
    more.addEventListener('click', () => {
      const oldCount = shown - 1;
      shown += pageSize;
      render();
      grid.querySelectorAll('.news-card')[oldCount]?.focus({preventScroll: true});
    });
    load();
    return;
  }

  const title = document.getElementById('post-title');
  const summary = document.getElementById('post-summary');
  const content = document.getElementById('post-content');
  const date = document.getElementById('post-date');

  function articleFragment(html) {
    const parsed = new DOMParser().parseFromString(html, 'text/html');
    parsed.querySelectorAll('script,object,embed,base,meta,link').forEach(node => node.remove());
    parsed.body.querySelectorAll('*').forEach(node => {
      [...node.attributes].forEach(attribute => {
        if (/^on/i.test(attribute.name) || attribute.name === 'srcdoc') node.removeAttribute(attribute.name);
      });
      ['href', 'src', 'poster'].forEach(name => {
        const value = node.getAttribute(name);
        if (!value || (name === 'href' && (value.startsWith('#') || value.startsWith('mailto:')))) return;
        if (!safeURL(value)) node.removeAttribute(name);
      });
      if (node.tagName === 'A' && node.getAttribute('target') === '_blank') node.rel = 'noopener noreferrer';
      if (node.tagName === 'IMG') { node.loading = 'lazy'; node.decoding = 'async'; }
      if (node.tagName === 'IFRAME') { node.loading = 'lazy'; node.referrerPolicy = 'no-referrer'; }
    });
    const fragment = document.createDocumentFragment();
    fragment.append(...parsed.body.childNodes);
    return fragment;
  }

  function script(src) {
    return new Promise((resolve, reject) => {
      const node = document.createElement('script');
      node.src = src;
      node.async = true;
      const timer = setTimeout(() => { node.remove(); reject(new Error('组件加载超时')); }, 6000);
      node.onload = () => { clearTimeout(timer); resolve(); };
      node.onerror = () => { clearTimeout(timer); reject(new Error('组件加载失败')); };
      document.head.append(node);
    });
  }

  async function enhanceArticle() {
    const code = [...content.querySelectorAll('pre code')];
    code.forEach(block => {
      const pre = block.closest('pre');
      const wrap = element('div', 'code-wrap');
      const button = element('button', 'copy-btn', '复制代码');
      button.type = 'button';
      button.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(block.textContent);
          button.textContent = '已复制';
        } catch (_) { button.textContent = '请选择代码复制'; }
        setTimeout(() => { button.textContent = '复制代码'; }, 1800);
      });
      pre.before(wrap);
      wrap.append(button, pre);
    });
    if (code.length) {
      try {
        await script('https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.10.0/highlight.min.js');
        if (window.hljs) code.forEach(block => window.hljs.highlightElement(block));
      } catch (_) { /* Plain code remains readable if the optional highlighter is unavailable. */ }
    }
    const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, {
      acceptNode: node => node.parentElement.closest('pre,code,script,style,textarea') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT
    });
    const prose = [];
    while (walker.nextNode()) prose.push(walker.currentNode.textContent);
    if (/\$\$[\s\S]+?\$\$|(^|[^\\])\$[^$\n]{1,200}\$/m.test(prose.join('\n'))) {
      try {
        const link = element('link');
        link.rel = 'stylesheet';
        link.href = 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css';
        document.head.append(link);
        await script('https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js');
        await script('https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js');
        window.renderMathInElement?.(content, {delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}], throwOnError: false});
      } catch (_) { /* The original formula stays visible. */ }
    }
  }

  async function loadArticle() {
    const slug = new URLSearchParams(location.search).get('slug');
    if (!slug) { title.textContent = '未指定文章'; error(content, '请从手记目录选择一篇文章。'); return; }
    content.setAttribute('aria-busy', 'true');
    try {
      const list = await posts();
      const post = list.find(item => item.slug === slug);
      if (!post) { title.textContent = '文章不存在'; error(content, '这篇手记可能已移动，请返回全部手记查找。'); return; }
      title.textContent = String(post.title || '未命名手记');
      summary.textContent = String(post.summary || '');
      date.textContent = String(post.date || '');
      document.title = title.textContent + ' · Tankey × Monody';
      document.querySelector('meta[name="description"]').content = String(post.summary || post.title || 'Tankey 与 Monody 的手记');
      const path = safeURL(post.renderedPath || post.path, true);
      if (!path || !new URL(path).pathname.startsWith(new URL('blog/', location.href).pathname)) throw new Error('文章路径无效');
      const html = await request(path, false);
      content.replaceChildren(articleFragment(html));
      const firstHeading = content.firstElementChild;
      if (firstHeading?.tagName === 'H1' && firstHeading.textContent.trim() === title.textContent.trim()) firstHeading.remove();
      content.setAttribute('aria-busy', 'false');
      enhanceArticle();
    } catch (_) {
      if (title.textContent === '正在打开手记…') title.textContent = '手记暂时未能打开';
      error(content, '文章加载未完成，请再试一次。', loadArticle);
    }
  }
  loadArticle();
})();
