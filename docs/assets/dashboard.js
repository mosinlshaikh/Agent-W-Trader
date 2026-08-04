const stages=['CREATED','RISK APPROVED','SUBMITTED','PARTIAL FILL','FILLED','EXIT SIGNAL','CLOSED'];
const state={running:false,index:-1,lastMove:Date.now(),retry:0,orders:[],capital:1000000,cash:842500,pnl:4850};
const $=id=>document.getElementById(id);

function money(v){return new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(v)}
function now(){return new Date().toLocaleTimeString('en-IN',{hour12:false})}

function renderMetrics(){
  const rows=[['Virtual Capital',money(state.capital)],['Available Cash',money(state.cash)],['Today P&L',`${state.pnl>=0?'+':''}${money(state.pnl)}`],['Daily Drawdown','0.31%'],['Open Positions',state.running?'1':'0'],['Production Ready','20%']];
  $('metrics').innerHTML=rows.map(([a,b])=>`<article class="metric"><span>${a}</span><strong>${b}</strong></article>`).join('');
}

function renderLifecycle(){
  $('lifecycle').innerHTML=stages.map((s,i)=>{
    const cls=i<state.index?'complete':i===state.index?'active':'';
    return `<div class="stage ${cls}"><strong>${s}</strong><small>${i<state.index?'✓ done':i===state.index?'processing':'waiting'}</small></div>`
  }).join('');
}

function renderAgents(){
  const agents=[
    ['Market Structure','Watching','Bullish bias','74%'],['Microstructure','Active','Bid imbalance','68%'],['F&O','Active','Short covering','71%'],['Cost Engine','Validated','Net edge positive','100%'],['Risk Agent','Active','Within limits','100%'],['Reconciler','Watching','Broker/local matched','100%']
  ];
  $('agents').innerHTML=agents.map(a=>`<div class="agent"><h3>${a[0]}</h3><p>Status: <strong>${a[1]}</strong></p><p>Signal: <strong>${a[2]}</strong></p><p>Confidence: <strong>${a[3]}</strong></p></div>`).join('');
}

function renderRisk(){
  const meters=[['Daily loss',10],['Gross exposure',22],['Sector concentration',18],['Correlation risk',24],['Margin usage',16]];
  $('riskMeters').innerHTML=meters.map(([n,v])=>`<div class="meter"><div class="meter-label"><span>${n}</span><strong>${v}%</strong></div><div class="meter-line"><div class="meter-fill" style="width:${v}%"></div></div></div>`).join('');
}

function addOrder(reason='Normal transition'){
  const stage=stages[Math.max(0,state.index)];
  const price=stage==='CLOSED'?'24,585.20':'24,560.00';
  const pnl=stage==='CLOSED'?'+₹1,260':'—';
  state.orders.unshift({time:now(),symbol:'NIFTY-PAPER',side:'BUY',qty:50,stage,price,pnl,reason});
  state.orders=state.orders.slice(0,10);
  $('ordersBody').innerHTML=state.orders.map(o=>`<tr><td>${o.time}</td><td>${o.symbol}</td><td>${o.side}</td><td>${o.qty}</td><td>${o.stage}</td><td>${o.price}</td><td>${o.pnl}</td><td>${o.reason}</td></tr>`).join('');
}

function moveNext(reason='Normal transition'){
  state.lastMove=Date.now();
  state.retry=0;
  state.index++;
  $('lastTransition').textContent=now();
  $('watchdogState').textContent='HEALTHY';
  $('recoveryAction').textContent='None';
  addOrder(reason);
  renderLifecycle();
  if(state.index>=stages.length-1){
    state.running=false;
    state.pnl+=1260;
    state.cash+=1260;
    $('activeTradeTitle').textContent='NIFTY paper trade completed';
    $('startTradeBtn').disabled=false;
    renderMetrics();
  }
}

function startTrade(){
  if(state.running)return;
  state.running=true;state.index=-1;state.retry=0;state.lastMove=Date.now();
  $('activeTradeTitle').textContent='NIFTY paper trade in progress';
  $('startTradeBtn').disabled=true;
  moveNext('Trade intent created');
}

function engineTick(){
  if(!state.running)return;
  const elapsed=Date.now()-state.lastMove;
  const normalDelay=2600;
  const timeout=6500;

  if(elapsed>=timeout){
    state.retry++;
    $('watchdogState').textContent='RECOVERING';
    $('recoveryAction').textContent=`Retry ${state.retry}: reconcile and advance`;
    state.lastMove=Date.now();
    if(state.retry<=2){
      setTimeout(()=>moveNext('Watchdog reconciliation recovery'),700);
    }else{
      $('watchdogState').textContent='BLOCKED SAFELY';
      $('recoveryAction').textContent='Order blocked; operator review required';
      $('systemStatus').textContent='SYSTEM DEGRADED';
      $('systemStatus').className='badge warning';
      state.running=false;
      $('startTradeBtn').disabled=false;
    }
    return;
  }

  if(elapsed>=normalDelay){
    // Deliberately delay one stage once to demonstrate watchdog visibility without freezing.
    if(state.index===2 && state.retry===0 && !state.delayedOnce){state.delayedOnce=true;return;}
    moveNext();
  }
}

$('startTradeBtn').addEventListener('click',startTrade);
renderMetrics();renderLifecycle();renderAgents();renderRisk();
setInterval(engineTick,500);
setTimeout(startTrade,900);
