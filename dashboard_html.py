# ============================================================================
#  DASHBOARD UI  v2  -  served by dashboard_backend.py
#  All 7 ideas applied + LLM2 extras (Apply button, fault colours)
# ============================================================================

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Marathon Refinery Optimization Advisor</title>
<style>
  :root{
    --navy:#1a3a5c;--teal:#2a9d8f;--orange:#e76f51;--red:#c0392b;
    --gold:#e6a817;--grey:#6c757d;--bg:#0f1720;--panel:#182430;
    --panel2:#1f2d3d;--line:#2c3e50;--text:#e8edf2;--dim:#9fb0c0;
    --ok:#2ecc71;--warn:#e67e22;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);font-size:13px;line-height:1.4}
  .topbar{display:flex;align-items:center;justify-content:space-between;background:var(--navy);padding:10px 18px;border-bottom:2px solid var(--orange)}
  .topbar h1{font-size:16px;font-weight:600}
  .topbar .sub{color:#bcd;font-size:11px;font-weight:400}
  .status-pills{display:flex;gap:10px;align-items:center}
  .pill{background:var(--panel2);padding:4px 12px;border-radius:12px;font-size:11px;border:1px solid var(--line)}
  .pill b{color:var(--gold)}
  .mode-sel{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:3px 8px;font-size:11px}
  .layout{display:grid;grid-template-columns:1fr 360px;gap:12px;padding:12px}
  .col-left{display:flex;flex-direction:column;gap:12px}
  .col-right{display:flex;flex-direction:column;gap:12px}
  .full-width{grid-column:1/-1}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
  .card h2{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--dim);margin-bottom:10px;border-bottom:1px solid var(--line);padding-bottom:6px}
  .hint{font-size:10px;color:var(--grey);margin-left:6px;font-weight:400;text-transform:none;letter-spacing:0}
  .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
  .kpi{background:var(--panel2);border-radius:8px;padding:10px;text-align:center;border:1px solid var(--line)}
  .kpi .icon{font-size:18px;margin-bottom:3px}
  .kpi .val{font-size:22px;font-weight:700}
  .kpi .lbl{font-size:10px;color:var(--dim);text-transform:uppercase}
  .kpi .sub{font-size:10px;color:var(--grey)}
  .kpi.good .val{color:var(--ok)}.kpi.warn .val{color:var(--warn)}.kpi.bad .val{color:var(--red)}
  .units{display:flex;align-items:flex-start;justify-content:space-between;gap:6px}
  .unit{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 6px;text-align:center;flex:1;min-width:80px;transition:.3s;display:flex;flex-direction:column;gap:2px}
  .unit.lead{border-color:var(--orange);box-shadow:0 0 0 1px var(--orange)}
  .unit.hot{border-color:var(--red);box-shadow:0 0 8px rgba(192,57,43,.6)}
  .unit.fault-active{border-color:var(--gold);box-shadow:0 0 8px rgba(230,168,23,.4)}
  .unit .u-icon{font-size:16px}.unit .n{font-size:10px;color:var(--dim)}
  .unit .nm{font-size:12px;font-weight:600}.unit .k{font-size:11px;color:var(--teal);font-weight:600}
  .unit .lim{font-size:9px;color:var(--grey);margin-top:1px}
  .arrow{color:var(--grey);font-size:18px;padding-top:22px;flex-shrink:0}
  .gauges{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:10px}
  .gauge{background:var(--panel2);border-radius:8px;padding:8px;border:1px solid var(--line)}
  .gauge .g-lbl{font-size:10px;color:var(--dim)}
  .gauge .bar{height:7px;background:#0d1620;border-radius:4px;margin-top:5px;overflow:hidden}
  .gauge .fill{height:100%;background:var(--teal);width:0;transition:.4s}
  .gauge .fill.warn{background:var(--warn)}.gauge .fill.bad{background:var(--red)}
  .gauge .g-val{font-size:11px;margin-top:3px}
  .btn-row{display:flex;flex-wrap:wrap;gap:7px}
  button{cursor:pointer;font-family:inherit;font-size:11px;border:none;border-radius:6px;padding:7px 11px;background:var(--panel2);color:var(--text);border:1px solid var(--line);transition:.15s}
  button:hover{background:var(--line)}
  button.scen{background:var(--navy);border-color:var(--teal)}
  button.scenB{background:var(--navy);border-color:var(--orange)}
  button.fault{background:#2a2027;border-color:#5a3040}
  button.fault:hover{background:#3a2833}
  button.clear{background:#1e3a2a;border-color:#2a6a4a}
  button.primary{background:var(--teal);color:#04241f;font-weight:600;border:none}
  button.primary:hover{background:#33b8a8}
  button.apply-btn{background:var(--orange);color:#fff;font-weight:600;border:none}
  button.apply-btn:hover{background:#d05a3e}
  button:disabled{opacity:.5;cursor:not-allowed}
  .agents{display:flex;flex-direction:column;gap:10px}
  .agent{background:var(--panel2);border-radius:8px;padding:10px;border-left:3px solid var(--grey)}
  .agent.mon{border-left-color:#4a90d9}.agent.opt{border-left-color:var(--teal)}.agent.saf{border-left-color:var(--orange)}
  .agent .a-head{display:flex;justify-content:space-between;align-items:center}
  .agent .a-name{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
  .agent .a-func{font-size:9.5px;color:var(--dim);font-weight:400;text-transform:none;letter-spacing:0;margin-left:5px}
  .verdict{font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;display:inline-block}
  .verdict.APPROVE{background:#12351f;color:var(--ok)}.verdict.REJECT{background:#3a1414;color:#ff6b6b}.verdict.COUNTER{background:#3a2e12;color:var(--gold)}
  .agent .a-body{font-size:11px;color:var(--text);margin-top:5px}
  .agent .a-reason{font-size:10.5px;color:var(--dim);margin-top:5px;font-style:italic}
  .badge{display:inline-block;font-size:9px;padding:1px 6px;border-radius:8px;background:var(--line);color:var(--dim);margin-left:4px}
  .badge.deg{background:#3a2e12;color:var(--gold)}
  .loop-tag{font-size:10px;color:var(--grey);margin:6px 0 2px}
  .outcome{margin-top:8px;padding:8px;border-radius:6px;text-align:center;font-weight:600;font-size:12px}
  .outcome.APPROVED{background:#12351f;color:var(--ok)}.outcome.HOLD_NO_SAFE_IMPROVEMENT{background:#3a2e12;color:var(--gold)}
  .slider-row{display:flex;align-items:center;gap:8px;margin:6px 0}
  .slider-row label{font-size:10.5px;width:135px;color:var(--dim);flex-shrink:0}
  .slider-row input[type=range]{flex:1}
  .slider-row .sv{font-size:10.5px;width:48px;text-align:right;color:var(--teal)}
  .slider-row .lim-tag{font-size:9px;color:var(--grey);white-space:nowrap}
  .preview-panel{background:#0d1620;border:1px solid var(--line);border-radius:8px;padding:10px;margin-top:8px;display:none}
  .preview-panel.show{display:block}
  .preview-panel h3{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
  .preview-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
  .prev-item{background:var(--panel2);border-radius:6px;padding:6px 8px;font-size:10.5px}
  .prev-item .pi-label{color:var(--dim);font-size:9.5px}
  .prev-item .pi-vals{display:flex;align-items:center;gap:6px;margin-top:2px}
  .prev-item .before{color:var(--grey)}.prev-item .arrow-r{color:var(--dim)}
  .prev-item .after{font-weight:600}
  .after.up{color:var(--ok)}.after.down{color:#ff6b6b}.after.neutral{color:var(--text)}
  .breach-box{background:#3a1414;border-radius:6px;padding:7px;margin-top:7px;font-size:10.5px;color:#ff9999}
  .safe-box{background:#12351f;border-radius:6px;padding:7px;margin-top:7px;font-size:10.5px;color:var(--ok)}
  .chat-log{height:150px;overflow-y:auto;background:#0d1620;border-radius:6px;padding:8px;font-size:11px;display:flex;flex-direction:column;gap:6px}
  .msg{padding:6px 9px;border-radius:8px;max-width:92%}
  .msg.user{background:var(--navy);align-self:flex-end}.msg.bot{background:var(--panel2);align-self:flex-start;white-space:pre-wrap}
  .chat-in{display:flex;gap:6px;margin-top:8px}
  .chat-in input{flex:1;background:#0d1620;border:1px solid var(--line);color:var(--text);border-radius:6px;padding:7px;font-size:11px}
  .log{height:150px;overflow-y:auto;font-size:10.5px;display:flex;flex-direction:column;gap:3px}
  .log .e{padding:4px 6px;border-radius:4px;background:#0d1620;border-left:2px solid var(--line)}
  .log .e.fault{border-left-color:var(--red)}.log .e.scenario{border-left-color:var(--orange)}
  .log .e.manual_change{border-left-color:var(--gold)}.log .e.agent_cycle{border-left-color:var(--teal)}
  .log .e .t{color:var(--grey)}
  .glossary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
  .gl-item{background:var(--panel2);border-radius:6px;padding:7px 10px;font-size:11px;border-left:2px solid var(--teal)}
  .gl-item b{color:var(--teal)}.gl-item span{color:var(--dim)}
  .flash{animation:flash .6s}
  @keyframes flash{0%{background:rgba(230,168,23,.3)}100%{}}
</style>
</head>
<body>

<div class="topbar">
  <div><h1>🏭 Marathon Refinery Optimization Advisor <span class="sub">&nbsp;Gulf Coast · Multi-Agent Advisory System</span></h1></div>
  <div class="status-pills">
    <span class="pill">⏱ Tick <b id="tick">0</b></span>
    <span class="pill">⚠ Faults <b id="faultcount">0</b></span>
    <select class="mode-sel" id="modeSel">
      <option value="MOCK">🔲 MOCK (no API)</option>
      <option value="LIVE">🟢 LIVE (Groq)</option>
      <option value="REPLAY">▶ REPLAY</option>
    </select>
  </div>
</div>

<div class="layout">
<div class="col-left">

  <div class="card">
    <h2>📊 Live Key Performance Indicators</h2>
    <div class="kpis">
      <div class="kpi" id="kpi-margin"><div class="icon">💰</div><div class="val" id="v-margin">--</div><div class="lbl">Margin $/bbl</div><div class="sub" id="v-marginday">--</div></div>
      <div class="kpi" id="kpi-octane"><div class="icon">⭐</div><div class="val" id="v-octane">--</div><div class="lbl">Pool Octane (RON)</div><div class="sub">floor ≥ 87.0</div></div>
      <div class="kpi" id="kpi-coke"><div class="icon">🔥</div><div class="val" id="v-coke">--</div><div class="lbl">FCC Coke %</div><div class="sub">limit ≤ 6.0%</div></div>
      <div class="kpi" id="kpi-h2"><div class="icon">⚗️</div><div class="val" id="v-h2">--</div><div class="lbl">H₂ Margin (MMscfd)</div><div class="sub" id="v-h2sub">--</div></div>
    </div>
  </div>

  <div class="card">
    <h2>🏗️ Live Plant — Process Units <span class="hint">updates every 3s · 🟠=lead · 🔴=near limit · 🟡=fault active</span></h2>
    <div class="units" id="units"></div>
    <div class="gauges" id="gauges"></div>
  </div>

  <div class="card">
    <h2>⚡ Scenario &amp; Fault Injection <span class="hint">agents respond automatically</span></h2>
    <div class="btn-row">
      <button class="scen" onclick="scenario('A')">📈 Scenario A: Gasoline Opportunity</button>
      <button class="scenB" onclick="scenario('B')">❄️ Scenario B: Diesel Cold-Snap</button>
      <button class="clear" onclick="clearFaults()">🔄 Clear / Reset</button>
    </div>
    <div class="btn-row" style="margin-top:8px" id="faultBtns"></div>
  </div>

  <div class="card">
    <h2>🤖 Advisory Pipeline
      <button class="primary" style="float:right;margin-top:-4px" onclick="advise()" id="adviseBtn">▶ Run Advisory Cycle</button>
    </h2>
    <div class="agents">
      <div class="agent mon"><div class="a-head"><span class="a-name">🛡 Sentinel <span class="a-func">(Monitoring Agent)</span></span></div><div class="a-body" id="mon-body">Press "Run Advisory Cycle" to diagnose.</div></div>
      <div class="agent opt"><div class="a-head"><span class="a-name">🧠 Strategist <span class="a-func">(Optimization Agent)</span></span></div><div class="a-body" id="opt-body">—</div></div>
      <div class="agent saf"><div class="a-head"><span class="a-name">🔒 Guardian <span class="a-func">(Safety &amp; Compliance Agent)</span></span></div><div class="a-body" id="saf-body">—</div></div>
    </div>
    <div id="outcome"></div>
    <div id="applyBtn" style="display:none;margin-top:8px">
      <button class="apply-btn" style="width:100%" onclick="applyRec()">✅ Apply Recommendation to Live Plant</button>
    </div>
  </div>

</div>

<div class="col-right">

  <div class="card">
    <h2>💬 Advisor — Operator Assistant <span class="hint">preview only</span></h2>
    <div class="chat-log" id="chatlog">
      <div class="msg bot">Ask me anything — e.g. "What happens if I raise hydrocracker conversion to 0.9?" or "How does the Reformer affect the Hydrocracker?"</div>
    </div>
    <div class="chat-in">
      <input id="chatInput" placeholder="Ask a what-if or how-it-works question..." onkeydown="if(event.key==='Enter')ask()">
      <button class="primary" onclick="ask()">Ask</button>
    </div>
  </div>

  <div class="card">
    <h2>🎛️ Manual Control <span class="hint">preview impact first → Safety check → Apply</span></h2>
    <div id="sliders"></div>
    <div style="display:flex;gap:8px;margin-top:8px">
      <button class="primary" style="flex:1" onclick="previewManual()">🔍 Preview Impact</button>
      <button class="apply-btn" style="flex:1" id="applyManualBtn" onclick="applyManual()" disabled>✅ Apply</button>
    </div>
    <div class="preview-panel" id="previewPanel">
      <h3>📋 Predicted Impact</h3>
      <div class="preview-grid" id="previewGrid"></div>
      <div id="previewSafety"></div>
    </div>
  </div>

  <div class="card">
    <h2>📋 Event Log <span class="hint">live audit trail</span></h2>
    <div class="log" id="log"></div>
  </div>

</div>

<div class="card full-width" style="margin:0 0 12px">
  <h2>📖 Glossary — Key Terms on This Dashboard</h2>
  <div class="glossary-grid" id="glossary"></div>
</div>

</div>

<script>
const $ = id => document.getElementById(id);
let CFG=null, LAST=null, busy=false, lastCard=null;

const UNIT_DEFS=[
  {key:'cdu', n:'1',icon:'🛢️',nm:'CDU',        knob:'cdu_furnace_temp_C',     suf:'°C', limKey:'cdu_furnace_temp_max_C'},
  {key:'vdu', n:'2',icon:'💨',nm:'VDU',        knob:'vdu_severity',           suf:'',   limKey:'vdu_severity_max'},
  {key:'fcc', n:'3',icon:'🔥',nm:'FCC',        knob:'fcc_severity',           suf:'',   limKey:'fcc_coke_make_max_pct',limLabel:'coke≤'},
  {key:'ref', n:'4',icon:'⚗️',nm:'Reformer',   knob:'reformer_severity',      suf:'',   limKey:'reformer_severity_max'},
  {key:'hc',  n:'5',icon:'⭐',nm:'Hydrocracker',knob:'hydrocracker_conversion',suf:'',  limKey:'hydrocracker_conversion_max',lead:true},
  {key:'blend',n:'6',icon:'🧪',nm:'Blending',  knob:null,                     suf:'',   limKey:null},
];

const SLIDER_KNOBS=[
  {k:'cdu_furnace_temp_C',       label:'🌡️ CDU Furnace (°C)'},
  {k:'fcc_severity',             label:'🔥 FCC Severity'},
  {k:'reformer_severity',        label:'⚗️ Reformer Severity'},
  {k:'hydrocracker_conversion',  label:'⭐ HC Conversion (lead)'},
];

const GLOSSARY=[
  ['CDU','Crude Distillation Unit — separates crude by boiling point'],
  ['VDU','Vacuum Distillation Unit — recovers extra gas oil from residue'],
  ['FCC','Fluid Catalytic Cracker — converts gas oil to gasoline with a catalyst'],
  ['Reformer','Converts naphtha to high-octane gasoline AND produces H₂'],
  ['Hydrocracker','Lead unit — cracks gas oil; conversion knob controls gasoline vs diesel split'],
  ['Blending Pool','Where all gasoline streams mix; must meet octane + sulfur specs'],
  ['Crack Spread','Product price minus crude cost — the refinery margin driver'],
  ['Octane (RON)','Gasoline quality; must stay ≥ 87 RON (US regular spec)'],
  ['ULSD','Ultra-Low Sulfur Diesel — sulfur ≤ 15 ppm (0.0015 wt%)'],
  ['BOV','Blending Octane Value — non-linear octane blending index per stream'],
  ['H₂ Balance','Reformer makes H₂; Hydrocracker consumes it — demand cannot exceed supply'],
  ['Conversion','HC setting 0.60–0.98: high → more gasoline; low → more diesel'],
  ['Severity','How hard a unit runs; higher = better quality but more energy/coke'],
  ['VGO','Vacuum Gas Oil — finite feed pool shared between FCC and Hydrocracker'],
  ['Coke Make','FCC by-product; hard limit ≤ 6.0% — regenerator burn constraint'],
  ['Margin $/bbl','Gross profit per barrel processed (Marathon FY2025: $16.87/bbl real)'],
  ['Knob','A setpoint the operator or Strategist (Optimization Agent) can change'],
  ['Limit','Hard constraint enforced by Guardian (Safety Agent) — never crossed'],
];

async function api(path,method='GET',body=null){
  const opt={method,headers:{'Content-Type':'application/json'}};
  if(body) opt.body=JSON.stringify(body);
  return await (await fetch(path,opt)).json();
}

async function init(){
  CFG=await api('/api/config');

  // Build unit boxes
  const u=$('units'); u.innerHTML='';
  UNIT_DEFS.forEach((d,i)=>{
    const lim=d.limKey?CFG.limits[d.limKey]:null;
    const limLabel=d.limLabel||'≤';
    const limStr=lim!=null?`${limLabel}${(+lim).toFixed(lim<5?2:0)}`:'';
    const div=document.createElement('div');
    div.className='unit'+(d.lead?' lead':''); div.id='unit-'+d.key;
    div.innerHTML=`<div class="u-icon">${d.icon}</div><div class="n">${d.n}</div><div class="nm">${d.nm}</div><div class="k" id="uk-${d.key}">--</div><div class="lim">${limStr}</div>`;
    u.appendChild(div);
    if(i<UNIT_DEFS.length-1){const a=document.createElement('div');a.className='arrow';a.innerHTML='→';u.appendChild(a);}
  });

  // Build gauges
  const g=$('gauges'); g.innerHTML='';
  [['margin','💰 Margin $/bbl'],['octane','⭐ Octane vs floor'],['coke','🔥 Coke vs limit'],['h2','⚗️ H₂ supply/demand']].forEach(([k,lbl])=>{
    g.innerHTML+=`<div class="gauge"><div class="g-lbl">${lbl}</div><div class="bar"><div class="fill" id="gf-${k}"></div></div><div class="g-val" id="gv-${k}">--</div></div>`;
  });

  // Build fault buttons
  const fb=$('faultBtns');
  const nice={heavy_sour_crude:'🛢 Heavy/Sour Crude',h2_shortfall:'⚗️ H₂ Shortfall',fcc_coke_excursion:'🔥 FCC Coke Excursion',energy_cost_spike:'💸 Energy Cost Spike',octane_floor_risk:'⭐ Octane Floor Risk',cdu_throughput_constraint:'🔩 Throughput Constraint'};
  CFG.sandbox_faults.forEach(f=>{fb.innerHTML+=`<button class="fault" onclick="injectFault('${f}')">${nice[f]||f}</button>`;});

  // Build sliders
  const sl=$('sliders'); sl.innerHTML='';
  SLIDER_KNOBS.forEach(s=>{
    const spec=CFG.knobs[s.k];
    const stepv=(s.k.includes('severity')||s.k.includes('conversion'))?0.01:1;
    const dp=stepv<1?2:0;
    sl.innerHTML+=`<div class="slider-row"><label>${s.label}</label><input type="range" id="sl-${s.k}" min="${spec.min}" max="${spec.max}" step="${stepv}" value="${spec.baseline}" oninput="$('sv-${s.k}').textContent=(+this.value).toFixed(${dp});resetPreview()"><span class="sv" id="sv-${s.k}">${(+spec.baseline).toFixed(dp)}</span><span class="lim-tag">[${(+spec.min).toFixed(dp)}–${(+spec.max).toFixed(dp)}]</span></div>`;
  });

  // Build glossary
  const gl=$('glossary'); gl.innerHTML='';
  GLOSSARY.forEach(([term,def])=>{gl.innerHTML+=`<div class="gl-item"><b>${term}</b> — <span>${def}</span></div>`;});

  $('modeSel').onchange=async e=>{await api('/api/mode','POST',{mode:e.target.value});};
  await refresh();
  setInterval(tick,3000);
  refreshLog();
  setInterval(refreshLog,4000);
}

async function tick(){if(busy)return;render(await api('/api/tick'));}
async function refresh(){render(await api('/api/state'));}

function render(s){
  LAST=s; $('tick').textContent=s.tick; $('faultcount').textContent=s.active_faults.length; $('modeSel').value=s.mode;
  $('v-margin').textContent='$'+s.margin_usd_bbl.toFixed(2);
  $('v-marginday').textContent='$'+(s.margin_usd_day/1000).toFixed(0)+'k/day';
  setKpi('kpi-margin',s.margin_usd_bbl>=14?'good':s.margin_usd_bbl>=10?'warn':'bad');
  $('v-octane').textContent=s.pool_octane.toFixed(2);
  setKpi('kpi-octane',s.pool_octane>=s.octane_floor+1?'good':s.pool_octane>=s.octane_floor?'warn':'bad');
  $('v-coke').textContent=s.fcc_coke_pct.toFixed(2)+'%';
  setKpi('kpi-coke',s.fcc_coke_pct<=s.fcc_coke_limit-0.7?'good':s.fcc_coke_pct<=s.fcc_coke_limit?'warn':'bad');
  const h2m=s.h2_available-s.h2_demand;
  $('v-h2').textContent=h2m.toFixed(2); $('v-h2sub').textContent=s.h2_demand.toFixed(1)+'/'+s.h2_available.toFixed(1)+' MMscfd';
  setKpi('kpi-h2',h2m>3?'good':h2m>=0?'warn':'bad');

  // Live unit boxes (Idea 1)
  const hasFault=s.active_faults&&s.active_faults.length>0;
  UNIT_DEFS.forEach(d=>{
    const el=$('unit-'+d.key); if(!el) return;
    const kEl=el.querySelector('.k');
    if(d.knob&&s.knobs&&s.knobs[d.knob]!==undefined){
      const v=s.knobs[d.knob];
      kEl.innerHTML=d.knob.includes('temp')?v.toFixed(0)+' °C':v.toFixed(2);
    } else if(d.key==='blend'){
      kEl.innerHTML=s.pool_octane?s.pool_octane.toFixed(1)+' RON':'--';
    }
    el.classList.toggle('fault-active',hasFault);
  });
  if(CFG){
    $('unit-fcc').classList.toggle('hot',s.fcc_coke_pct>s.fcc_coke_limit-0.3);
    $('unit-cdu').classList.toggle('hot',s.furnace_temp>s.furnace_limit-3);
    $('unit-hc').classList.toggle('hot',(s.h2_available-s.h2_demand)<1);
  }
  gauge('margin',clamp(s.margin_usd_bbl/25*100),s.margin_usd_bbl>=10,s.margin_usd_bbl>=6,'$'+s.margin_usd_bbl.toFixed(2)+'/bbl');
  gauge('octane',clamp((s.pool_octane-85)/8*100),s.pool_octane>=s.octane_floor+0.5,s.pool_octane>=s.octane_floor,s.pool_octane.toFixed(2)+' RON');
  gauge('coke',clamp(s.fcc_coke_pct/s.fcc_coke_limit*100),true,s.fcc_coke_pct<=s.fcc_coke_limit,s.fcc_coke_pct.toFixed(2)+'/'+s.fcc_coke_limit+'%');
  gauge('h2',clamp(s.h2_available/Math.max(s.h2_demand,1)*50),h2m>=1,h2m>=0,s.h2_demand.toFixed(1)+'/'+s.h2_available.toFixed(1));
}

function setKpi(id,cls){$(id).className='kpi '+cls;}
function clamp(v){return Math.max(0,Math.min(100,v));}
function gauge(k,pct,isGood,isOk,txt){
  const f=$('gf-'+k); f.style.width=pct+'%';
  f.className='fill'+(!isOk?' bad':!isGood?' warn':'');
  $('gv-'+k).textContent=txt;
}

// Idea 2: auto-advise on fault/scenario
async function scenario(w){flash();render(await api('/api/scenario','POST',{which:w}));refreshLog();await advise();}
async function injectFault(f){flash();render(await api('/api/fault','POST',{fault:f}));refreshLog();await advise();}
async function clearFaults(){render(await api('/api/clear','POST',{}));refreshLog();$('outcome').innerHTML='';$('applyBtn').style.display='none';}
function flash(){$('units').classList.add('flash');setTimeout(()=>$('units').classList.remove('flash'),600);}

async function advise(){
  busy=true;$('adviseBtn').disabled=true;$('adviseBtn').textContent='⏳ Thinking...';
  $('mon-body').textContent='Diagnosing…';$('opt-body').textContent='—';$('saf-body').textContent='—';
  $('outcome').innerHTML='';$('applyBtn').style.display='none';
  try{
    const r=await api('/api/advise','POST',{});lastCard=r;
    const m=r.monitoring;
    const degM=m._degraded?`<span class="badge deg">degraded</span>`:'';
    $('mon-body').innerHTML=`<b>${(m.status||'?').toUpperCase()}</b>${degM}<br>${esc(m.headline||'')}${reason(m.reasoning)}`;
    let optHtml='',safHtml='';
    r.attempts.forEach(a=>{
      const tag=r.attempts.length>1?`<div class="loop-tag">Attempt ${a.loop}:</div>`:'';
      optHtml+=tag+`<div>${fmtChanges(a.proposed_changes)} → <b>${money(a.margin_delta)}/day</b>${reason(a.opt_reasoning)}</div>`;
      const vcls=a.verdict||'';
      safHtml+=tag+`<span class="verdict ${vcls}">${a.verdict||'?'}</span> `+(a.binding_limits.length?`binds: ${a.binding_limits.join(', ')}`:'all clear')+reason(a.safety_reasoning);
    });
    $('opt-body').innerHTML=optHtml||'—';$('saf-body').innerHTML=safHtml||'—';
    const oc=r.outcome;
    $('outcome').innerHTML=`<div class="outcome ${oc}">${oc==='APPROVED'?'✅ APPROVED — '+fmtChanges(r.final_changes):'⏸ HOLDING — no safe improvement found'} &nbsp;(${r.loops} loop${r.loops>1?'s':''})</div>`;
    if(oc==='APPROVED'&&Object.keys(r.final_changes||{}).length) $('applyBtn').style.display='block';
  }catch(e){$('mon-body').textContent='Error: '+e;}
  busy=false;$('adviseBtn').disabled=false;$('adviseBtn').innerHTML='▶ Run Advisory Cycle';
  refreshLog();
}

async function applyRec(){if(!lastCard)return;await api('/api/apply','POST',{});$('applyBtn').style.display='none';await refresh();refreshLog();}

// Idea 3: full impact preview
function resetPreview(){$('applyManualBtn').disabled=true;$('previewPanel').classList.remove('show');}
function getSliders(){const ch={};SLIDER_KNOBS.forEach(s=>{ch[s.k]=+$('sl-'+s.k).value;});return ch;}

async function previewManual(){
  $('previewPanel').classList.add('show');
  $('previewGrid').innerHTML='<div style="color:var(--dim);font-size:11px">Calculating…</div>';
  $('previewSafety').innerHTML='';
  try{
    const p=await api('/api/preview','POST',{changes:getSliders()});
    if(p.error){$('previewGrid').innerHTML=`<div style="color:#ff6b6b">${p.error}</div>`;return;}
    const rows=[
      ['💰 Margin $/bbl',  fmt2(p.margin_usd_bbl_before), fmt2(p.margin_usd_bbl_after),  p.margin_usd_bbl_after>p.margin_usd_bbl_before],
      ['⛽ Gasoline (bpd)', rnd(p.gasoline_pool_bpd_before),rnd(p.gasoline_pool_bpd_after), p.gasoline_pool_bpd_after>p.gasoline_pool_bpd_before],
      ['🚛 Diesel (bpd)',   rnd(p.diesel_pool_bpd_before), rnd(p.diesel_pool_bpd_after),  p.diesel_pool_bpd_after>p.diesel_pool_bpd_before],
      ['✈️ Jet (bpd)',      rnd(p.jet_bpd_before),         rnd(p.jet_bpd_after),          p.jet_bpd_after>p.jet_bpd_before],
      ['⭐ Pool Octane',    fmt2(p.pool_octane_before),     fmt2(p.pool_octane_after),     p.pool_octane_after>p.pool_octane_before],
      ['🔥 FCC Coke %',    fmt2(p.fcc_coke_before),        fmt2(p.fcc_coke_after),        p.fcc_coke_after<p.fcc_coke_before],
      ['⚗️ H₂ Demand MM',  p.h2_demand_before+'',         p.h2_demand_after+'',          p.h2_demand_after<p.h2_demand_before],
      ['💡 Energy kMMBtu', fmt1(p.energy_mmbtu_before),    fmt1(p.energy_mmbtu_after),    p.energy_mmbtu_after<p.energy_mmbtu_before],
      ['💧 Sulfur ppm',    p.diesel_sulfur_ppm_before+'',  p.diesel_sulfur_ppm_after+'', p.diesel_sulfur_ppm_after<p.diesel_sulfur_ppm_before],
    ];
    $('previewGrid').innerHTML=rows.map(([lbl,bef,aft,good])=>`<div class="prev-item"><div class="pi-label">${lbl}</div><div class="pi-vals"><span class="before">${bef}</span><span class="arrow-r">→</span><span class="after ${good===true?'up':good===false?'down':'neutral'}">${aft}</span></div></div>`).join('');
    if(p.all_safe){
      $('previewSafety').innerHTML=`<div class="safe-box">✅ All safety limits satisfied — change is safe to apply.</div>`;
      $('applyManualBtn').disabled=false;
    } else {
      const bl=p.breaches.map(b=>`${b.limit} (${b.value} vs ${b.bound})`).join('; ');
      $('previewSafety').innerHTML=`<div class="breach-box">🔒 Guardian will BLOCK: ${bl}</div>`;
      $('applyManualBtn').disabled=true;
    }
  }catch(e){$('previewGrid').innerHTML=`<div style="color:#ff6b6b">Error: ${e}</div>`;}
}

async function applyManual(){
  const r=await api('/api/manual','POST',{changes:getSliders()});
  $('previewSafety').innerHTML=r.applied
    ?`<div class="safe-box">✅ ${r.verdict} — applied. Margin ${money(r.margin_delta)}/day.</div>`
    :`<div class="breach-box">🔒 ${r.verdict} — BLOCKED. ${r.binding_limits.join(', ')}</div>`;
  $('applyManualBtn').disabled=true;
  await refresh();refreshLog();
}

async function ask(){
  const inp=$('chatInput');const q=inp.value.trim();if(!q)return;inp.value='';
  addMsg('user',q);addMsg('bot','⏳…');
  const log=$('chatlog');const t=log.lastChild;
  try{t.textContent=(await api('/api/assistant','POST',{question:q})).answer||'(no answer)';}
  catch(e){t.textContent='Error: '+e;}
  log.scrollTop=log.scrollHeight;
}
function addMsg(who,txt){const l=$('chatlog');const d=document.createElement('div');d.className='msg '+who;d.textContent=txt;l.appendChild(d);l.scrollTop=l.scrollHeight;}

async function refreshLog(){
  const r=await api('/api/log?n=14');
  const l=$('log');l.innerHTML='';
  r.events.slice().reverse().forEach(e=>{
    l.innerHTML+=`<div class="e ${e.event_type}"><span class="t">${e.tick!=null?'t'+e.tick:''} ${e.event_type}</span> — ${esc(e.details)}${e.binding_limits&&e.binding_limits.length?` <span style="color:#ff6b6b">[${e.binding_limits.join(',')}]</span>`:''}</div>`;
  });
}

function reason(r){if(!r)return '';const p=[];for(const k in r)if(r[k]&&k!=='_degraded')p.push(`<b>${k}:</b> ${esc(''+r[k])}`);return p.length?`<div class="a-reason">${p.join(' · ')}</div>`:'`';}
function fmtChanges(c){if(!c||!Object.keys(c).length)return '(no change)';return Object.entries(c).map(([k,v])=>`${k.replace('_bpd','').replace('hydrocracker','HC').replace(/_/g,' ')}=${(+v).toFixed(k.includes('temp')||k.includes('bpd')?0:2)}`).join(', ');}
function money(v){if(v==null)return '?';return(v>=0?'+':'')+'$'+Math.round(v).toLocaleString();}
function esc(s){return(s||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function fmt2(v){return(+v).toFixed(2);}function fmt1(v){return(+v).toFixed(1);}function rnd(v){return Math.round(+v).toLocaleString();}

init();
</script>
</body>
</html>
"""
