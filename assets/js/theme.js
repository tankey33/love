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
    if('serviceWorker'in navigator&&location.protocol==='https:')navigator.serviceWorker.register('sw.js').catch(()=>{});
  },{once:true});
})();
