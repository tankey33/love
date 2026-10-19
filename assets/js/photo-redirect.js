(()=>{const query=new URLSearchParams(location.search),id=query.get('photo')||query.get('id')||'';location.replace('photo.html'+(id?'#photo='+encodeURIComponent(id):''))})();
