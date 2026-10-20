(() => {
 const $=id=>document.getElementById(id);
 const safe=(s)=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
 const fmt=(num,digits=1)=>num==null?'—':Number(num).toFixed(digits);
 const localTime=(date)=>{try{return new Date(date).toLocaleString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZone:'America/New_York'})+' ET'}catch{return 'TBD'}};
 let state=null;
 document.querySelectorAll('.tab').forEach(btn=>btn.addEventListener('click',()=>{
   document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x===btn));
   document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x.id===btn.dataset.tab));
 }));
 $('gameFilter').addEventListener('change',()=>renderGames(state));
 function statusFor(model,preview){return preview?model?.preview_direction:model?.watch}
 function renderModel(label,model,preview){
   const side=statusFor(model,preview);
   return `<div class="model-view"><div class="num-label">${safe(label)}</div>
     <div class="model-value">${fmt(model?.total)}</div>
     <div class="model-mini"><span>EDGE ${model?.edge!=null?(model.edge>0?'+':'')+fmt(model.edge,2):'—'}</span><span class="${side?'good':'muted'}">${safe(side?(preview?'PREVIEW ':'WATCH ')+side:'NO SIGNAL')}</span></div></div>`;
 }
 function renderGames(d){const target=$('gameList');if(!d)return;
  let games=d.games||[];
  const filter=$('gameFilter').value;
  if(filter==='watch')games=games.filter(g=>g.prediction&&(statusFor(g.prediction,g.prediction.preview)||statusFor(g.prediction.original,g.prediction.preview)));
  if(filter==='pending')games=games.filter(g=>!g.prediction);
  if(!games.length){target.innerHTML='<div class="empty">'+(filter==='watch'?'No model signals currently meet the 5.5-point threshold.':filter==='pending'?'No games currently waiting for enough season data.':'No games have been imported yet. Once the first sync runs, today’s matchups will appear here.')+'</div>';return}
  target.innerHTML=games.map(g=>{
    const pred=g.prediction,market=g.market,preview=pred?.preview;
    const v1Side=statusFor(pred?.original,preview),v2Side=statusFor(pred,preview);
    const disagree=v1Side&&v2Side&&v1Side!==v2Side;
    const tag=!pred?'COLLECTING DATA':disagree?'MODELS DISAGREE':preview?'EXPERIMENTAL PREVIEW':(v1Side||v2Side)?'WATCH':'NO SIGNAL';
    return `<article class="game-card"><div class="game-top"><span>${safe(localTime(g.date))}</span><span class="pill ${!preview&&Boolean(v1Side||v2Side)?'watch':''}">${safe(tag)}</span></div>
      <div class="matchup">${safe(g.away)} <span class="vs">@</span> ${safe(g.home)}</div>
      <div class="market-strip"><span class="num-label">BOOK TOTAL</span><strong>${fmt(market?.line)}</strong></div>
      <div class="model-comparison">${renderModel('V1 · ORIGINAL EXCEL',pred?.original,preview)}${renderModel('V2 · ADJUSTED',pred,preview)}</div>
      <div class="card-bottom">${pred?(preview?`Early-season preview — ${pred.away_games} away / ${pred.home_games} home qualifying games; no official picks logged`:'Each model records its own qualifying paper signals'):'Predictions unavailable: both teams need at least one qualifying game.'}${market?` · ${safe(market.book)} · ${market.offers} books`:' · No sportsbook total available'}</div></article>`}).join('');
 }
 function render(d){state=d;
  $('updated').textContent=d.generated_at?'SYNCED '+localTime(d.generated_at):'AWAITING FIRST SYNC';
  $('gamesArchived').textContent=d.source_status?.games_archived??'—';$('teamsReady').textContent=d.source_status?.teams_with_stats??'—';
  const perf=d.performance_by_model?.v2||d.performance||{};$('record').textContent=`${perf.wins||0}–${perf.losses||0}`;
  $('units').textContent=(Number(perf.units)>0?'+':'')+fmt(perf.units||0,2)+'u';renderGames(d);
  if($('v1Record')){const p=d.performance_by_model?.v1||{};$('v1Record').textContent=`${p.wins||0}–${p.losses||0}`;$('v1Units').textContent=(Number(p.units)>0?'+':'')+fmt(p.units||0,2)+'u';}
  $('teamRows').innerHTML=(d.teams||[]).map(t=>`<tr><td>${safe(t.team)}</td><td>${t.games}</td><td>${fmt(t.pace)}</td><td>${fmt(t.ortg)}</td><td>${fmt(t.drtg)}</td><td class="${t.ready?'good':'muted'}">${t.ready?'10+ GAMES':t.games>=1?'PREVIEW':'COLLECTING'}</td></tr>`).join('')||'<tr><td colspan="6" class="muted">Waiting for the first completed games with valid boxscore data.</td></tr>';
  $('paperRows').innerHTML=(d.paper_bets||[]).map(p=>`<tr><td>${safe((p.model||'v2').toUpperCase())}</td><td>${safe(p.away)} @ ${safe(p.home)}</td><td class="${p.side==='OVER'?'good':''}">${safe(p.side)}</td><td>${fmt(p.line)}</td><td>${p.price>0?'+':''}${p.price}</td><td>${safe((p.result||'pending').toUpperCase())}</td><td>${p.units==null?'—':(p.units>0?'+':'')+fmt(p.units,2)+'u'}</td></tr>`).join('')||'<tr><td colspan="7" class="muted">No paper picks yet. Both models wait for 10 qualifying games per team.</td></tr>';
 }
 fetch('./data/dashboard.json',{cache:'no-store'}).then(resp=>{if(!resp.ok)throw new Error('No dashboard data');return resp.json()}).then(render).catch(err=>{$('gameList').innerHTML=`<div class="empty">Unable to load data: ${safe(err.message)}. Make sure the site is served by a web server (or GitHub Pages), not file://.</div>`});
})();
