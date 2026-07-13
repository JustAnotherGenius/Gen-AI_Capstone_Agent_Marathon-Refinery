# ============================================================================
#  DASHBOARD UI  v3  -  served by dashboard_backend.py
#  Tier 1 + Tier 2 features added on top of v2:
#   Tier 1: advisory-mode language, system tagline, DCS dispatch toast,
#           About/metadata panel, methodology footnote, alarm banner,
#           export snapshot button
#   Tier 2: trend charts (sparklines), risk score gauge, fault impact
#           summary banner, text-file upload for the Assistant, 2x2 agent
#           grid, horizontal pipeline stepper, market scenario dropdown,
#           expandable/filterable event log, status-pill styling
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
  .topbar{display:flex;align-items:center;justify-content:space-between;background:var(--navy);padding:8px 18px;border-bottom:2px solid var(--orange)}
  .topbar h1{font-size:16px;font-weight:600}
  .topbar .sub{color:#bcd;font-size:11px;font-weight:400}
  .tagline-bar{background:#132537;padding:5px 18px;font-size:11px;color:var(--teal);border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center}
  .adv-badge{background:#12351f;color:var(--ok);border:1px solid #1f5c34;border-radius:10px;padding:2px 10px;font-size:10px;font-weight:700;letter-spacing:.3px}
  .status-pills{display:flex;gap:10px;align-items:center}
  .pill{background:var(--panel2);padding:4px 12px;border-radius:12px;font-size:11px;border:1px solid var(--line)}
  .pill b{color:var(--gold)}
  .mode-sel{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:3px 8px;font-size:11px}
  .icon-btn{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:4px 9px;font-size:11px;cursor:pointer}
  .icon-btn:hover{background:var(--line)}

  /* ALARM BANNER (Tier 1 #2) */
  .alarm-banner{display:none;background:#3a1414;border-bottom:2px solid var(--red);color:#ff9999;
    padding:8px 18px;font-size:12px;font-weight:600;align-items:center;gap:10px}
  .alarm-banner.show{display:flex}
  .alarm-banner .pulse{width:9px;height:9px;border-radius:50%;background:#ff4444;animation:pulse 1.1s infinite}
  @keyframes pulse{0%{opacity:1}50%{opacity:.3}100%{opacity:1}}
  .alarm-banner.resolved{background:#12351f;border-bottom-color:#1f5c34;color:var(--ok)}
  .alarm-banner.resolved .pulse{background:#2ecc71;animation:none}

  /* IMPACT SUMMARY TOAST (Tier 2 #11) */
  .impact-toast{display:none;background:#132537;border:1px solid var(--teal);border-left:4px solid var(--teal);
    padding:8px 14px;margin:0 12px;border-radius:0 6px 6px 0;font-size:11.5px;color:var(--text)}
  .impact-toast.show{display:block}
  .impact-toast.bad{border-color:var(--red);border-left-color:var(--red)}

  /* DCS DISPATCH TOAST (Tier 1 #5) */
  .dcs-toast{position:fixed;bottom:20px;right:20px;background:#12351f;border:1px solid var(--ok);
    color:var(--ok);padding:12px 18px;border-radius:8px;font-size:12px;font-weight:600;
    box-shadow:0 4px 16px rgba(0,0,0,.4);z-index:999;display:none;max-width:340px}
  .dcs-toast.show{display:block;animation:slidein .3s ease-out}
  @keyframes slidein{from{transform:translateX(30px);opacity:0}to{transform:translateX(0);opacity:1}}

  .layout{display:grid;grid-template-columns:1fr 360px;gap:12px;padding:12px}
  .col-left{display:flex;flex-direction:column;gap:12px}
  .col-right{display:flex;flex-direction:column;gap:12px}
  .full-width{grid-column:1/-1}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
  .card h2{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--dim);margin-bottom:10px;border-bottom:1px solid var(--line);padding-bottom:6px;display:flex;justify-content:space-between;align-items:center}
  .hint{font-size:10px;color:var(--grey);margin-left:6px;font-weight:400;text-transform:none;letter-spacing:0}

  /* KPI + RISK GAUGE */
  .kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
  .kpi{background:var(--panel2);border-radius:8px;padding:10px;text-align:center;border:1px solid var(--line)}
  .kpi .icon{font-size:18px;margin-bottom:3px}
  .kpi .val{font-size:22px;font-weight:700}
  .kpi .lbl{font-size:10px;color:var(--dim);text-transform:uppercase}
  .kpi .sub{font-size:10px;color:var(--grey)}
  .kpi.good .val{color:var(--ok)}.kpi.warn .val{color:var(--warn)}.kpi.bad .val{color:var(--red)}
  .risk-ring{width:52px;height:52px;margin:0 auto;position:relative}
  .risk-ring svg{transform:rotate(-90deg)}
  .risk-ring .rv{position:absolute;top:0;left:0;width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700}

  /* TREND CHARTS (Tier 2 #9) */
  .trends{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
  .trend-box{background:var(--panel2);border-radius:8px;padding:8px;border:1px solid var(--line)}
  .trend-box .tt{font-size:10px;color:var(--dim);display:flex;justify-content:space-between;margin-bottom:4px}
  .trend-box canvas{width:100%;height:44px;display:block}

  /* PLANT UNITS */
  .units{display:flex;align-items:flex-start;justify-content:space-between;gap:6px}
  .unit{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 6px;text-align:center;flex:1;min-width:80px;transition:.3s;display:flex;flex-direction:column;gap:2px}
  .unit.lead{border-color:var(--orange);box-shadow:0 0 0 1px var(--orange)}
  .unit.hot{border-color:var(--red);box-shadow:0 0 8px rgba(192,57,43,.6)}
  .unit.fault-active{border-color:var(--gold);box-shadow:0 0 8px rgba(230,168,23,.4)}
  .unit .u-icon{font-size:16px}.unit .n{font-size:10px;color:var(--dim)}
  .unit .nm{font-size:12px;font-weight:600}.unit .k{font-size:11px;color:var(--teal);font-weight:600}
  .unit .lim{font-size:9px;color:var(--grey);margin-top:1px}
  .unit .out{font-size:10px;color:var(--gold);margin-top:2px;padding-top:2px;border-top:1px dashed #2c3e50}
  .unit .out .ol{font-size:8px;color:var(--grey);display:block;text-transform:uppercase;letter-spacing:.3px}
  .arrow{color:var(--grey);font-size:18px;padding-top:22px;flex-shrink:0}

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
  button.preset-btn{background:#2a1f3a;border-color:#6a4a9e;color:#c9a8f5;font-size:10.5px}
  button.preset-btn:hover{background:#3a2a52}
  button:disabled{opacity:.5;cursor:not-allowed}
  .market-sel{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:6px 9px;font-size:11px;flex:1;min-width:200px}

  /* HORIZONTAL PIPELINE STEPPER (Tier 2 #14) */
  .stepper{display:flex;align-items:center;gap:4px;margin-bottom:12px}
  .step{flex:1;background:var(--panel2);border:1px solid var(--line);border-radius:7px;padding:8px 4px;text-align:center;font-size:10px;color:var(--dim);transition:.3s}
  .step .si{font-size:15px;display:block;margin-bottom:2px}
  .step.active{background:var(--teal);color:#04241f;border-color:var(--teal);font-weight:700}
  .step.active .si{filter:none}
  .step.done{background:#12351f;color:var(--ok);border-color:#1f5c34}
  .step-arrow{color:var(--grey);font-size:13px}

  /* 2x2 AGENT GRID (Tier 2 #13) */
  .agent-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  .agent{background:var(--panel2);border-radius:8px;padding:10px;border-left:3px solid var(--grey)}
  .agent.mon{border-left-color:#4a90d9}.agent.opt{border-left-color:var(--teal)}
  .agent.saf{border-left-color:var(--orange)}.agent.adv{border-left-color:#9b59b6}
  .agent .a-head{display:flex;justify-content:space-between;align-items:center}
  .agent .a-name{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
  .agent .a-func{font-size:9px;color:var(--dim);font-weight:400;text-transform:none;letter-spacing:0;display:block;margin-top:1px}
  .status-pill{font-size:9.5px;font-weight:700;padding:2px 8px;border-radius:10px;display:inline-block}
  .status-pill.APPROVE,.status-pill.OPTIMIZED,.status-pill.NOMINAL{background:#12351f;color:var(--ok)}
  .status-pill.REJECT,.status-pill.ALERT{background:#3a1414;color:#ff6b6b}
  .status-pill.COUNTER{background:#3a2e12;color:var(--gold)}
  .agent .a-body{font-size:10.5px;color:var(--text);margin-top:5px;min-height:28px}
  .agent .a-reason{font-size:9.5px;color:var(--dim);margin-top:5px;font-style:italic}
  .badge{display:inline-block;font-size:9px;padding:1px 6px;border-radius:8px;background:var(--line);color:var(--dim);margin-left:4px}
  .badge.deg{background:#3a2e12;color:var(--gold)}
  .loop-tag{font-size:10px;color:var(--grey);margin:4px 0 2px}
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

  .chat-log{height:140px;overflow-y:auto;background:#0d1620;border-radius:6px;padding:8px;font-size:11px;display:flex;flex-direction:column;gap:6px}
  .msg{padding:6px 9px;border-radius:8px;max-width:92%}
  .msg.user{background:var(--navy);align-self:flex-end}.msg.bot{background:var(--panel2);align-self:flex-start;white-space:pre-wrap}
  .chat-in{display:flex;gap:6px;margin-top:8px}
  .chat-in input{flex:1;background:#0d1620;border:1px solid var(--line);color:var(--text);border-radius:6px;padding:7px;font-size:11px}
  .upload-row{display:flex;align-items:center;gap:8px;margin-top:6px;font-size:10.5px;color:var(--dim)}
  .upload-row input[type=file]{font-size:10px;color:var(--dim);max-width:200px}
  .upload-row .fname{color:var(--teal);font-size:10px}

  /* EVENT LOG (Tier 2 #16) */
  .log-filters{display:flex;gap:5px;margin-bottom:6px;flex-wrap:wrap}
  .log-filter{font-size:9.5px;padding:3px 8px;border-radius:10px;background:var(--panel2);border:1px solid var(--line);color:var(--dim);cursor:pointer}
  .log-filter.active{background:var(--teal);color:#04241f;border-color:var(--teal);font-weight:700}
  .log{height:150px;overflow-y:auto;font-size:10.5px;display:flex;flex-direction:column;gap:3px}
  .log .e{padding:4px 6px;border-radius:4px;background:#0d1620;border-left:2px solid var(--line);cursor:default}
  .log .e.fault{border-left-color:var(--red)}.log .e.scenario{border-left-color:var(--orange)}
  .log .e.manual_change{border-left-color:var(--gold)}.log .e.agent_cycle{border-left-color:var(--teal)}
  .log .e.market{border-left-color:#9b59b6}.log .e.dispatch{border-left-color:var(--ok)}
  .log .e .t{color:var(--grey)}
  .log .e .expand{color:var(--teal);cursor:pointer;font-size:9.5px;margin-left:6px}
  .log .e .full{display:none;margin-top:5px;padding:6px;background:var(--panel2);border-radius:4px;font-size:9.5px;color:var(--dim);white-space:pre-wrap}
  .log .e .full.show{display:block}

  .glossary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
  .gl-item{background:var(--panel2);border-radius:6px;padding:7px 10px;font-size:11px;border-left:2px solid var(--teal)}
  .gl-item b{color:var(--teal)}.gl-item span{color:var(--dim)}

  /* ABOUT MODAL (Tier 1 #6) */
  .modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:998;align-items:center;justify-content:center}
  .modal-overlay.show{display:flex}
  .modal{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:22px;max-width:480px;width:90%}
  .modal h2{border:none;margin-bottom:12px;font-size:14px}
  .modal .team-row{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--line);font-size:11.5px}
  .modal .methodology{font-size:10.5px;color:var(--dim);margin-top:12px;line-height:1.5;padding-top:10px;border-top:1px solid var(--line)}
  .modal .close-btn{float:right;cursor:pointer;color:var(--dim);font-size:16px}

  .footer-methodology{font-size:9.5px;color:var(--grey);text-align:center;padding:8px 18px 14px}

  /* MODE DISCLAIMER BANNER (the user's 2nd request) */
  .mode-banner{padding:7px 18px;font-size:11.5px;font-weight:600;display:flex;
    align-items:center;justify-content:space-between;gap:10px;border-bottom:2px solid transparent}
  .mode-banner.mock{background:#3a2e12;color:var(--gold);border-bottom-color:var(--gold)}
  .mode-banner.live{background:#12351f;color:var(--ok);border-bottom-color:#1f5c34}
  .mode-banner.replay{background:#132537;color:#4a90d9;border-bottom-color:#2a4a70}
  .mode-banner .mb-left{display:flex;align-items:center;gap:8px}
  .mode-banner button{font-size:10.5px;padding:4px 12px;font-weight:700}
  .mode-banner.mock button{background:var(--gold);color:#3a2e12;border:none}
  .mode-banner.mock button:hover{background:#f0b830}

  /* KEY-CHOICE MODAL */
  .key-choice-card{background:var(--panel2);border:1.5px solid var(--line);border-radius:8px;
    padding:12px;margin-bottom:10px;cursor:pointer;transition:.15s}
  .key-choice-card:hover{border-color:var(--teal)}
  .key-choice-card.selected{border-color:var(--teal);background:#132a26}
  .key-choice-card .kc-title{font-size:12.5px;font-weight:700;color:var(--text);margin-bottom:3px}
  .key-choice-card .kc-sub{font-size:10.5px;color:var(--dim)}
  .key-input-row{display:none;margin-top:10px}
  .key-input-row.show{display:block}
  .key-input-row input{width:100%;background:#0d1620;border:1px solid var(--line);color:var(--text);
    border-radius:6px;padding:8px;font-size:11.5px;font-family:monospace}
  .key-input-row .key-note{font-size:9.5px;color:var(--grey);margin-top:5px}
  .key-modal-actions{display:flex;gap:8px;margin-top:14px}
  .key-status-note{font-size:10px;color:var(--dim);margin-top:10px;padding-top:10px;border-top:1px solid var(--line)}

  /* THINKING / ELAPSED TIME INDICATOR */
  .thinking-status{display:none;align-items:center;gap:8px;background:#132537;
    border:1px solid var(--teal);border-radius:7px;padding:8px 12px;margin-bottom:10px;
    font-size:11.5px;color:var(--teal)}
  .thinking-status.show{display:flex}
  .thinking-status .spinner{width:13px;height:13px;border:2px solid #2a4a45;
    border-top-color:var(--teal);border-radius:50%;animation:spin .7s linear infinite;flex-shrink:0}
  @keyframes spin{to{transform:rotate(360deg)}}
  .thinking-status .elapsed{margin-left:auto;font-family:monospace;font-weight:700;color:var(--gold)}

  /* AUTO-ADVISORY TOGGLE + LAST-CYCLE INFO (nice-to-have #1, #2) */
  .pipeline-status-row{display:flex;justify-content:space-between;align-items:center;
    margin-bottom:10px;font-size:11px;flex-wrap:wrap;gap:8px;background:var(--panel2);
    border:1px solid var(--line);border-radius:7px;padding:7px 10px}
  .auto-toggle{display:flex;align-items:center;gap:7px;cursor:pointer;user-select:none}
  .auto-toggle input{display:none}
  .toggle-slider{width:32px;height:18px;background:#2c3e50;border-radius:10px;
    position:relative;transition:.2s;flex-shrink:0}
  .toggle-slider::before{content:'';position:absolute;width:14px;height:14px;border-radius:50%;
    background:var(--dim);top:2px;left:2px;transition:.2s}
  .auto-toggle input:checked + .toggle-slider{background:var(--teal)}
  .auto-toggle input:checked + .toggle-slider::before{background:#04241f;transform:translateX(14px)}
  .toggle-label{color:var(--dim);font-size:11px}
  .toggle-label .auto-hint{color:var(--grey);font-size:9.5px}
  .last-cycle-info{color:var(--dim);font-size:10.5px;text-align:right}
  .last-cycle-info .outcome-tag{font-weight:700}
  .last-cycle-info .outcome-tag.APPROVED{color:var(--ok)}
  .last-cycle-info .outcome-tag.HOLD_NO_SAFE_IMPROVEMENT{color:var(--gold)}

  /* FAULT DURATION BADGE (nice-to-have #5) */
  button.fault{position:relative}
  .fault-duration{display:block;font-size:8.5px;color:var(--gold);margin-top:2px;font-weight:400}

  .flash{animation:flash .6s}
  @keyframes flash{0%{background:rgba(230,168,23,.3)}100%{}}
</style>
</head>
<body>

<div class="topbar">
  <div><h1>&#127981; Marathon Refinery Optimization Advisor <span class="sub">&nbsp;Gulf Coast &middot; Multi-Agent Advisory System</span></h1></div>
  <div class="status-pills">
    <span class="pill">&#9201; Tick <b id="tick">0</b></span>
    <span class="pill">&#9888; Faults <b id="faultcount">0</b></span>
    <button class="icon-btn" onclick="exportSnapshot()" title="Download snapshot">&#11015; Export</button>
    <button class="icon-btn" onclick="toggleAbout(true)" title="About this project">&#8505; About</button>
    <select class="mode-sel" id="modeSel">
      <option value="MOCK">&#128307; MOCK (no API)</option>
      <option value="LIVE">&#128994; LIVE (Groq)</option>
      <option value="REPLAY">&#9654; REPLAY</option>
    </select>
  </div>
</div>
<div class="tagline-bar">
  <span id="taglineText">Real-Time Multi-Agent Digital Twin for Site-Wide Margin Optimization</span>
  <span class="adv-badge">&#128737; ADVISORY MODE &mdash; OPERATOR REVIEW REQUIRED</span>
</div>
<div class="mode-banner mock" id="modeBanner">
  <span class="mb-left"><span id="modeBannerIcon">&#128993;</span> <span id="modeBannerText">MOCK MODE — responses are simulated demonstrations, not real AI reasoning.</span></span>
  <button onclick="toggleKeyModal(true)" id="modeBannerBtn">Switch to LIVE &rarr;</button>
</div>
<div class="alarm-banner" id="alarmBanner"><span class="pulse"></span><span id="alarmText"></span></div>
<div class="impact-toast" id="impactToast"></div>

<div class="modal-overlay" id="keyModal">
  <div class="modal">
    <span class="close-btn" onclick="toggleKeyModal(false)">&times;</span>
    <h2>&#128273; Power the AI Agents</h2>
    <div class="key-choice-card" id="kcDefault" onclick="selectKeyChoice(false)">
      <div class="kc-title">&#9989; Use project default key</div>
      <div class="kc-sub">Runs on the presenter's Groq key. Simplest option — just click and go.</div>
    </div>
    <div class="key-choice-card" id="kcOwn" onclick="selectKeyChoice(true)">
      <div class="kc-title">&#128273; Use your own Groq API key</div>
      <div class="kc-sub">Free at console.groq.com. Your key is used only for your session and is never shown to other visitors.</div>
    </div>
    <div class="key-input-row" id="keyInputRow">
      <input type="password" id="ownApiKey" placeholder="gsk_...">
      <div class="key-note">Stored only in this session, server-side. Never logged, never shown to anyone else, never included in exports.</div>
    </div>
    <div class="key-modal-actions">
      <button class="primary" style="flex:1" onclick="saveKeyChoice()">&#9654; Save &amp; Switch to LIVE</button>
    </div>
    <div class="key-status-note" id="keyStatusNote"></div>
  </div>
</div>

<div class="layout">
<div class="col-left">

  <div class="card">
    <h2>&#128202; Live Key Performance Indicators</h2>
    <div class="kpis">
      <div class="kpi" id="kpi-margin"><div class="icon">&#128176;</div><div class="val" id="v-margin">--</div><div class="lbl">Margin $/bbl</div><div class="sub" id="v-marginday">--</div></div>
      <div class="kpi" id="kpi-octane"><div class="icon">&#11088;</div><div class="val" id="v-octane">--</div><div class="lbl">Pool Octane (RON)</div><div class="sub">floor &ge; 87.0</div></div>
      <div class="kpi" id="kpi-coke"><div class="icon">&#128293;</div><div class="val" id="v-coke">--</div><div class="lbl">FCC Coke %</div><div class="sub">limit &le; 6.0%</div></div>
      <div class="kpi" id="kpi-h2"><div class="icon">&#9879;&#65039;</div><div class="val" id="v-h2">--</div><div class="lbl">H&#8322; Margin (MMscfd)</div><div class="sub" id="v-h2sub">--</div></div>
      <div class="kpi" id="kpi-risk">
        <div class="risk-ring">
          <svg width="52" height="52"><circle cx="26" cy="26" r="22" stroke="#2c3e50" stroke-width="5" fill="none"/>
            <circle id="riskArc" cx="26" cy="26" r="22" stroke="#2ecc71" stroke-width="5" fill="none" stroke-dasharray="138" stroke-dashoffset="138" stroke-linecap="round"/></svg>
          <div class="rv" id="v-risk">--</div>
        </div>
        <div class="lbl" style="margin-top:4px">Plant Health</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>&#128200; Trends <span class="hint">last ~40 ticks</span></h2>
    <div class="trends">
      <div class="trend-box"><div class="tt"><span>Margin $/bbl</span><span id="tr-margin-now">--</span></div><canvas id="tr-margin"></canvas></div>
      <div class="trend-box"><div class="tt"><span>Octane RON</span><span id="tr-octane-now">--</span></div><canvas id="tr-octane"></canvas></div>
      <div class="trend-box"><div class="tt"><span>FCC Coke %</span><span id="tr-coke-now">--</span></div><canvas id="tr-coke"></canvas></div>
      <div class="trend-box"><div class="tt"><span>H&#8322; Margin</span><span id="tr-h2-now">--</span></div><canvas id="tr-h2"></canvas></div>
    </div>
  </div>

  <div class="card">
    <h2>&#127959;&#65039; Live Plant &mdash; Process Units <span class="hint">updates every 3s</span></h2>
    <div class="units" id="units"></div>
  </div>

  <div class="card">
    <h2>&#9889; Scenario, Fault &amp; Market Injection <span class="hint">agents respond automatically</span></h2>
    <div class="btn-row">
      <button class="scen" onclick="scenario('A')">&#128200; Scenario A: Gasoline Opportunity</button>
      <button class="scenB" onclick="scenario('B')">&#10052;&#65039; Scenario B: Diesel Cold-Snap</button>
      <button class="clear" onclick="clearFaults()">&#128260; Clear / Reset</button>
    </div>
    <div class="btn-row" style="margin-top:8px" id="faultBtns"></div>
    <div class="btn-row" style="margin-top:8px">
      <select class="market-sel" id="marketSel"></select>
      <button class="primary" onclick="applyMarket()">Apply Market Environment</button>
    </div>
  </div>

  <div class="card">
    <h2>&#129302; Advisory Pipeline
      <button class="primary" onclick="advise()" id="adviseBtn">&#9654; Run Advisory Cycle</button>
    </h2>
    <div class="pipeline-status-row">
      <label class="auto-toggle">
        <input type="checkbox" id="autoAdvisoryToggle" onchange="toggleAutoAdvisory()">
        <span class="toggle-slider"></span>
        <span class="toggle-label">Auto-Advisory <span class="auto-hint" id="autoAdvisoryHint"></span></span>
      </label>
      <span class="last-cycle-info" id="lastCycleInfo">No cycles run yet</span>
    </div>
    <div class="thinking-status" id="thinkingStatus">
      <span class="spinner"></span>
      <span id="thinkingText">Agents are investigating the plant state…</span>
      <span class="elapsed" id="thinkingElapsed">0.0s</span>
    </div>
    <div class="stepper" id="stepper"></div>
    <div class="agent-grid">
      <div class="agent mon"><div class="a-head"><span class="a-name">&#128737; Sentinel<span class="a-func">Monitoring Agent</span></span></div>
        <div class="a-body" id="mon-body">Press "Run Advisory Cycle" to diagnose.</div></div>
      <div class="agent opt"><div class="a-head"><span class="a-name">&#129504; Strategist<span class="a-func">Optimization Agent</span></span></div>
        <div class="a-body" id="opt-body">&mdash;</div></div>
      <div class="agent saf"><div class="a-head"><span class="a-name">&#128274; Guardian<span class="a-func">Safety &amp; Compliance Agent</span></span></div>
        <div class="a-body" id="saf-body">&mdash;</div></div>
      <div class="agent adv"><div class="a-head"><span class="a-name">&#128172; Advisor<span class="a-func">Operator Assistant</span></span></div>
        <div class="a-body">Preview-only. Ask questions in the panel &rarr;</div></div>
    </div>
    <div id="outcome"></div>
    <div id="applyBtn" style="display:none;margin-top:8px">
      <button class="apply-btn" style="width:100%" onclick="applyRec()">&#9989; Approve &amp; Execute &mdash; Dispatch to DCS</button>
    </div>
  </div>

</div>

<div class="col-right">

  <div class="card">
    <h2>&#128172; Advisor &mdash; Operator Assistant <span class="hint">preview only</span></h2>
    <div class="chat-log" id="chatlog">
      <div class="msg bot">Ask me anything &mdash; e.g. "What happens if I raise hydrocracker conversion to 0.9?"</div>
    </div>
    <div class="chat-in">
      <input id="chatInput" placeholder="Ask a what-if or how-it-works question..." onkeydown="if(event.key==='Enter')ask()">
      <button class="primary" onclick="ask()">Ask</button>
    </div>
    <div class="upload-row">
      <label class="icon-btn" style="cursor:pointer">&#128206; Attach text file
        <input type="file" id="fileUpload" accept=".txt,.md,.csv" style="display:none" onchange="handleFileUpload(event)">
      </label>
      <span class="fname" id="fname"></span>
    </div>
  </div>

  <div class="card">
    <h2>&#127777;&#65039; Manual Control <span class="hint">preview impact first</span></h2>
    <div id="sliders"></div>
    <div style="display:flex;gap:8px;margin-top:8px">
      <button class="primary" style="flex:1" onclick="previewManual()">&#128269; Preview Impact</button>
      <button class="apply-btn" style="flex:1" id="applyManualBtn" onclick="applyManual()" disabled>&#9989; Apply</button>
    </div>
    <div class="preview-panel" id="previewPanel">
      <h3>&#128203; Predicted Impact</h3>
      <div class="preview-grid" id="previewGrid"></div>
      <div id="previewSafety"></div>
    </div>
    <div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--line)">
      <div class="hint" style="display:block;margin:0 0 6px;font-size:10px">&#129504; Smart presets — real grounded search, one-click auto-apply</div>
      <div class="btn-row">
        <button class="preset-btn" onclick="runPreset('max_profit')">&#128176; Max Profit/bbl</button>
        <button class="preset-btn" onclick="runPreset('max_octane')">&#11088; Max Octane</button>
        <button class="preset-btn" onclick="runPreset('max_health')">&#128737; Max Plant Health</button>
        <button class="preset-btn" onclick="runPreset('min_coke')">&#128293; Min Coke</button>
        <button class="preset-btn" onclick="runPreset('balanced')">&#9878;&#65039; Most Optimum</button>
      </div>
      <div id="presetNote" style="margin-top:8px"></div>
    </div>
  </div>

  <div class="card">
    <h2>&#128203; Event Log / DCS Operator Audit Log
      <button class="icon-btn" onclick="exportSnapshot()">&#11015;</button>
    </h2>
    <div class="log-filters" id="logFilters"></div>
    <div class="log" id="log"></div>
  </div>

</div>

<div class="card full-width" style="margin:0 0 4px">
  <h2>&#128214; Glossary &mdash; Key Terms on This Dashboard</h2>
  <div class="glossary-grid" id="glossary"></div>
</div>

</div>

<div class="footer-methodology" id="methodologyFooter"></div>
<div class="dcs-toast" id="dcsToast"></div>

<div class="modal-overlay" id="aboutModal">
  <div class="modal">
    <span class="close-btn" onclick="toggleAbout(false)">&times;</span>
    <h2 id="aboutTitle">About</h2>
    <div id="aboutTeam"></div>
    <div class="methodology" id="aboutMethodology"></div>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);
let CFG=null, LAST=null, busy=false, lastCard=null, uploadedText=null;
let logFilterActive = 'all';

const UNIT_DEFS=[
  {key:'cdu', n:'1',icon:'&#128721;&#65039;',nm:'CDU',        knob:'cdu_furnace_temp_C',     suf:'&deg;C', limKey:'cdu_furnace_temp_max_C', outLabel:'diesel yield'},
  {key:'vdu', n:'2',icon:'&#128168;',nm:'VDU',        knob:'vdu_severity',           suf:'',   limKey:'vdu_severity_max', outLabel:'VGO recovery'},
  {key:'fcc', n:'3',icon:'&#128293;',nm:'FCC',        knob:'fcc_severity',           suf:'',   limKey:'fcc_coke_make_max_pct',limLabel:'coke&le;', outLabel:'gasoline yield'},
  {key:'ref', n:'4',icon:'&#9879;&#65039;',nm:'Reformer',   knob:'reformer_severity',      suf:'',   limKey:'reformer_severity_max', outLabel:'reformate RON'},
  {key:'hc',  n:'5',icon:'&#11088;',nm:'Hydrocracker',knob:'hydrocracker_conversion',suf:'',  limKey:'hydrocracker_conversion_max',lead:true, outLabel:'gasoline split'},
  {key:'blend',n:'6',icon:'&#129514;',nm:'Blending',  knob:null,                     suf:'',   limKey:null, outLabel:'gasoline pool'},
];

const SLIDER_KNOBS=[
  {k:'cdu_furnace_temp_C',       label:'&#127777;&#65039; CDU Furnace (&deg;C)'},
  {k:'fcc_severity',             label:'&#128293; FCC Severity'},
  {k:'reformer_severity',        label:'&#9879;&#65039; Reformer Severity'},
  {k:'hydrocracker_conversion',  label:'&#11088; HC Conversion (lead)'},
];

const STEPPER_DEFS = [
  {icon:'&#9888;', label:'Event'}, {icon:'&#128737;', label:'Sentinel'},
  {icon:'&#129504;', label:'Strategist'}, {icon:'&#128274;', label:'Guardian'},
  {icon:'&#9989;', label:'Recommendation'},
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
  ['BOV','Blending Octane Value — non-linear octane blending index'],
  ['H₂ Balance','Reformer makes H₂; Hydrocracker consumes it — demand cannot exceed supply'],
  ['Conversion','HC setting 0.60–0.98: high → more gasoline; low → more diesel'],
  ['Severity','How hard a unit runs; higher = better quality but more energy/coke'],
  ['VGO','Vacuum Gas Oil — finite feed pool shared between FCC and Hydrocracker'],
  ['Coke Make','FCC by-product; hard limit ≤ 6.0% — regenerator burn constraint'],
  ['Margin $/bbl','Gross profit per barrel processed (Marathon FY2025: $16.87/bbl real)'],
  ['Plant Health Score','Composite 0-100 gauge: headroom across octane, coke, furnace temp, and H₂ balance'],
  ['DCS','Distributed Control System — the real plant control layer a recommendation dispatches to'],
  ['Knob','A setpoint the operator or Strategist (Optimization Agent) can change'],
  ['Limit','Hard constraint enforced by Guardian (Safety Agent) — never crossed'],
];

async function api(path,method='GET',body=null){
  const opt={method,headers:{'Content-Type':'application/json'}};
  if(body) opt.body=JSON.stringify(body);
  return await (await fetch(path,opt)).json();
}

function friendlyError(e){
  // "Failed to fetch" (a TypeError) means the request never got a response
  // at all -- the server didn't return an error, it was simply unreachable.
  const isNetworkErr = e instanceof TypeError;
  return isNetworkErr
    ? "Can't reach the server. If you're on a Render/public link, it may be waking up from sleep (~30s) — wait and try again. If running locally, check the server is still running."
    : ('Error: ' + e);
}

async function init(){
  CFG=await api('/api/config');

  $('taglineText').textContent = CFG.meta.tagline;
  $('aboutTitle').innerHTML = '&#8505; ' + CFG.meta.project_name;
  $('aboutTeam').innerHTML = `<div style="font-size:10.5px;color:var(--dim);margin-bottom:8px">${CFG.meta.program}</div>` +
    CFG.meta.team.map(t=>`<div class="team-row"><span>${t.name}</span><span style="color:var(--teal)">${t.roll}</span></div>`).join('');
  $('aboutMethodology').textContent = CFG.meta.methodology;
  $('methodologyFooter').textContent = CFG.meta.methodology;

  const u=$('units'); u.innerHTML='';
  UNIT_DEFS.forEach((d,i)=>{
    const lim=d.limKey?CFG.limits[d.limKey]:null;
    const limLabel=d.limLabel||'&le;';
    const limStr=lim!=null?`${limLabel}${(+lim).toFixed(lim<5?2:0)}`:'';
    const div=document.createElement('div');
    div.className='unit'+(d.lead?' lead':''); div.id='unit-'+d.key;
    div.innerHTML=`<div class="u-icon">${d.icon}</div><div class="n">${d.n}</div><div class="nm">${d.nm}</div><div class="k" id="uk-${d.key}">--</div><div class="lim">${limStr}</div><div class="out"><span class="ol">${d.outLabel}</span><span id="uo-${d.key}">--</span></div>`;
    u.appendChild(div);
    if(i<UNIT_DEFS.length-1){const a=document.createElement('div');a.className='arrow';a.innerHTML='&#8594;';u.appendChild(a);}
  });

  const fb=$('faultBtns');
  const nice={heavy_sour_crude:'&#128721; Heavy/Sour Crude',h2_shortfall:'&#9879;&#65039; H2 Shortfall',fcc_coke_excursion:'&#128293; FCC Coke Excursion',energy_cost_spike:'&#128184; Energy Cost Spike',octane_floor_risk:'&#11088; Octane Floor Risk',cdu_throughput_constraint:'&#128295; Throughput Constraint'};
  CFG.sandbox_faults.forEach(f=>{fb.innerHTML+=`<button class="fault" onclick="injectFault('${f}')">${nice[f]||f}<span class="fault-duration" id="fd-${f}"></span></button>`;});

  const msel=$('marketSel'); msel.innerHTML='';
  Object.entries(CFG.market_presets).forEach(([k,label])=>{msel.innerHTML+=`<option value="${k}">${label}</option>`;});

  const sl=$('sliders'); sl.innerHTML='';
  SLIDER_KNOBS.forEach(s=>{
    const spec=CFG.knobs[s.k];
    const stepv=(s.k.includes('severity')||s.k.includes('conversion'))?0.01:1;
    const dp=stepv<1?2:0;
    sl.innerHTML+=`<div class="slider-row"><label>${s.label}</label><input type="range" id="sl-${s.k}" min="${spec.min}" max="${spec.max}" step="${stepv}" value="${spec.baseline}" oninput="$('sv-${s.k}').textContent=(+this.value).toFixed(${dp});resetPreview()"><span class="sv" id="sv-${s.k}">${(+spec.baseline).toFixed(dp)}</span><span class="lim-tag">[${(+spec.min).toFixed(dp)}&ndash;${(+spec.max).toFixed(dp)}]</span></div>`;
  });

  const gl=$('glossary'); gl.innerHTML='';
  GLOSSARY.forEach(([term,def])=>{gl.innerHTML+=`<div class="gl-item"><b>${term}</b> — <span>${def}</span></div>`;});

  const lf=$('logFilters');
  ['all','fault','scenario','market','agent_cycle','manual_change','dispatch'].forEach(f=>{
    lf.innerHTML+=`<span class="log-filter${f==='all'?' active':''}" data-f="${f}" onclick="setLogFilter('${f}')">${f.replace('_',' ')}</span>`;
  });

  buildStepper('idle');
  $('modeSel').onchange=async e=>{
    const st = await api('/api/session/mode','POST',{mode:e.target.value});
    updateModeBanner(st);
    if(autoAdvisoryEnabled) refreshAutoAdvisoryHint(st.mode);
  };

  const initialStatus = await api('/api/session/status');
  updateModeBanner(initialStatus);

  await refresh();
  setInterval(tick,3000);
  refreshLog();
  refreshHistory();
  setInterval(refreshLog,4000);
  setInterval(refreshHistory,3200);
}

// ---- stepper ----
function buildStepper(mode){
  const st=$('stepper'); st.innerHTML='';
  STEPPER_DEFS.forEach((s,i)=>{
    let cls='step';
    if(mode==='thinking') cls+=' active';
    else if(mode==='done') cls+=' done';
    st.innerHTML+=`<div class="${cls}"><span class="si">${s.icon}</span>${s.label}</div>`;
    if(i<STEPPER_DEFS.length-1) st.innerHTML+='<span class="step-arrow">&#8594;</span>';
  });
}

// ---- tick & render ----
async function tick(){
  if(busy) return;
  render(await api('/api/tick'));
  if(autoAdvisoryEnabled){
    autoAdvisoryTickCounter++;
    if(autoAdvisoryTickCounter >= AUTO_ADVISORY_INTERVAL_TICKS && !busy){
      autoAdvisoryTickCounter = 0;
      advise();   // fire-and-forget; advise() manages its own busy/UI state
    }
  }
}
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

  // risk ring
  const risk = s.risk_score!=null?s.risk_score:0;
  $('v-risk').textContent = Math.round(risk);
  const circumference = 138;
  const offset = circumference - (risk/100)*circumference;
  const arc = $('riskArc');
  arc.setAttribute('stroke-dashoffset', offset);
  arc.setAttribute('stroke', risk>=65?'#2ecc71':risk>=40?'#e67e22':'#c0392b');

  // alarm banner (Tier 1 #2 + resolved-transition fix)
  updateAlarmBanner(s);

  const hasFault=s.active_faults&&s.active_faults.length>0;
  const uo = s.unit_outputs || {};
  const outFmt = {cdu:'%', vdu:'%', fcc:'%', ref:' RON', hc:'%', blend:' bpd'};
  UNIT_DEFS.forEach(d=>{
    const el=$('unit-'+d.key); if(!el) return;
    const kEl=el.querySelector('.k');
    if(d.knob&&s.knobs&&s.knobs[d.knob]!==undefined){
      const v=s.knobs[d.knob];
      kEl.innerHTML=d.knob.includes('temp')?v.toFixed(0)+' &deg;C':v.toFixed(2);
    } else if(d.key==='blend'){
      kEl.innerHTML=s.pool_octane?s.pool_octane.toFixed(1)+' RON':'--';
    }
    // live per-unit OUTPUT (not the setpoint) -- this is what actually
    // moves every tick, same as the KPI strip, per the user's original ask
    const oEl = $('uo-'+d.key);
    if(oEl && uo[d.key]!==undefined){
      const val = uo[d.key];
      oEl.textContent = (d.key==='blend' ? Math.round(val).toLocaleString() : val.toFixed(2)) + outFmt[d.key];
    }
    el.classList.toggle('fault-active',hasFault);
  });
  if(CFG){
    $('unit-fcc').classList.toggle('hot',s.fcc_coke_pct>s.fcc_coke_limit-0.3);
    $('unit-cdu').classList.toggle('hot',s.furnace_temp>s.furnace_limit-3);
    $('unit-hc').classList.toggle('hot',(s.h2_available-s.h2_demand)<1);
  }

  // nice-to-have #5: "active for Xs" duration badge on fault buttons.
  // Clear all badges first, then populate only the currently-active ones --
  // scenario faults (scenario_A/B) don't have a sandbox button, so they're
  // simply skipped here (no matching element, harmless no-op).
  document.querySelectorAll('.fault-duration').forEach(el=>el.textContent='');
  (s.fault_details || []).forEach(f=>{
    const el = document.getElementById('fd-'+f.name);
    if(!el) return;
    const secs = f.duration_seconds;
    el.textContent = 'active ' + (secs < 60 ? `${secs}s` : `${Math.floor(secs/60)}m ${Math.round(secs%60)}s`);
  });

  if(s.impact_summary) showImpactToast(s.impact_summary);
}

function setKpi(id,cls){$(id).className='kpi '+cls;}

// ---- Nice-to-have #1: Auto-Advisory toggle ----
let autoAdvisoryEnabled = false;
let autoAdvisoryTickCounter = 0;
const AUTO_ADVISORY_INTERVAL_TICKS = 5;   // ~15s at the 3s tick rate

function toggleAutoAdvisory(){
  autoAdvisoryEnabled = $('autoAdvisoryToggle').checked;
  autoAdvisoryTickCounter = 0;
  if(!autoAdvisoryEnabled){ $('autoAdvisoryHint').textContent=''; return; }
  refreshAutoAdvisoryHint($('modeSel').value);
}
function refreshAutoAdvisoryHint(mode){
  const intervalSecs = AUTO_ADVISORY_INTERVAL_TICKS * 3;
  $('autoAdvisoryHint').textContent = `(every ~${intervalSecs}s)` + (mode==='LIVE' ? ' — LIVE calls will run unattended' : '');
}

// ---- Nice-to-have #2: persistent last-cycle display ----
let lastAdvisoryTime = null;
let lastAdvisoryOutcome = null;

function updateLastCycleDisplay(){
  const el = $('lastCycleInfo');
  if(!lastAdvisoryTime){ el.textContent = 'No cycles run yet'; return; }
  const secs = Math.floor((Date.now() - lastAdvisoryTime) / 1000);
  const ago = secs < 5 ? 'just now' : secs < 60 ? `${secs}s ago` : `${Math.floor(secs/60)}m ago`;
  const label = lastAdvisoryOutcome === 'APPROVED' ? 'APPROVED'
    : lastAdvisoryOutcome === 'HOLD_NO_SAFE_IMPROVEMENT' ? 'HOLD — SME REVIEW' : lastAdvisoryOutcome;
  el.innerHTML = `Last cycle: ${ago} — <span class="outcome-tag ${lastAdvisoryOutcome}">${label}</span>`;
}
setInterval(updateLastCycleDisplay, 5000);   // keep the "Xs ago" text live even when idle

// ---- Alarm banner state machine: breach -> resolved-confirmation -> hidden.
// Also explains WHEN a breach persists because an active FAULT keeps
// re-forcing it every tick (faults are persistent-until-cleared by design;
// a one-time knob fix alone cannot silence one -- only Clear/Reset can).
let __wasBreaching = false;
let __resolvedTimer = null;

function updateAlarmBanner(s){
  const ab = $('alarmBanner');
  const breaching = s.breaches && s.breaches.length > 0;

  if(breaching){
    clearTimeout(__resolvedTimer);
    ab.className = 'alarm-banner show';
    const faultNote = (s.active_faults && s.active_faults.length)
      ? ' — an ACTIVE FAULT is re-forcing this every cycle; press Clear/Reset to fully resolve it.'
      : '';
    $('alarmText').textContent = 'ACTIVE LIMIT BREACH: '
      + s.breaches.map(b=>`${b.limit} (${b.value} vs ${b.bound})`).join('  |  ') + faultNote;
    __wasBreaching = true;
  } else if(__wasBreaching){
    // transition: it WAS breaching, now it's clear -- confirm, then hide
    ab.className = 'alarm-banner show resolved';
    $('alarmText').innerHTML = '&#9989; Breach resolved — all limits back within range.';
    __wasBreaching = false;
    clearTimeout(__resolvedTimer);
    __resolvedTimer = setTimeout(()=>{ ab.classList.remove('show'); }, 4000);
  } else {
    ab.classList.remove('show');
  }
}

function showImpactToast(imp){
  const t=$('impactToast');
  t.textContent = imp.text;
  t.className = 'impact-toast show' + (imp.delta<0 || (imp.breaches_now&&imp.breaches_now.length) ? ' bad':'');
  clearTimeout(window.__impactTimer);
  window.__impactTimer = setTimeout(()=>t.classList.remove('show'), 9000);
}

function showDcsToast(msg){
  const t=$('dcsToast');
  t.textContent = '&#9989; '.replace('&#9989;','✅ ') + msg;
  t.classList.add('show');
  clearTimeout(window.__dcsTimer);
  window.__dcsTimer = setTimeout(()=>t.classList.remove('show'), 6000);
}

// ---- trend charts (Tier 2 #9) ----
async function refreshHistory(){
  const d = await api('/api/history');
  const pts = d.points || [];
  if(!pts.length) return;
  drawSparkline('tr-margin', pts.map(p=>p.margin), '#2a9d8f');
  drawSparkline('tr-octane', pts.map(p=>p.octane), '#4a90d9');
  drawSparkline('tr-coke', pts.map(p=>p.coke), '#e76f51');
  drawSparkline('tr-h2', pts.map(p=>p.h2_margin), '#e6a817');
  const last = pts[pts.length-1];
  $('tr-margin-now').textContent = '$'+last.margin.toFixed(2);
  $('tr-octane-now').textContent = last.octane.toFixed(2);
  $('tr-coke-now').textContent = last.coke.toFixed(2)+'%';
  $('tr-h2-now').textContent = last.h2_margin.toFixed(2);
}

function drawSparkline(canvasId, values, color){
  const cv = $(canvasId); if(!cv) return;
  const dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth || 140, h = 44;
  cv.width = w*dpr; cv.height = h*dpr;
  const ctx = cv.getContext('2d'); ctx.scale(dpr,dpr);
  ctx.clearRect(0,0,w,h);
  if(values.length<2) return;
  const min = Math.min(...values), max = Math.max(...values);
  const span = (max-min) || 1;
  ctx.beginPath();
  ctx.strokeStyle = color; ctx.lineWidth = 1.6;
  values.forEach((v,i)=>{
    const x = (i/(values.length-1)) * (w-4) + 2;
    const y = h - 4 - ((v-min)/span) * (h-8);
    if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.stroke();
  // fill under curve
  ctx.lineTo(w-2, h-2); ctx.lineTo(2, h-2); ctx.closePath();
  ctx.fillStyle = color+'22'; ctx.fill();
}

// ---- scenario/fault/market (Tier 2 #11, #15; Tier 1 #2 via render) ----
async function scenario(w){flash();render(await api('/api/scenario','POST',{which:w}));refreshLog();await advise();}
async function injectFault(f){flash();render(await api('/api/fault','POST',{fault:f}));refreshLog();await advise();}
async function applyMarket(){
  const preset = $('marketSel').value;
  flash();
  render(await api('/api/market','POST',{preset}));
  refreshLog();
}
async function clearFaults(){render(await api('/api/clear','POST',{}));refreshLog();$('outcome').innerHTML='';$('applyBtn').style.display='none';buildStepper('idle');}
function flash(){$('units').classList.add('flash');setTimeout(()=>$('units').classList.remove('flash'),600);}

// ---- advisory cycle ----
function startThinkingTimer(){
  const box=$('thinkingStatus'), txt=$('thinkingText'), el=$('thinkingElapsed');
  box.classList.add('show');
  txt.textContent='Agents are investigating the plant state…';
  const t0 = performance.now();
  const timer = setInterval(()=>{
    const secs = (performance.now()-t0)/1000;
    el.textContent = secs.toFixed(1)+'s';
    // contextual messaging as it runs longer -- especially relevant in LIVE
    // mode where rate-limit pacing/cooldowns can genuinely take a while.
    if(secs > 20) txt.textContent='Still working — LIVE mode can pace calls to respect API rate limits…';
    else if(secs > 8) txt.textContent='Strategist and Guardian are reasoning through the proposal…';
    else txt.textContent='Agents are investigating the plant state…';
  }, 100);
  return timer;
}
function stopThinkingTimer(timer){
  clearInterval(timer);
  $('thinkingStatus').classList.remove('show');
}

async function advise(){
  busy=true;$('adviseBtn').disabled=true;$('adviseBtn').textContent='&#9203; Thinking...';
  $('mon-body').textContent='Diagnosing…';$('opt-body').textContent='—';$('saf-body').textContent='—';
  $('outcome').innerHTML='';$('applyBtn').style.display='none';
  buildStepper('thinking');
  const timer = startThinkingTimer();
  try{
    const r=await api('/api/advise','POST',{});lastCard=r;
    const m=r.monitoring;
    const degM=m._degraded?`<span class="badge deg">degraded</span>`:'';
    const statusPill = `<span class="status-pill ${m.status==='problem'?'ALERT':m.status==='opportunity'?'OPTIMIZED':'NOMINAL'}">${(m.status||'?').toUpperCase()}</span>`;
    $('mon-body').innerHTML=`${statusPill}${degM}<br>${esc(m.headline||'')}${reason(m.reasoning)}`;
    let optHtml='',safHtml='';
    r.attempts.forEach(a=>{
      const tag=r.attempts.length>1?`<div class="loop-tag">Attempt ${a.loop}:</div>`:'';
      optHtml+=tag+`<div>${fmtChanges(a.proposed_changes)} &rarr; <b>${money(a.margin_delta)}/day</b>${reason(a.opt_reasoning)}</div>`;
      const vcls=a.verdict||'';
      safHtml+=tag+`<span class="status-pill ${vcls}">${vcls}</span> `+(a.binding_limits.length?`binds: ${a.binding_limits.join(', ')}`:'all clear')+reason(a.safety_reasoning);
    });
    $('opt-body').innerHTML=optHtml||'—';$('saf-body').innerHTML=safHtml||'—';
    const oc=r.outcome;
    const holdMsg = '&#129490; HUMAN INTERVENTION REQUIRED — Subject Matter Expert review needed. '
      + 'Agents could not find a safe improvement within their loop budget.';
    $('outcome').innerHTML=`<div class="outcome ${oc}">${oc==='APPROVED'?'&#10003; APPROVED — '+fmtChanges(r.final_changes):holdMsg} &nbsp;(${r.loops} loop${r.loops>1?'s':''})</div>`;
    if(oc==='APPROVED'&&Object.keys(r.final_changes||{}).length) $('applyBtn').style.display='block';
    buildStepper('done');
    lastAdvisoryTime = Date.now();
    lastAdvisoryOutcome = oc;
    updateLastCycleDisplay();
  }catch(e){$('mon-body').textContent=friendlyError(e);buildStepper('idle');}
  stopThinkingTimer(timer);
  busy=false;$('adviseBtn').disabled=false;$('adviseBtn').innerHTML='&#9654; Run Advisory Cycle';
  refreshLog();
}

async function applyRec(){
  if(!lastCard)return;
  const r=await api('/api/apply','POST',{});
  $('applyBtn').style.display='none';
  await refresh();refreshLog();
  if(r.dispatch_message) showDcsToast(r.dispatch_message);
}

// ---- manual control preview ----
function resetPreview(){$('applyManualBtn').disabled=true;$('previewPanel').classList.remove('show');}
function getSliders(){const ch={};SLIDER_KNOBS.forEach(s=>{ch[s.k]=+$('sl-'+s.k).value;});return ch;}

async function previewManual(){
  $('previewPanel').classList.add('show');
  $('presetNote').innerHTML='';
  $('previewGrid').innerHTML='<div style="color:var(--dim);font-size:11px">Calculating…</div>';
  $('previewSafety').innerHTML='';
  try{
    const p=await api('/api/preview','POST',{changes:getSliders()});
    if(p.error){$('previewGrid').innerHTML=`<div style="color:#ff6b6b">${p.error}</div>`;return;}
    const rows=[
      ['&#128176; Margin $/bbl',  fmt2(p.margin_usd_bbl_before), fmt2(p.margin_usd_bbl_after),  p.margin_usd_bbl_after>p.margin_usd_bbl_before],
      ['&#9981; Gasoline (bpd)', rnd(p.gasoline_pool_bpd_before),rnd(p.gasoline_pool_bpd_after), p.gasoline_pool_bpd_after>p.gasoline_pool_bpd_before],
      ['&#128667; Diesel (bpd)',   rnd(p.diesel_pool_bpd_before), rnd(p.diesel_pool_bpd_after),  p.diesel_pool_bpd_after>p.diesel_pool_bpd_before],
      ['&#9992;&#65039; Jet (bpd)',      rnd(p.jet_bpd_before),         rnd(p.jet_bpd_after),          p.jet_bpd_after>p.jet_bpd_before],
      ['&#11088; Pool Octane',    fmt2(p.pool_octane_before),     fmt2(p.pool_octane_after),     p.pool_octane_after>p.pool_octane_before],
      ['&#128293; FCC Coke %',    fmt2(p.fcc_coke_before),        fmt2(p.fcc_coke_after),        p.fcc_coke_after<p.fcc_coke_before],
      ['&#9879;&#65039; H&#8322; Demand MM',  p.h2_demand_before+'',         p.h2_demand_after+'',          p.h2_demand_after<p.h2_demand_before],
      ['&#128161; Energy kMMBtu', fmt1(p.energy_mmbtu_before),    fmt1(p.energy_mmbtu_after),    p.energy_mmbtu_after<p.energy_mmbtu_before],
      ['&#128167; Sulfur ppm',    p.diesel_sulfur_ppm_before+'',  p.diesel_sulfur_ppm_after+'', p.diesel_sulfur_ppm_after<p.diesel_sulfur_ppm_before],
    ];
    $('previewGrid').innerHTML=rows.map(([lbl,bef,aft,good])=>`<div class="prev-item"><div class="pi-label">${lbl}</div><div class="pi-vals"><span class="before">${bef}</span><span class="arrow-r">&rarr;</span><span class="after ${good===true?'up':good===false?'down':'neutral'}">${aft}</span></div></div>`).join('');
    if(p.all_safe){
      $('previewSafety').innerHTML=`<div class="safe-box">&#9989; All safety limits satisfied — change is safe to apply.</div>`;
      $('applyManualBtn').disabled=false;
    } else {
      const bl=p.breaches.map(b=>`${b.limit} (${b.value} vs ${b.bound})`).join('; ');
      $('previewSafety').innerHTML=`<div class="breach-box">&#128274; Guardian will BLOCK: ${bl}</div>`;
      $('applyManualBtn').disabled=true;
    }
  }catch(e){
    $('previewGrid').innerHTML=`<div style="color:#ff6b6b">${esc(friendlyError(e))}</div>`;
  }
}

// ---- smart preset buttons: real grounded search, no LLM/tokens used ----
async function runPreset(objective){
  const btns = document.querySelectorAll('.preset-btn');
  btns.forEach(b=>b.disabled=true);
  $('presetNote').innerHTML = '<div style="color:var(--dim);font-size:11px;padding:6px 0">&#128269; Scanning configurations and applying the best safe result…</div>';
  try{
    const r = await api('/api/optimize_preset','POST',{objective});
    // r IS the fresh live state (ui_state) plus the preset metadata --
    // render it immediately so KPIs/units/alarm banner all reflect reality
    render(r);
    // reflect the applied knobs on the sliders too, if this objective
    // touched a knob that has one (some searched dims, e.g. fcc_feed_bpd,
    // don't have a slider -- that's fine, nothing to update there)
    Object.entries(r.changes || {}).forEach(([k,v])=>{
      const sl = $('sl-'+k); if(!sl) return;
      const dp = (k.includes('severity')||k.includes('conversion'))?2:0;
      sl.value = v;
      const sv = $('sv-'+k); if(sv) sv.textContent = (+v).toFixed(dp);
    });
    const noteClass = r.applied ? 'safe-box' : 'breach-box';
    const noteIcon = r.applied ? '&#9989;' : '&#129490;';
    $('presetNote').innerHTML =
      `<div class="${noteClass}">${noteIcon} <b>${r.label}:</b> ${esc(r.note)}</div>`;
    if(r.applied){
      flash();
      if(r.dispatch_message) showDcsToast(r.dispatch_message);
    }
    refreshLog();
  }catch(e){
    $('presetNote').innerHTML=`<div class="breach-box">${esc(friendlyError(e))}</div>`;
  }
  btns.forEach(b=>b.disabled=false);
}

async function applyManual(){
  const r=await api('/api/manual','POST',{changes:getSliders()});
  $('previewSafety').innerHTML=r.applied
    ?`<div class="safe-box">&#9989; ${r.verdict} — applied. Margin ${money(r.margin_delta)}/day.</div>`
    :`<div class="breach-box">&#128274; ${r.verdict} — BLOCKED. ${r.binding_limits.join(', ')}</div>`;
  $('applyManualBtn').disabled=true;
  if(r.applied) showDcsToast('Manual setpoint dispatched to Distributed Control System (DCS).');
  await refresh();refreshLog();
}

// ---- assistant + file upload (Tier 2 #12) ----
let __askInFlight = false;
let __askCounter = 0;

async function ask(){
  const inp=$('chatInput');
  if(__askInFlight) return;
  const q=inp.value.trim(); if(!q) return;
  inp.value='';
  __askInFlight = true;
  inp.disabled = true;
  const askBtn = document.querySelector('.chat-in button');
  if(askBtn) askBtn.disabled = true;

  const myId = ++__askCounter;
  addMsg('user', q);
  const myBubble = addMsg('bot', '&#8987; thinking…');

  try {
    const r = await api('/api/assistant','POST',{question:q, uploaded_text: uploadedText});
    if (myBubble && myBubble.isConnected) myBubble.textContent = r.answer || '(no answer)';
  } catch(e) {
    if (myBubble && myBubble.isConnected) myBubble.textContent = friendlyError(e);
  } finally {
    __askInFlight = false;
    inp.disabled = false;
    if(askBtn) askBtn.disabled = false;
    inp.focus();
    const log=$('chatlog'); log.scrollTop = log.scrollHeight;
  }
}
function addMsg(who,txt){
  const l=$('chatlog'); const d=document.createElement('div');
  d.className='msg '+who; d.textContent=txt; l.appendChild(d);
  l.scrollTop=l.scrollHeight;
  return d;
}
function handleFileUpload(evt){
  const file = evt.target.files[0];
  if(!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    uploadedText = e.target.result.slice(0, 20000);   // cap to keep payload sane
    $('fname').textContent = file.name + ' attached (' + Math.round(file.size/1024) + ' KB)';
  };
  reader.readAsText(file);
}

// ---- event log (Tier 2 #16) ----
function setLogFilter(f){
  logFilterActive = f;
  document.querySelectorAll('.log-filter').forEach(el=>el.classList.toggle('active', el.dataset.f===f));
  refreshLog();
}

async function refreshLog(){
  const r=await api('/api/log?n=40');
  const l=$('log');l.innerHTML='';
  let events = r.events.slice().reverse();
  if(logFilterActive!=='all') events = events.filter(e=>e.event_type===logFilterActive);
  events.slice(0,25).forEach((e,idx)=>{
    const hasFull = !!e.full;
    const expandLink = hasFull ? `<span class="expand" onclick="toggleLogFull(this)">[details]</span>` : '';
    const fullBlock = hasFull ? `<div class="full">${esc(JSON.stringify(e.full, null, 1)).slice(0,900)}</div>` : '';
    l.innerHTML+=`<div class="e ${e.event_type}"><span class="t">${e.tick!=null?'t'+e.tick:''} ${e.event_type}</span> — ${esc(e.details)}${e.binding_limits&&e.binding_limits.length?` <span style="color:#ff6b6b">[${e.binding_limits.join(',')}]</span>`:''}${expandLink}${fullBlock}</div>`;
  });
}
function toggleLogFull(el){
  const block = el.nextElementSibling;
  if(block) block.classList.toggle('show');
}

async function exportSnapshot(){
  window.open('/api/export', '_blank');
}

function toggleAbout(show){
  $('aboutModal').classList.toggle('show', show);
}

// ---- Mode disclaimer banner + key-choice modal (the user's 2 requests) ----
function updateModeBanner(status){
  const mb = $('modeBanner');
  const mode = status.mode || 'MOCK';
  $('modeSel').value = mode;

  if(mode === 'LIVE'){
    mb.className = 'mode-banner live';
    $('modeBannerIcon').innerHTML = '&#128994;';
    $('modeBannerText').textContent = 'LIVE MODE — powered by real Groq AI reasoning'
      + (status.using_own_key ? ' (using your own API key).' : " (using the project's default key).");
    $('modeBannerBtn').style.display = 'none';
  } else if(mode === 'REPLAY'){
    mb.className = 'mode-banner replay';
    $('modeBannerIcon').innerHTML = '&#9654;';
    $('modeBannerText').textContent = 'REPLAY MODE — cached responses from a rehearsed run, not live reasoning.';
    $('modeBannerBtn').style.display = 'inline-block';
    $('modeBannerBtn').textContent = 'Switch to LIVE →';
  } else {
    mb.className = 'mode-banner mock';
    $('modeBannerIcon').innerHTML = '&#128993;';
    $('modeBannerText').textContent = 'MOCK MODE — responses are simulated demonstrations, not real AI reasoning.';
    $('modeBannerBtn').style.display = 'inline-block';
    $('modeBannerBtn').textContent = 'Switch to LIVE →';
  }
}

function toggleKeyModal(show){
  $('keyModal').classList.toggle('show', show);
  if(show){
    api('/api/session/status').then(st=>{
      $('keyStatusNote').textContent = `Current session: ${st.mode} mode`
        + (st.using_own_key!==undefined ? (st.using_own_key ? ' (your own key)' : ' (default key)') : '');
    });
  }
}

let __selectedOwnKey = false;
function selectKeyChoice(useOwn){
  __selectedOwnKey = useOwn;
  $('kcDefault').classList.toggle('selected', !useOwn);
  $('kcOwn').classList.toggle('selected', useOwn);
  $('keyInputRow').classList.toggle('show', useOwn);
}

async function saveKeyChoice(){
  const body = {use_own_key: __selectedOwnKey};
  if(__selectedOwnKey){
    const key = $('ownApiKey').value.trim();
    if(!key){ alert('Please paste your Groq API key, or choose "Use project default key" instead.'); return; }
    body.api_key = key;
  }
  const st = await api('/api/session/key','POST',body);
  updateModeBanner(st);
  toggleKeyModal(false);
  $('ownApiKey').value = '';   // never linger in the DOM longer than needed
}

function reason(r){if(!r)return '';const p=[];for(const k in r)if(r[k]&&k!=='_degraded')p.push(`<b>${k}:</b> ${esc(''+r[k])}`);return p.length?`<div class="a-reason">${p.join(' · ')}</div>`:'';}
function fmtChanges(c){if(!c||!Object.keys(c).length)return '(no change)';return Object.entries(c).map(([k,v])=>`${k.replace('_bpd','').replace('hydrocracker','HC').replace(/_/g,' ')}=${(+v).toFixed(k.includes('temp')||k.includes('bpd')?0:2)}`).join(', ');}
function money(v){if(v==null)return '?';return(v>=0?'+':'')+'$'+Math.round(v).toLocaleString();}
function esc(s){return(s||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function fmt2(v){return(+v).toFixed(2);}function fmt1(v){return(+v).toFixed(1);}function rnd(v){return Math.round(+v).toLocaleString();}

init();
</script>
</body>
</html>
"""
