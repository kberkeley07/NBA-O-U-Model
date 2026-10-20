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
 function renderGames(d){const target=$('gameList');if(!d)return;
  let games=d.games||[];
  const filter=$('gameFilter').value;
  if(filter==='watch')games=games.filter(g=>g.prediction?.watch||g.prediction?.preview_direction);
  if(filter==='pending')games=games.filter(g=>!g.prediction);
  if(!games.length){target.innerHTML='<div class="empty">'+(filter==='watch'?'No watch candidates currently meet the model threshold.':filter==='pending'?'No games currently waiting for enough season data.':'No games have been imported yet. Once the first sync runs, today’s matchups will appear here.')+'</div>';return}
  target.innerHTML=games.map(g=>{const pred=g.prediction, market=g.market,watch=pred?.watch,preview=pred?.preview;
    return `<article class="game-card"><div class="game-top"><span>${safe(localTime(g.date))}</span><span class="pill ${watch?'watch':''}">${safe(preview?(pred?.preview_direction?'PREVIEW '+pred.preview_direction:'PREVIEW ONLY'):watch?'WATCH '+watch:pred?'NO SIGNAL':'COLLECTING DATA')}</span></div>
      <div class="matchup">${safe(g.away)} <span class="vs">@</span> ${safe(g.home)}</div>
      <div class="grid-numbers"><div><div class="num-label">BOOK TOTAL</div><div class="num-value">${fmt(market?.line)}</div></div><div><div class="num-label">MODEL TOTAL</div><div class="num-value">${fmt(pred?.total)}</div></div><div><div class="num-label">EDGE</div><div class="num-value ${watch?'edge':''}">${pred?.edge!=null?(pred.edge>0?'+':'')+fmt(pred.edge):'—'}</div></div></div>
      <div class="card-bottom">${pred?(preview?`Early-season preview — ${pred.away_games} away / ${pred.home_games} home games; not tracked as a pick`:'Experimental 10+ game baseline'):'Preview unavailable: need 1 qualifying game from both teams'}${market?` · ${safe(market.book)} · ${market.offers} books`:' · No sportsbook total available'}</div></article>`}).join('');
 }
 function render(d){state=d;
  $('updated').textContent=d.generated_at?'SYNCED '+localTime(d.generated_at):'AWAITING FIRST SYNC';
  $('gamesArchived').textContent=d.source_status?.games_archived??'—';$('teamsReady').textContent=d.source_status?.teams_with_stats??'—';
  const perf=d.performance||{};$('record').textContent=`${perf.wins||0}–${perf.losses||0}`;
  $('units').textContent=(Number(perf.units)>0?'+':'')+fmt(perf.units||0,2)+'u';renderGames(d);
  $('teamRows').innerHTML=(d.teams||[]).map(t=>`<tr><td>${safe(t.team)}</td><td>${t.games}</td><td>${fmt(t.pace)}</td><td>${fmt(t.ortg)}</td><td>${fmt(t.drtg)}</td><td class="${t.ready?'good':'muted'}">${t.ready?'10+ GAMES':t.games>=1?'PREVIEW':'COLLECTING'}</td></tr>`).join('')||'<tr><td colspan="6" class="muted">Waiting for the first completed games with valid boxscore data.</td></tr>';
  $('paperRows').innerHTML=(d.paper_bets||[]).map(p=>`<tr><td>${safe(p.away)} @ ${safe(p.home)}</td><td class="${p.side==='OVER'?'good':''}">${safe(p.side)}</td><td>${fmt(p.line)}</td><td>${p.price>0?'+':''}${p.price}</td><td>${safe((p.result||'pending').toUpperCase())}</td><td>${p.units==null?'—':(p.units>0?'+':'')+fmt(p.units,2)+'u'}</td></tr>`).join('')||'<tr><td colspan="6" class="muted">No paper picks yet. The model intentionally waits for current-season sample size.</td></tr>';
 }
 fetch('./data/dashboard.json',{cache:'no-store'}).then(resp=>{if(!resp.ok)throw new Error('No dashboard data');return resp.json()}).then(render).catch(err=>{$('gameList').innerHTML=`<div class="empty">Unable to load data: ${safe(err.message)}. Make sure the site is served by a web server (or GitHub Pages), not file://.</div>`});
})();
