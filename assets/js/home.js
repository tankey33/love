(() => {
  'use strict';

  const DAY = 86400000;
  const CHINA_OFFSET = 8 * 60 * 60 * 1000;
  const START_LOCAL = Date.UTC(2017, 11, 29, 18, 20);
  const START_INSTANT = START_LOCAL - CHINA_OFFSET;
  const byId = id => document.getElementById(id);
  const chinaDate = instant => new Date(instant.getTime() + CHINA_OFFSET);

  function monthAnchor(months) {
    const year = 2017 + Math.floor((11 + months) / 12);
    const month = (11 + months) % 12;
    const day = Math.min(29, new Date(Date.UTC(year, month + 1, 0)).getUTCDate());
    return Date.UTC(year, month, day, 18, 20);
  }

  function updateTime() {
    const now = new Date();
    const local = chinaDate(now);
    const year = local.getUTCFullYear();
    let months = Math.max(0, (year - 2017) * 12 + local.getUTCMonth() - 11);
    if (local.getTime() < monthAnchor(months)) months = Math.max(0, months - 1);
    const days = Math.max(0, Math.floor((local.getTime() - monthAnchor(months)) / DAY));
    byId('timeTogether').textContent = `${Math.floor(months / 12)} 年 ${months % 12} 个月 ${days} 天`;
    byId('totalDays').textContent = `共 ${Math.max(0, Math.floor((now.getTime() - START_INSTANT) / DAY)).toLocaleString('zh-CN')} 天 · 始于 2017 年 12 月 29 日`;

    const anniversaryToday = local.getUTCMonth() === 11 && local.getUTCDate() === 29;
    let nextYear = year;
    let anniversary = Date.UTC(nextYear, 11, 29, 18, 20);
    if (local.getTime() >= anniversary) anniversary = Date.UTC(++nextYear, 11, 29, 18, 20);
    const years = nextYear - 2017;
    const remainingDays = Math.max(0, Math.ceil((anniversary - local.getTime()) / DAY));
    byId('anniversaryLabel').textContent = `第 ${years} 个周年纪念日`;
    byId('anniversaryCountdown').textContent = anniversaryToday
      ? `今天，我们一起走过了 ${year - 2017} 年。`
      : `距离下一次周年纪念日，还有 ${remainingDays} 天`;
    byId('anniversaryDate').textContent = `${nextYear} 年 12 月 29 日`;
  }

  function photoDate(photo) {
    let value = photo.takenAt || photo.uploadedAt || photo.date || (photo.mtime ? photo.mtime * 1000 : null);
    if (typeof value === 'string') {
      if (/^\d{4}-\d{2}-\d{2}$/.test(value)) value += 'T00:00:00+08:00';
      else if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value) && !/(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)) {
        value += /^(?:Z|[+-]\d{2}:\d{2})$/i.test(photo.timeZone || '') ? photo.timeZone : '+08:00';
      }
    }
    const date = value ? new Date(value) : null;
    return date && Number.isFinite(date.getTime()) ? date : null;
  }

  async function loadMemory() {
    try {
      const response = await fetch('assets/js/photo-data.json', {cache: 'no-cache'});
      if (!response.ok) throw new Error(`Photo index: ${response.status}`);
      const payload = await response.json();
      const photos = (Array.isArray(payload) ? payload : payload.photos || []).map(photo => ({photo, date: photoDate(photo)}))
        .filter(entry => entry.date && (entry.photo.thumb || entry.photo.thumbnail || entry.photo.full || entry.photo.src));
      if (!photos.length) return;
      photos.sort((a, b) => b.date - a.date || String(b.photo.id).localeCompare(String(a.photo.id), undefined, {numeric: true}));
      const today = chinaDate(new Date());
      const matches = photos.filter(({date}) => {
        const taken = chinaDate(date);
        return taken.getUTCFullYear() < today.getUTCFullYear() && taken.getUTCMonth() === today.getUTCMonth() && taken.getUTCDate() === today.getUTCDate();
      });
      const {photo, date} = matches[0] || photos[0];
      const image = byId('memoryImage');
      const source = photo.thumb || photo.thumbnail || photo.full || photo.src;
      const srcset = typeof photo.srcset === 'string' ? photo.srcset : '';
      byId('memoryLink').href = `photo.html#photo=${encodeURIComponent(photo.id ?? '')}`;
      byId('memoryHeading').textContent = matches.length ? '往年今日' : '最近的记忆';
      const memoryTitle = photo.description || (/\D/.test(photo.title || '') ? photo.title : '一个值得记住的日常。');
      byId('memoryTitle').textContent = memoryTitle.length > 48 ? `${memoryTitle.slice(0, 48)}…` : memoryTitle;
      byId('memoryDate').textContent = `${photo.takenAt ? '拍摄于' : '记录于'} ${new Intl.DateTimeFormat('zh-CN', {timeZone: 'Asia/Shanghai', dateStyle: 'long'}).format(date)}`;
      image.addEventListener('load', () => {
        image.classList.add('is-loaded');
        byId('memoryPlaceholder').hidden = true;
      }, {once: true});
      image.addEventListener('error', () => {
        if (photo.full && image.getAttribute('src') !== photo.full) {
          image.removeAttribute('srcset');
          image.src = photo.full;
        }
      }, {once: true});
      image.alt = photo.description || (/\D/.test(photo.title || '') ? photo.title : '一起走过的日常');
      image.hidden = false;
      if (srcset) {
        image.srcset = srcset;
        image.sizes = '(max-width: 600px) 112px, (max-width: 840px) 320px, 220px';
      }
      image.src = source;
    } catch (error) {
      console.warn('首页回忆暂未加载，可从写真页继续浏览。', error);
    }
  }

  updateTime();
  window.setInterval(() => { if (!document.hidden) updateTime(); }, 60000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) updateTime(); });
  loadMemory();
})();
