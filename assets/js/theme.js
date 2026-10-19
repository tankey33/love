(()=>{
  'use strict';
  const root=document.documentElement,system=matchMedia('(prefers-color-scheme:dark)');
  const read=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}};
  const save=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value))}catch{}};
  let choice=read('love-theme','system');
  function theme(){root.dataset.theme=choice==='system'?(system.matches?'dark':'light'):choice;const b=document.querySelector('.theme-toggle');if(b){b.textContent=root.dataset.theme==='dark'?'☾':'☀';b.setAttribute('aria-label','切换为'+(root.dataset.theme==='dark'?'日间':'夜间')+'主题');b.title='当前'+(root.dataset.theme==='dark'?'夜间':'日间')+'主题'}let meta=document.querySelector('meta[name="theme-color"]:not([media])');if(!meta){meta=document.createElement('meta');meta.name='theme-color';document.head.prepend(meta)}meta.content=root.dataset.theme==='dark'?'#1d1f1c':'#edf3f4'}
  theme();system.addEventListener('change',theme);
  document.addEventListener('DOMContentLoaded',()=>{
    const header=document.querySelector('.topbar-inner');if(header&&!header.querySelector('.theme-toggle')){const button=document.createElement('button');button.type='button';button.className='theme-toggle';header.append(button);button.addEventListener('click',()=>{choice=root.dataset.theme==='dark'?'light':'dark';save('love-theme',choice);theme()});theme()}
    const main=document.querySelector('main');if(main&&!document.querySelector('.skip-link')){main.id=main.id||'main-content';const skip=document.createElement('a');skip.className='skip-link';skip.href='#'+main.id;skip.textContent='跳到主要内容';document.body.prepend(skip)}
    document.querySelectorAll('.nav a.active').forEach(a=>a.setAttribute('aria-current','page'));
    let audio=document.getElementById('bgm');if(!audio){audio=document.createElement('audio');audio.id='bgm';audio.src='music/white.mp3';audio.preload='none';audio.loop=true;document.body.append(audio)}
    if(!document.querySelector('[data-music-toggle]')){const dock=document.createElement('details');dock.className='music-dock';dock.innerHTML='<summary><span class="music-indicator" aria-hidden="true"></span>背景音乐</summary><div class="music-dock-content"><button type="button" class="music-btn" data-music-toggle aria-label="播放背景音乐"></button><p data-music-title>White</p><label class="music-volume">音量<input data-music-volume type="range" min="0" max="1" step="0.05" aria-label="音乐音量"></label><p data-music-status class="music-status" role="status"></p></div>';document.body.append(dock)}
    const state=read('love-music',{});let wanted=state.playing===true,savedTime=Number(state.time)||0,lastSaved=0;
    audio.volume=Number.isFinite(state.volume)?Math.max(0,Math.min(1,state.volume)):.45;
    const status=message=>document.querySelectorAll('[data-music-status]').forEach(e=>e.textContent=message);
    const persist=()=>save('love-music',{playing:wanted,time:audio.currentTime||savedTime,volume:audio.volume});
    function update(){document.querySelectorAll('[data-music-toggle]').forEach(b=>{b.classList.toggle('is-playing',!audio.paused);b.setAttribute('aria-label',audio.paused?'播放背景音乐':'暂停背景音乐');b.setAttribute('aria-pressed',String(!audio.paused));b.innerHTML=audio.paused?'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 11 7-11 7z"/></svg>':'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>'});document.querySelector('.music-dock')?.classList.toggle('is-playing',!audio.paused);document.querySelectorAll('[data-music-volume]').forEach(e=>e.value=String(audio.volume))}
    async function play(){wanted=true;try{await audio.play();status('正在播放 · White')}catch{status('轻点播放，继续听 White')}persist();update()}
    function pause(){wanted=false;audio.pause();status('已暂停');persist();update()}
    document.querySelectorAll('[data-music-toggle]').forEach(b=>b.addEventListener('click',()=>audio.paused?play():pause()));
    document.querySelectorAll('[data-music-volume]').forEach(input=>input.addEventListener('input',()=>{audio.volume=Number(input.value);persist();update()}));
    document.querySelectorAll('[data-music-title]').forEach(e=>e.textContent='White');
    audio.addEventListener('loadedmetadata',()=>{if(savedTime&&Number.isFinite(audio.duration))audio.currentTime=Math.min(savedTime,audio.duration-.1)});
    audio.addEventListener('timeupdate',()=>{if(Date.now()-lastSaved>2000){lastSaved=Date.now();persist()}});
    audio.addEventListener('play',()=>{wanted=true;update();persist()});audio.addEventListener('pause',update);
    audio.addEventListener('error',()=>status('音乐暂时无法加载，可稍后重试'));
    addEventListener('pagehide',persist);document.addEventListener('visibilitychange',()=>{if(document.hidden)persist()});
    if(document.body.classList.contains('page-home')){let clicks=0,timer;document.addEventListener('click',e=>{if(e.target.closest('a,button,input,select,textarea,summary'))return;clicks++;clearTimeout(timer);if(clicks===3){clicks=0;play()}else timer=setTimeout(()=>{if(clicks===2)pause();clicks=0},320)})}
    update();if(wanted)play();else status('轻点播放背景音乐');
    if('serviceWorker'in navigator&&location.protocol==='https:')navigator.serviceWorker.register('sw.js').catch(()=>{});
  },{once:true});
})();
