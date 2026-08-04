const stages=['CREATED','RISK APPROVED','SUBMITTED','PARTIAL FILL','FILLED','EXIT SIGNAL','CLOSED'];
const screens=[
  {name:'Market Structure Agent',symbol:'NIFTY 50',signal:'Bullish BOS',side:'BUY',confidence:78,entry:24560,sl:24518,target:24642,pnl:1260},
  {name:'Microstructure Agent',symbol:'BANKNIFTY',signal:'Bid imbalance',side:'WATCH',confidence:69,entry:51840,sl:51760,target:52010,pnl:740},
  {name:'F&O Intelligence Agent',symbol:'NIFTY OPT',signal:'Short covering',side:'BUY',confidence:73,entry:186.4,sl:171.2,target:214.8,pnl:2120},
  {name:'Mean Reversion Agent',symbol:'RELIANCE',signal:'VWAP reclaim',side:'BUY',confidence:66,entry:2978,sl:2958,target:3016,pnl:580},
  {name:'Momentum Agent',symbol:'HDFCBANK',signal:'Trend expansion',side:'BUY',confidence:71,entry:1768,sl:1752,target:1798,pnl:920},
  {name:'Risk & Cost Agent',symbol:'PORTFOLIO',signal:'Trade approved',side:'VETO READY',confidence:100,entry:0,sl:0,target:0,pnl:0},
  {name:'Execution Reconciler',symbol:'BROKER LINK',signal:'State matched',side:'SYNC',confidence:100,entry:0,sl:0,target:0,pnl:0}
];
const state={running:false,index:-1,lastMove:Date.now(),retry:0,orders:[],capital:1000000,cash:842500,pnl:4850,layout:0,delayedOnce:false,tick:0};
const $=id=>document.getElementById(id);
const layouts=[['layout-command','Command'],['layout-wall','Wall'],['layout-focus','Focus']];

function money(v){return new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(v)}
function now(){return new Date().toLocaleTimeString('en-IN',{hour12:false})}
function clamp(v,a,b){return Math.max(a,Math.min(b,v))}

function renderMetrics(){
  const rows=[['Virtual Capital',money(state.capital)],['Available Cash',money(state.cash)],['Today P&L',`${state.pnl>=0?'+':''}${money(state.pnl)}`],['Daily Drawdown','0.31%'],['Active Agents','7 / 7'],['Production Ready','20%']];
  $('metrics').innerHTML=rows.map(([a,b],i)=>`<article class="metric glass"><span>${a}</span><strong class="${i===2?'positive':''}">${b}</strong></article>`).join('');
}

function createSeries(base,seed,count=48){
  let p=base||100;const out=[];
  for(let i=0;i<count;i++){
    const wave=Math.sin((i+seed)*.38)*.0024;const drift=(seed%2?1:-.2)*.00045;
    const open=p;const close=open*(1+wave+drift+(Math.random()-.5)*.0022);
    const high=Math.max(open,close)*(1+Math.random()*.0018);const low=Math.min(open,close)*(1-Math.random()*.0018);
    out.push({open,high,low,close});p=close;
  }
  return out;
}

function drawChart(canvas,data,screen){
  const dpr=window.devicePixelRatio||1;const rect=canvas.getBoundingClientRect();
  if(!rect.width||!rect.height)return;canvas.width=rect.width*dpr;canvas.height=rect.height*dpr;
  const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);const w=rect.width,h=rect.height;ctx.clearRect(0,0,w,h);
  const values=data.flatMap(d=>[d.high,d.low]);const min=Math.min(...values),max=Math.max(...values);const span=max-min||1;
  ctx.strokeStyle='rgba(77,226,255,.08)';ctx.lineWidth=1;
  for(let i=1;i<5;i++){ctx.beginPath();ctx.moveTo(0,h*i/5);ctx.lineTo(w,h*i/5);ctx.stroke()}
  const step=w/data.length;const cw=Math.max(2,step*.56);
  data.forEach((d,i)=>{const x=i*step+step/2;const y=v=>h-((v-min)/span)*(h-22)-11;const up=d.close>=d.open;ctx.strokeStyle=up?'#37f7a4':'#ff5f78';ctx.fillStyle=ctx.strokeStyle;ctx.beginPath();ctx.moveTo(x,y(d.high));ctx.lineTo(x,y(d.low));ctx.stroke();ctx.fillRect(x-cw/2,Math.min(y(d.open),y(d.close)),cw,Math.max(1,Math.abs(y(d.open)-y(d.close))))});
  const last=data[data.length-1];ctx.strokeStyle='rgba(77,226,255,.7)';ctx.setLineDash([5,5]);const ly=h-((last.close-min)/span)*(h-22)-11;ctx.beginPath();ctx.moveTo(0,ly);ctx.lineTo(w,ly);ctx.stroke();ctx.setLineDash([]);
}

