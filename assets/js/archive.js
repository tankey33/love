(() => {
  'use strict';
  const type = document.body.dataset.archiveType;
  if (!['movie', 'music'].includes(type)) return;
  const movie = type === 'movie';
  const pageSize = movie ? 20 : 30;
  const archivePath = movie ? 'data/movies.json' : 'data/music.json';
  const fallbackPath = movie ? 'data/movie-trending.json' : 'data/music-trending.json';
  const grid = document.getElementById('grid');
  const liveGrid = document.getElementById('liveGrid');
  const more = document.getElementById('more');
  const search = document.getElementById('search');
  const count = document.getElementById('count');
  const liveStatus = document.getElementById('liveStatus');
  const cacheKey = 'love-artwork-v2-' + type;
  let all = [], shown = pageSize, query = '', artworkRequests = 0, activeArtwork = 0;
  let artCache = {};
  try { artCache = JSON.parse(localStorage.getItem(cacheKey) || '{}') || {}; } catch (_) { /* Storage may be disabled. */ }
  const artworkQueue = [];
  const inFlight = new Map();

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = String(text);
    return node;
  }

  function safeURL(value) {
    if (typeof value !== 'string' || !value.trim()) return '';
    try {
      const url = new URL(value, location.href);
      return ['https:', 'http:'].includes(url.protocol) ? url.href : '';
    } catch (_) { return ''; }
  }

  function artworkURL(value) {
    const url = safeURL(value);
    return url.includes('mzstatic.com/')
      ? url.replace(/\/\d+x\d+(bb)?\.(jpg|png)/i, '/600x600bb.$2') : url;
  }

  async function getJSON(url, timeout = 8000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(url, {cache: 'no-cache', signal: controller.signal});
      if (!response.ok) throw new Error('请求失败');
      return await response.json();
    } finally { clearTimeout(timer); }
  }

  const imageObserver = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const image = entry.target;
      image.src = image.dataset.src;
      imageObserver.unobserve(image);
    });
  }, {rootMargin: '200px'}) : null;

  function putImage(cover, source, eager = false) {
    const url = artworkURL(source);
    if (!url || cover.querySelector('img')) return;
    const image = element('img');
    image.alt = '';
    image.decoding = 'async';
    image.loading = eager ? 'eager' : 'lazy';
    image.referrerPolicy = 'no-referrer';
    image.width = 600;
    image.height = movie ? 900 : 600;
    image.addEventListener('load', () => image.classList.add('loaded'), {once: true});
    image.addEventListener('error', () => {
      image.classList.add('failed');
      image.removeAttribute('src');
      cover.classList.add('artwork-unavailable');
    }, {once: true});
    cover.prepend(image);
    if (eager || !imageObserver) image.src = url;
    else { image.dataset.src = url; imageObserver.observe(image); }
  }

  function normalize(item) {
    const title = String(item.title || item.name || '未名');
    const sub = String(movie ? item.director || item.artistName || item.english || item.year || '' : item.artist || item.artistName || item.genre || '');
    const fallback = movie ? 'https://search.douban.com/movie/subject_search?search_text=' : 'https://music.apple.com/cn/search?term=';
    return {
      title, sub,
      art: artworkURL(item.posterUrl || item.artworkUrl100 || item.artworkUrl),
      url: safeURL(item.doubanUrl || item.storeUrl || item.url) || fallback + encodeURIComponent(title + (movie ? '' : ' ' + sub)),
      rating: Number(typeof item.rating === 'object' ? item.rating?.value : item.rating),
      summary: String(item.summary || item.description || item.card_subtitle || '暂无简介'),
      search: String(item.english || title)
    };
  }

  function card(raw, index, live = false) {
    const item = normalize(raw);
    const link = element('a', 'card');
    link.href = item.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.setAttribute('aria-label', item.title + (item.sub ? '，' + item.sub : '') + '（在新标签页打开）');
    const cover = element('div', 'cover');
    cover.dataset.glyph = item.title.slice(0, 3);
    const cached = artCache[item.search] || artCache[item.title];
    const image = item.art || artworkURL(cached?.art);
    if (image) putImage(cover, image, live && index < (innerWidth < 600 ? 2 : 4));
    else if (artworkObserver) {
      cover.dataset.artworkTitle = movie ? item.search : item.title + ' ' + item.sub;
      artworkObserver.observe(cover);
    }
    if (live) cover.append(element('span', 'rank', String(index + 1).padStart(2, '0')));
    if (movie) {
      const hover = element('div', 'douban-hover');
      hover.setAttribute('aria-hidden', 'true');
      const score = element('div', 'douban-score');
      score.append(element('span', '', '豆瓣综合评分'), element('strong', '', Number.isFinite(item.rating) && item.rating > 0 ? item.rating.toFixed(1) : '暂无'));
      hover.append(score, element('p', '', item.summary));
      cover.append(hover);
    }
    const copy = element('div', 'copy');
    copy.append(element('h3', '', item.title), element('p', '', item.sub || '静静收藏'));
    link.append(cover, copy);
    return link;
  }

  async function findArtwork(title) {
    if (artCache[title]) return artCache[title];
    if (inFlight.has(title)) return inFlight.get(title);
    if (artworkRequests >= 12) return null;
    artworkRequests++;
    const promise = (async () => {
      try {
        const params = new URLSearchParams({term: title, country: movie ? 'US' : 'CN', media: type, entity: movie ? 'movie' : 'song', limit: '1'});
        const data = await getJSON('https://itunes.apple.com/search?' + params, 4500);
        const hit = data.results?.[0];
        const art = artworkURL(hit?.artworkUrl100);
        if (!art) return null;
        artCache[title] = {art, url: safeURL(hit.trackViewUrl || hit.collectionViewUrl)};
        try { localStorage.setItem(cacheKey, JSON.stringify(artCache)); } catch (_) { /* Browsing remains available. */ }
        return artCache[title];
      } catch (_) { return null; }
      finally { inFlight.delete(title); }
    })();
    inFlight.set(title, promise);
    return promise;
  }

  async function drainArtworkQueue() {
    if (activeArtwork >= 2) return;
    const cover = artworkQueue.shift();
    if (!cover) return;
    if (!cover.isConnected) { drainArtworkQueue(); return; }
    activeArtwork++;
    try {
      const found = await findArtwork(cover.dataset.artworkTitle);
      if (found?.art && cover.isConnected) putImage(cover, found.art);
    } finally { activeArtwork--; drainArtworkQueue(); }
  }

  const artworkObserver = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      artworkObserver.unobserve(entry.target);
      artworkQueue.push(entry.target);
      drainArtworkQueue();
    });
  }, {rootMargin: '120px'}) : null;

  function clearCards(container) {
    container.querySelectorAll('img').forEach(image => imageObserver?.unobserve(image));
    container.querySelectorAll('[data-artwork-title]').forEach(cover => artworkObserver?.unobserve(cover));
    container.replaceChildren();
  }

  function showError(container, text, retry) {
    clearCards(container);
    const status = element('div', 'status', text);
    status.setAttribute('role', 'status');
    const button = element('button', 'retry-button', '重新加载');
    button.type = 'button';
    button.addEventListener('click', retry);
    status.append(button);
    container.append(status);
    container.setAttribute('aria-busy', 'false');
  }

  function filtered() {
    const term = query.toLocaleLowerCase();
    return all.filter(item => !term || [item.title, item.name, item.artist, item.director, item.english, item.year, item.genre, item.tags?.join(' '), item.summary].join(' ').toLocaleLowerCase().includes(term));
  }

  function render() {
    const list = filtered();
    count.textContent = query ? '找到 ' + list.length + ' 则' : '共 ' + list.length + ' 则';
    clearCards(grid);
    const fragment = document.createDocumentFragment();
    list.slice(0, shown).forEach((item, index) => fragment.append(card(item, index)));
    if (!list.length) fragment.append(element('p', 'status', '没有找到匹配的' + (movie ? '电影' : '音乐') + '，换个关键词试试。'));
    grid.append(fragment);
    grid.setAttribute('aria-busy', 'false');
    more.hidden = list.length <= shown;
    more.textContent = '再看一些（还剩 ' + Math.max(0, list.length - shown) + ' 则）';
  }

  async function loadArchive() {
    grid.setAttribute('aria-busy', 'true');
    try {
      const data = await getJSON(archivePath);
      if (!Array.isArray(data)) throw new Error('Invalid collection');
      all = data.filter(item => item && typeof item === 'object');
      const heroCount = document.getElementById('heroCount');
      if (heroCount) heroCount.textContent = all.length;
      render();
    } catch (_) {
      showError(grid, '馆藏暂时未能打开，请再试一次。', loadArchive);
      count.textContent = '加载未完成';
    }
  }

  function renderLive(list, status) {
    clearCards(liveGrid);
    const fragment = document.createDocumentFragment();
    list.slice(0, 20).forEach((item, index) => fragment.append(card(item, index, true)));
    liveGrid.append(fragment);
    liveGrid.setAttribute('aria-busy', 'false');
    liveStatus.textContent = status;
  }

  async function loadLive() {
    liveGrid.setAttribute('aria-busy', 'true');
    let hasSnapshot = false;
    try {
      const list = await getJSON(fallbackPath);
      if (!Array.isArray(list) || !list.length) throw new Error('Empty snapshot');
      renderLive(list, movie && list[0]?.syncedAt ? '豆瓣同步 · ' + list[0].syncedAt : '馆藏快照');
      hasSnapshot = true;
    } catch (_) {
      if (movie) showError(liveGrid, '热门电影暂时未能打开，馆藏仍可正常浏览。', loadLive);
    }
    if (movie) return;
    try {
      const data = await getJSON('https://rss.applemarketingtools.com/api/v2/cn/music/most-played/20/songs.json', 4000);
      const results = data.feed?.results;
      if (!Array.isArray(results) || !results.length) throw new Error('Empty feed');
      renderLive(results, 'Apple Music · ' + new Date().toLocaleDateString('zh-CN'));
    } catch (_) {
      if (!hasSnapshot) showError(liveGrid, '榜单暂时未能打开，馆藏仍可正常浏览。', loadLive);
    }
  }

  let inputTimer;
  search.addEventListener('input', () => {
    clearTimeout(inputTimer);
    inputTimer = setTimeout(() => { query = search.value.trim(); shown = pageSize; render(); }, 120);
  });
  more.addEventListener('click', () => {
    const previous = shown;
    shown += pageSize;
    render();
    grid.querySelectorAll('.card')[previous]?.focus({preventScroll: true});
  });
  loadArchive();
  loadLive();
})();