function renderScreens(){
  $('screenGrid').innerHTML=screens.map((s,i)=>`<article class="screen-card" data-screen="${i}">
    <header class="screen-head"><div class="screen-title"><span class="screen-index">0${i+1}</span><div><h3>${s.name}</h3><small>${s.symbol} · ${s.signal}</small></div></div><div class="screen-tools"><button class="focus-btn" data-focus="${i}">MAX</button></div></header>
    <div class="screen-body"><div class="chart-wrap"><canvas id="chart-${i}"></canvas><div class="chart-overlay"><span class="mini-tag">${s.side}</span><span class="mini-tag">CONF ${s.confidence}%</span><span class="mini-tag">LIVE</span></div></div>
    <aside class="trade-data"><div class="data-row"><span>ENTRY</span><strong>${s.entry?s.entry.toLocaleString('en-IN'):'CONTROL'}</strong></div><div class="data-row"><span>STOP</span><strong>${s.sl?s.sl.toLocaleString('en-IN'):'HARD VETO'}</strong></div><div class="data-row"><span>TARGET</span><strong>${s.target?s.target.toLocaleString('en-IN'):'SYNC'}</strong></div><div class="data-row"><span>PAPER P&L</span><strong class="positive">${s.pnl?'+'+money(s.pnl):'—'}</strong></div><div class="data-row"><span>STATUS</span><strong class="positive">ACTIVE</strong></div></aside></div>
  </article>`).join('');
  screens.forEach((s,i)=>{s.series=s.series||createSeries(s.entry||100+i*15,i+2);drawChart($(`chart-${i}`),s.series,s)});
  document.querySelectorAll('.focus-btn').forEach(btn=>btn.addEventListener('click',()=>toggleFocus(Number(btn.dataset.focus))));
}

function refreshCharts(){
  screens.forEach((s,i)=>{const a=s.series[s.series.length-1];const open=a.close;const close=open*(1+(Math.random()-.46)*.0024);s.series.push({open,close,high:Math.max(open,close)*(1+Math.random()*.0012),low:Math.min(open,close)*(1-Math.random()*.0012)});s.series.shift();drawChart($(`chart-${i}`),s.series,s)});
}

function toggleFocus(index){
  const cards=[...document.querySelectorAll('.screen-card')];const target=cards[index];const active=target.classList.contains('focused');cards.forEach(c=>c.classList.remove('focused'));if(!active)target.classList.add('focused');setTimeout(()=>screens.forEach((s,i)=>drawChart($(`chart-${i}`),s.series,s)),80);
}
function resetFocus(){document.querySelectorAll('.screen-card').forEach(c=>c.classList.remove('focused'));setTimeout(refreshCharts,60)}
function cycleLayout(){state.layout=(state.layout+1)%layouts.length;const [cls,label]=layouts[state.layout];$('screenGrid').className=`screen-grid ${cls}`;$('layoutLabel').textContent=`Layout: ${label}`;setTimeout(refreshCharts,80)}

function renderLifecycle(){
  $('lifecycle').innerHTML=stages.map((s,i)=>{const cls=i<state.index?'complete':i===state.index?'active':'';return `<div class="stage ${cls}"><strong>${s}</strong><small>${i<state.index?'✓ done':i===state.index?'processing':'waiting'}</small></div>`}).join('');
}
function renderAgents(){
  $('agents').innerHTML=screens.slice(0,6).map(a=>`<div class="agent"><h3>${a.name}</h3><p>Status: <strong>ACTIVE</strong></p><p>Signal: <strong>${a.signal}</strong></p><p>Confidence: <strong>${a.confidence}%</strong></p></div>`).join('');
}
function renderRisk(){
  const meters=[['Daily loss',10],['Gross exposure',22],['Sector concentration',18],['Correlation risk',24],['Margin usage',16]];
  $('riskMeters').innerHTML=meters.map(([n,v])=>`<div class="meter"><div class="meter-label"><span>${n}</span><strong>${v}%</strong></div><div class="meter-line"><div class="meter-fill" style="width:${v}%"></div></div></div>`).join('');
}
function addOrder(reason='Normal transition'){
  const stage=stages[Math.max(0,state.index)];const price=stage==='CLOSED'?'24,585.20':'24,560.00';const pnl=stage==='CLOSED'?'+₹1,260':'—';
  state.orders.unshift({time:now(),symbol:'NIFTY-PAPER',agent:'Market Structure',side:'BUY',qty:50,stage,price,pnl,reason});state.orders=state.orders.slice(0,12);
  $('ordersBody').innerHTML=state.orders.map(o=>`<tr><td>${o.time}</td><td>${o.symbol}</td><td>${o.agent}</td><td>${o.side}</td><td>${o.qty}</td><td>${o.stage}</td><td>${o.price}</td><td class="${o.pnl!=='—'?'positive':''}">${o.pnl}</td><td>${o.reason}</td></tr>`).join('');
}
function moveNext(reason='Normal transition'){
  state.lastMove=Date.now();state.retry=0;state.index++;$('lastTransition').textContent=now();$('watchdogState').textContent='HEALTHY';$('recoveryAction').textContent='None';addOrder(reason);renderLifecycle();
  if(state.index>=stages.length-1){state.running=false;state.pnl+=1260;state.cash+=1260;$('activeTradeTitle').textContent='NIFTY paper trade completed';$('startTradeBtn').disabled=false;renderMetrics()}
}
function startTrade(){if(state.running)return;state.running=true;state.index=-1;state.retry=0;state.lastMove=Date.now();state.delayedOnce=false;$('activeTradeTitle').textContent='NIFTY paper trade in progress';$('startTradeBtn').disabled=true;moveNext('Trade intent created')}
function engineTick(){
  $('clock').textContent=now();$('latencyValue').textContent=`${14+Math.floor(Math.random()*14)} ms`;if(!state.running)return;
  const elapsed=Date.now()-state.lastMove,normalDelay=2500,timeout=6200;
  if(elapsed>=timeout){state.retry++;$('watchdogState').textContent='RECOVERING';$('recoveryAction').textContent=`Retry ${state.retry}: reconcile and advance`;state.lastMove=Date.now();if(state.retry<=2)setTimeout(()=>moveNext('Watchdog reconciliation recovery'),650);else{$('watchdogState').textContent='BLOCKED SAFELY';$('recoveryAction').textContent='Operator review required';$('systemStatus').textContent='SYSTEM DEGRADED';$('systemStatus').className='badge warning';state.running=false;$('startTradeBtn').disabled=false}return}
  if(elapsed>=normalDelay){if(state.index===2&&!state.delayedOnce){state.delayedOnce=true;return}moveNext()}
}

$('startTradeBtn').addEventListener('click',startTrade);$('layoutBtn').addEventListener('click',cycleLayout);$('focusResetBtn').addEventListener('click',resetFocus);
window.addEventListener('resize',()=>setTimeout(refreshCharts,80));
renderMetrics();renderLifecycle();renderScreens();renderAgents();renderRisk();
setInterval(engineTick,500);setInterval(refreshCharts,1800);setTimeout(startTrade,900);
