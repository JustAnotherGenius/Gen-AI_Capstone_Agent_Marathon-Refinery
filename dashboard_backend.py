# ============================================================================
#  MARATHON REFINERY OPTIMIZATION ADVISOR  -  DASHBOARD BACKEND
#  Phase: Live Control-Room UI  (Option B: local Flask backend + browser UI)
# ----------------------------------------------------------------------------
#  Thin HTTP layer over the Phase 2 simulator + Phase 3 agents. Serves the
#  single-page dashboard and exposes endpoints the browser polls/calls:
#
#    GET  /                -> the dashboard HTML
#    GET  /api/tick        -> advance plant one step, return live state
#    GET  /api/state       -> current state without advancing
#    GET  /api/history     -> last N ticks of key metrics (trend charts)
#    POST /api/scenario    -> trigger scenario A or B (+ impact summary)
#    POST /api/fault       -> inject a sandbox fault (+ impact summary)
#    POST /api/market      -> apply a market-environment preset
#    POST /api/clear       -> clear all faults
#    POST /api/advise      -> run one full advisory cycle (the 3 agents)
#    POST /api/apply       -> apply an approved recommendation (DCS dispatch)
#    POST /api/manual      -> operator manual knob change (routed through Safety)
#    POST /api/preview     -> preview impact of a manual change (no apply)
#    POST /api/assistant   -> ask the Operator Assistant (preview-only)
#    GET  /api/log         -> the event log (with expandable reasoning)
#    GET  /api/export      -> download full state + log snapshot as JSON
#    GET  /api/config      -> knob ranges, limits, specs, team metadata
#
#  RUN (locally, on your machine):
#     pip install flask
#     python dashboard_backend.py
#     -> open http://127.0.0.1:5000  in your browser
#
#  The backend imports the Phase 2 & Phase 3 modules, so both .py files must
#  be in the same folder as this file.
# ============================================================================

import os
import json
import random
import itertools
from collections import deque
from datetime import datetime
from flask import Flask, request, jsonify, Response

# --- import the simulator (Phase 2) and the agents (Phase 3) ---
import marathon_refinery_sim_phase2 as sim
import marathon_refinery_phase3 as agents
from marathon_refinery_sim_phase2 import (
    CFG, PLANT, step, clear_faults, trigger_scenario_A, trigger_scenario_B,
    inject_fault, SANDBOX_FAULTS, get_refinery_state,
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

# ---------------------------------------------------------------------------
#  Per-browser-session state (mode + own API key), isolated so one visitor's
#  choice never affects another's. The Flask session cookie holds only a
#  random session id (HttpOnly, signed) -- the actual mode/key live SERVER
#  SIDE in this dict, keyed by that id. The key itself is never sent back to
#  any browser, logged, or included in the event log / export snapshot.
# ---------------------------------------------------------------------------
import uuid
from flask import session as flask_session

SESSION_STORE = {}   # {session_id: {"mode": "MOCK"/"LIVE"/"REPLAY", "api_key": str|None}}

def _get_session_id():
    if "sid" not in flask_session:
        flask_session["sid"] = str(uuid.uuid4())
        flask_session.permanent = False
    sid = flask_session["sid"]
    if sid not in SESSION_STORE:
        SESSION_STORE[sid] = {"mode": "MOCK", "api_key": None, "using_own_key": False}
    return sid

def _session_ctx():
    """Build the session_ctx dict passed into every agents.*() call, so this
    visitor's mode/key choice is used for exactly this request and nothing
    else -- see marathon_refinery_phase3.call_llm()'s session_ctx docstring."""
    sid = _get_session_id()
    st = SESSION_STORE[sid]
    return {"session_id": sid, "mode": st["mode"], "api_key": st["api_key"]}

def _session_public_status():
    """What we're willing to tell the browser about its own session --
    NEVER includes the actual key value."""
    sid = _get_session_id()
    st = SESSION_STORE[sid]
    return {"mode": st["mode"], "using_own_key": st["using_own_key"]}

# --- Team / project metadata (Tier 1 #2, #4, #7) -- shown in the About panel
# and system tagline. Feeds the deck's own team list, kept in one place.
TEAM_METADATA = {
    "project_name": "Marathon Refinery Optimization Advisor",
    "tagline": "Real-Time Multi-Agent Digital Twin for Site-Wide Margin Optimization",
    "program": "IIM Mumbai · PGPEX Co'27 Capstone Project",
    "team": [
        {"name": "Prateek Kapoor", "roll": "260303021"},
        {"name": "Price Siddhartha", "roll": "26030303022"},
        {"name": "Priyan Kamble", "roll": "260303023"},
        {"name": "Pushkar Chaturvedi", "roll": "260303024"},
        {"name": "Rajeev Galgali", "roll": "260303025"},
    ],
    "methodology": (
        "Structure: Worley Consulting US refinery archetype (2024). "
        "Scale: Marathon Petroleum FY2025 filings + named Garyville hydrocracker. "
        "Baseline yields: EIA U.S. Refinery Yield data (Mar 2026). "
        "Unit equations are simplified, honestly-labeled engineering approximations."
    ),
}

# --- Market environment presets (Tier 2 #15) -- persistent economic
# conditions the operator can select, distinct from transient faults.
# Each preset is a dict of economics fields to set directly on the plant.
MARKET_PRESETS = {
    "baseline": {
        "label": "Baseline / Normal Market",
        "economics": {},   # empty = reset to CFG baseline via clear_faults()
    },
    "high_diesel_crack": {
        "label": "High Diesel Crack Spread",
        "economics": {"diesel_crack_usd_bbl": 52.0, "diesel_demand_bpd": 95_000},
    },
    "high_gasoline_crack": {
        "label": "High Gasoline Crack Spread",
        "economics": {"gasoline_crack_usd_bbl": 42.0, "gasoline_demand_bpd": 130_000},
    },
    "high_sulfur_discount": {
        "label": "High-Sulfur Crude Discount",
        "economics": {"crude_cost_usd_bbl": 68.0},   # cheaper, sourer crude
    },
}

# --- Rolling history for trend charts (Tier 2 #9) -- capped ring buffer,
# one entry appended per tick/state-changing call.
HISTORY_MAX = 40
HISTORY = deque(maxlen=HISTORY_MAX)



# Load operator manuals into the assistant's context.
# We combine three sources (in priority order):
#   1. Gemini's detailed process manual (Master_Refinery_Operations_Manual_Plant.md)
#   2. Our plain-language guide (Refinery_Process_Optimization_Advisor_Plant_Agent.md)
#   3. Our own User_Manual.md (if present alongside this file)
# All three are concatenated so the Advisor can answer questions from any of them.
_manual_parts = []
for _mpath in [
    "Master_Refinery_Operations_Manual_Plant.md",
    "Refinery_Process_Optimization_Advisor_Plant_Agent.md",
    "User_Manual.md",
]:
    try:
        with open(_mpath, encoding="utf-8", errors="replace") as _f:
            _manual_parts.append(f"=== {_mpath} ===\n" + _f.read())
    except FileNotFoundError:
        pass  # optional — skip if not present

if _manual_parts:
    agents.load_user_manual("\n\n".join(_manual_parts))
    print(f"  Manuals loaded: {len(_manual_parts)} file(s), "
          f"{len(agents.USER_MANUAL_TEXT):,} chars total")
else:
    agents.load_user_manual("(no manual files found — assistant runs on tools only)")


# ---------------------------------------------------------------------------
#  Helpers: build a compact, JSON-safe snapshot for the browser to render
# ---------------------------------------------------------------------------
def _display_noise(value, magnitude=0.004):
    """Tier 1 #1 -- tiny display-only sensor jitter (+/- ~0.4%) so live
    readouts don't look frozen between operator actions. This NEVER touches
    the underlying PLANT state or feeds into agent/Safety calculations --
    those always reason on the true, noise-free value. Display only."""
    return value * (1.0 + random.uniform(-magnitude, magnitude))


def _risk_score(s, lim, spec):
    """Tier 2 #10 -- a single 0-100 plant health score. For each tracked
    metric, compute headroom to its limit AS A FRACTION OF ITS REALISTIC
    OPERATING SPAN (not a raw value/limit ratio). This matters because our
    plant is deliberately calibrated with normal operation sitting fairly
    close to some limits (furnace 365 vs 370 limit; coke ~4.9% vs 6.0% limit)
    -- that's the trip-wire mechanic the demo scenarios rely on. A raw
    value/limit ratio would misreport totally normal operation as
    near-critical. We instead measure headroom against each metric's
    realistic low-end (the knob's own minimum, or a sensible process floor),
    then apply a concave (sqrt) transform: risk near a limit still drops
    toward 0, but the mid-range doesn't read as artificially alarming.
    This is a transparent, documented composite -- not a hidden black box."""
    def headroom_below_ceiling(value, ceiling, floor):
        """For metrics with an upper hard limit (furnace temp, coke %):
        100 = as far as realistically possible from the ceiling, 0 = at it."""
        span = max(ceiling - floor, 1e-9)
        pct = 100.0 * (ceiling - value) / span
        pct = max(0.0, min(100.0, pct))
        return (pct / 100.0) ** 0.5 * 100.0     # concave transform

    def headroom_above_floor(value, floor, comfortable_above):
        """For metrics with a lower hard limit (octane must stay >= floor):
        100 = comfortably above the floor, 0 = at the floor."""
        span = max(comfortable_above, 1e-9)
        pct = 100.0 * (value - floor) / span
        pct = max(0.0, min(100.0, pct))
        return (pct / 100.0) ** 0.5 * 100.0

    octane_h = headroom_above_floor(s["pool_octane_RON"], spec["gasoline_octane_floor_RON"], 3.0)
    coke_h = headroom_below_ceiling(s["coke_make_pct"], lim["fcc_coke_make_max_pct"], 3.0)   # 3.0% = typical low-severity coke
    furnace_h = headroom_below_ceiling(s["knobs"]["cdu_furnace_temp_C"], lim["cdu_furnace_temp_max_C"],
                                        CFG["knobs"]["cdu_furnace_temp_C"]["min"])            # knob's real floor
    h2_ratio = s["h2_available_scfd"] / max(s["h2_demand_scfd"], 1.0)
    h2_pct = max(0.0, min(100.0, (h2_ratio - 1.0) * 200))       # 0% at parity, 100% at 1.5x supply
    h2_h = (h2_pct / 100.0) ** 0.5 * 100.0                       # same concave shape

    score = (octane_h + coke_h + furnace_h + h2_h) / 4.0
    return round(score, 0)


# ---------------------------------------------------------------------------
#  "Smart preset" buttons (Manual Control panel) -- a REAL grounded grid
#  search over simulate_proposal(), NOT an LLM call. Zero token cost, fully
#  deterministic and reproducible, works identically in MOCK/LIVE/REPLAY.
#  Every candidate is checked against Guardian's real limits before being
#  offered -- these presets never suggest an unsafe configuration.
# ---------------------------------------------------------------------------
def _grid(lo, hi, steps=5):
    return [round(lo + (hi - lo) * i / (steps - 1), 4) for i in range(steps)]

PRESET_OBJECTIVES = {
    "max_profit": {
        "label": "Maximize Profit per Barrel",
        "dims": {
            "hydrocracker_conversion": _grid(0.60, 0.98),
            "fcc_severity": _grid(0.40, 0.90),
            "reformer_severity": _grid(0.40, 0.88),
        },
    },
    "max_octane": {
        "label": "Maximize Octane Number",
        "dims": {
            "reformer_severity": _grid(0.40, 0.88),
            "fcc_severity": _grid(0.40, 0.90),
            "hydrocracker_conversion": _grid(0.60, 0.98),
        },
    },
    "max_health": {
        "label": "Maximize Plant Health",
        "dims": {
            "cdu_furnace_temp_C": _grid(340, 400),
            "fcc_severity": _grid(0.40, 0.90),
            "hydrocracker_conversion": _grid(0.60, 0.98),
            "reformer_severity": _grid(0.40, 0.88),
        },
    },
    "min_coke": {
        "label": "Minimize Coke Generation",
        "dims": {
            "fcc_severity": _grid(0.40, 0.90),
            "fcc_feed_bpd": _grid(20_000, 80_000),
        },
    },
    "balanced": {
        "label": "Most Optimum Setup (Balanced)",
        "dims": {
            "hydrocracker_conversion": _grid(0.60, 0.98),
            "fcc_severity": _grid(0.40, 0.90),
            "reformer_severity": _grid(0.40, 0.88),
            "cdu_furnace_temp_C": _grid(340, 400),
        },
    },
}


def _objective_score(objective, pred, all_margins=None, all_risks=None):
    """Higher is always better, regardless of objective."""
    if objective == "max_profit":
        return pred["margin_usd_bbl"]
    if objective == "max_octane":
        return pred["pool_octane_RON"]
    if objective == "max_health":
        return _risk_score(pred, CFG["limits"], CFG["specs"])
    if objective == "min_coke":
        return -pred["coke_make_pct"]              # lower coke = higher score
    if objective == "balanced":
        # normalize margin and risk onto comparable 0-1 scales using the
        # batch's own observed range, then blend 60% margin / 40% health.
        m_lo, m_hi = min(all_margins), max(all_margins)
        r_lo, r_hi = min(all_risks), max(all_risks)
        m_norm = (pred["margin_usd_bbl"] - m_lo) / max(m_hi - m_lo, 1e-9)
        r_norm = (_risk_score(pred, CFG["limits"], CFG["specs"]) - r_lo) / max(r_hi - r_lo, 1e-9)
        return 0.6 * m_norm + 0.4 * r_norm
    raise ValueError(f"unknown objective '{objective}'")


def run_preset_search(objective, snapshot):
    """Scan the objective's grid, score every SAFE candidate on the real
    physics, return the best one. Falls back to 'no change' if nothing in
    the grid is safe (only possible under extreme fault conditions)."""
    if objective not in PRESET_OBJECTIVES:
        raise ValueError(f"unknown objective '{objective}'")
    spec = PRESET_OBJECTIVES[objective]
    dims = spec["dims"]
    dim_names = list(dims.keys())

    candidates = []   # (changes, predicted_state, is_safe)
    for combo in itertools.product(*dims.values()):
        changes = dict(zip(dim_names, combo))
        try:
            pred = sim.simulate_proposal(changes, snapshot)
        except Exception:
            continue
        safe = agents.check_all_limits(pred)["all_ok"]
        candidates.append((changes, pred, safe))

    safe_candidates = [c for c in candidates if c[2]]
    pool = safe_candidates if safe_candidates else candidates
    fell_back_unsafe = not safe_candidates

    if objective == "balanced" and pool:
        all_margins = [c[1]["margin_usd_bbl"] for c in pool]
        all_risks = [_risk_score(c[1], CFG["limits"], CFG["specs"]) for c in pool]
        scored = [(_objective_score(objective, c[1], all_margins, all_risks), c) for c in pool]
    else:
        scored = [(_objective_score(objective, c[1]), c) for c in pool]

    if not scored:
        # nothing evaluable at all -- return "no change" as the safe fallback
        return {"changes": {}, "predicted": snapshot, "scanned": len(candidates),
                "safe_found": 0, "fell_back_unsafe": True, "dims_searched": dim_names}

    scored.sort(key=lambda x: x[0], reverse=True)
    best_changes, best_pred, best_safe = scored[0][1]

    return {"changes": best_changes, "predicted": best_pred,
            "scanned": len(candidates), "safe_found": len(safe_candidates),
            "fell_back_unsafe": fell_back_unsafe, "dims_searched": dim_names}


def _ui_state(s, record_history=False):
    """Trim the big state dict to what the dashboard displays."""
    lim = CFG["limits"]; spec = CFG["specs"]
    limit_report = agents.check_all_limits(s)
    breaches = [{"limit": c["limit"], "value": c["value"], "bound": c["bound"]}
                for c in limit_report["checks"] if not c["ok"]]
    risk = _risk_score(s, lim, spec)

    out = {
        "tick": s.get("tick"),
        "active_faults": s.get("active_faults", []),
        "margin_usd_bbl": round(_display_noise(s["margin_usd_bbl"]), 2),
        "margin_usd_day": round(s["margin_usd_day"], 0),
        "slate": {
            "gasoline": round(s["slate_gasoline_pct"], 1),
            "distillate": round(s["slate_distillate_pct"], 1),
            "jet": round(s["slate_jet_pct"], 1),
        },
        "pool_octane": round(_display_noise(s["pool_octane_RON"], 0.001), 2),
        "octane_floor": spec["gasoline_octane_floor_RON"],
        "diesel_sulfur_ppm": round(s["diesel_sulfur_wt_pct"] * 1e4, 1),
        "sulfur_cap_ppm": round(spec["diesel_sulfur_cap_wt_pct"] * 1e4, 0),
        "fcc_coke_pct": round(_display_noise(s["coke_make_pct"], 0.006), 2),
        "fcc_coke_limit": lim["fcc_coke_make_max_pct"],
        "h2_demand": round(_display_noise(s["h2_demand_scfd"]) / 1e6, 2),
        "h2_available": round(s["h2_available_scfd"] / 1e6, 2),
        "feed_pool": round(s["feed_pool_bpd"], 0),
        "fcc_feed": round(s["fcc_feed_actual_bpd"], 0),
        "hc_feed": round(s["hc_feed_actual_bpd"], 0),
        "furnace_temp": round(s["knobs"]["cdu_furnace_temp_C"], 1),
        "furnace_limit": lim["cdu_furnace_temp_max_C"],
        "economics": {
            "gasoline_crack": round(s["economics"]["gasoline_crack_usd_bbl"], 1),
            "diesel_crack": round(s["economics"]["diesel_crack_usd_bbl"], 1),
            "energy_cost": round(s["economics"]["energy_cost_usd_mmbtu"], 2),
        },
        "knobs": {k: round(v, 4) for k, v in s["knobs"].items()},
        "mode": _session_public_status()["mode"],
        "breaches": breaches,              # Tier 1 #2 -- alarm banner
        "risk_score": risk,                # Tier 2 #10 -- health gauge
        # Per-unit LIVE OUTPUTS (not setpoints) -- the user's original ask
        # was for unit boxes to visibly update every tick, same as the KPI
        # strip. A knob (setpoint) correctly should NOT wobble on its own --
        # that would misrepresent what a setpoint means. These are instead
        # each unit's real computed output, which does respond to crude/
        # market drift even at a fixed setpoint. Cosmetic display noise
        # (same pattern as the KPI strip, never touching real physics or
        # Guardian's checks) is layered on top since the raw drift alone is
        # too small to show up at display precision -- see diagnosis notes.
        "unit_outputs": {
            "cdu": round(_display_noise(100 * s["cdu_diesel_bpd"] / max(s["knobs"]["cdu_throughput_bpd"], 1), 0.01), 2),
            "vdu": round(_display_noise(100 * s["vgo_bpd"] / max(s["residue_bpd"], 1), 0.01), 2),
            "fcc": round(_display_noise(100 * s["fcc_gasoline_bpd"] / max(s["fcc_feed_actual_bpd"], 1), 0.01), 2),
            "ref": round(_display_noise(s["reformate_bov"], 0.003), 2),
            "hc": round(_display_noise(100 * s["hc_gasoline_bpd"] / max(s["hc_gasoline_bpd"] + s["hc_diesel_bpd"], 1), 0.01), 2),
            "blend": round(_display_noise(s["gasoline_pool_bpd"], 0.006), 0),
        },
        # Nice-to-have #5: per-fault "active for Xs" duration, computed from
        # real tick count x the configured tick interval -- server-side, so
        # it survives a page refresh and stays consistent across tabs.
        "fault_details": [
            {"name": f["name"], "duration_ticks": f["duration_ticks"],
             "duration_seconds": round(f["duration_ticks"] * CFG["sim"]["tick_seconds"], 0)}
            for f in s.get("fault_details", [])
        ],
    }

    if record_history:
        HISTORY.append({
            "tick": s.get("tick"),
            "margin": round(s["margin_usd_bbl"], 2),         # true value, not noised
            "octane": round(s["pool_octane_RON"], 2),
            "coke": round(s["coke_make_pct"], 2),
            "h2_margin": round((s["h2_available_scfd"] - s["h2_demand_scfd"]) / 1e6, 2),
            "risk": risk,
        })
    return out




# ---------------------------------------------------------------------------
#  Fault/scenario/market impact summary (Tier 2 #11)
# ---------------------------------------------------------------------------
def _impact_summary(label, before_margin, after_state):
    """One-line, human-readable delta text shown immediately on injection,
    e.g. 'H2 shortfall detected -> expected margin drop of $1.42/bbl'.
    Uses the TRUE (non-noised) margin so the number is exactly reproducible."""
    after_margin = after_state["margin_usd_bbl"]
    delta = after_margin - before_margin
    direction = "gain" if delta >= 0 else "drop"
    limit_report = agents.check_all_limits(after_state)
    breaches = [c["limit"] for c in limit_report["checks"] if not c["ok"]]
    breach_note = f" | ALREADY BREACHING: {', '.join(breaches)}" if breaches else ""
    text = (f"{label} -> immediate margin {direction} of ${abs(delta):.2f}/bbl "
            f"(${before_margin:.2f} -> ${after_margin:.2f}){breach_note}")
    return {"text": text, "before_margin": round(before_margin, 2),
            "after_margin": round(after_margin, 2), "delta": round(delta, 2),
            "breaches_now": breaches}


# ---------------------------------------------------------------------------
#  Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return Response(DASHBOARD_HTML, mimetype="text/html")


@app.route("/api/config")
def api_config():
    """Knob ranges, limits, specs, fault list, team metadata, market presets."""
    return jsonify({
        "knobs": CFG["knobs"],
        "limits": CFG["limits"],
        "specs": CFG["specs"],
        "sandbox_faults": SANDBOX_FAULTS,
        "scenarios": ["scenario_A_gasoline_opportunity", "scenario_B_diesel_coldsnap"],
        "meta": TEAM_METADATA,
        "market_presets": {k: v["label"] for k, v in MARKET_PRESETS.items()},
    })


@app.route("/api/tick")
def api_tick():
    """Advance the plant one tick (the live heartbeat)."""
    s = step()
    return jsonify(_ui_state(s, record_history=True))


@app.route("/api/state")
def api_state():
    s = get_refinery_state()
    return jsonify(_ui_state(s, record_history=True))


@app.route("/api/history")
def api_history():
    """Tier 2 #9 -- last N ticks of key metrics, for trend charts."""
    return jsonify({"points": list(HISTORY)})


@app.route("/api/scenario", methods=["POST"])
def api_scenario():
    which = (request.json or {}).get("which", "A")
    before_margin = get_refinery_state()["margin_usd_bbl"]
    if which == "A":
        s = trigger_scenario_A()
        label = "Scenario A: gasoline opportunity triggered"
    else:
        s = trigger_scenario_B()
        label = "Scenario B: cold-snap diesel spike triggered"
    impact = _impact_summary(label, before_margin, s)
    agents.log_event("scenario", impact["text"], s)
    out = _ui_state(s, record_history=True)
    out["impact_summary"] = impact
    return jsonify(out)


@app.route("/api/fault", methods=["POST"])
def api_fault():
    fid = (request.json or {}).get("fault")
    if fid not in SANDBOX_FAULTS:
        return jsonify({"error": f"unknown fault '{fid}'"}), 400
    before_margin = get_refinery_state()["margin_usd_bbl"]
    s = inject_fault(fid)
    impact = _impact_summary(f"sandbox fault injected: {fid}", before_margin, s)
    agents.log_event("fault", impact["text"], s)
    out = _ui_state(s, record_history=True)
    out["impact_summary"] = impact
    return jsonify(out)


@app.route("/api/market", methods=["POST"])
def api_market():
    """Tier 2 #15 -- apply a persistent market-environment preset."""
    key = (request.json or {}).get("preset", "baseline")
    if key not in MARKET_PRESETS:
        return jsonify({"error": f"unknown preset '{key}'"}), 400
    before_margin = get_refinery_state()["margin_usd_bbl"]
    if key == "baseline":
        s = clear_faults()
    else:
        preset = MARKET_PRESETS[key]
        for k, v in preset["economics"].items():
            PLANT["economics"][k] = v
        s = step()
    impact = _impact_summary(f"market environment set: {MARKET_PRESETS[key]['label']}", before_margin, s)
    agents.log_event("market", impact["text"], s)
    out = _ui_state(s, record_history=True)
    out["impact_summary"] = impact
    return jsonify(out)


@app.route("/api/clear", methods=["POST"])
def api_clear():
    s = clear_faults()
    agents.log_event("clear", "all faults cleared; plant reset to baseline", s)
    return jsonify(_ui_state(s, record_history=True))


@app.route("/api/advise", methods=["POST"])
def api_advise():
    """Run ONE full advisory cycle: Monitor -> Optimize -> Safety (+ loops)."""
    card = agents.run_advisory_cycle(verbose=False, session_ctx=_session_ctx())
    # shape the card for the UI
    attempts = []
    for a in card.get("attempts", []):
        attempts.append({
            "loop": a["loop"],
            "proposed_changes": a["proposed_changes"],
            "margin_delta": a.get("predicted_margin_delta_usd_day"),
            "verdict": a["verdict"],
            "binding_limits": [b["limit"] for b in a.get("binding_limits", [])],
            "opt_reasoning": a.get("opt_reasoning"),
            "safety_reasoning": a.get("safety_reasoning"),
        })
    out = {
        "outcome": card["outcome"],
        "loops": card["loops"],
        "monitoring": card["monitoring"],
        "attempts": attempts,
        "final_changes": card["final_changes"],
    }
    # Tier 2 #16 -- stash the FULL card on the most recent log entry (already
    # written by run_advisory_cycle) so the event log can offer an expandable
    # "show full reasoning" view without a second round-trip.
    if agents.EVENT_LOG:
        agents.EVENT_LOG[-1]["full"] = out
    return jsonify(out)


@app.route("/api/apply", methods=["POST"])
def api_apply():
    """Operator accepts an approved recommendation -> dispatches to the
    (simulated) Distributed Control System. Tier 1 #5, #7 -- explicit
    advisory-mode language: this is a human-triggered dispatch action,
    never an autonomous write."""
    card = agents.run_advisory_cycle(verbose=False, session_ctx=_session_ctx())
    result = agents.apply_recommendation(card)
    if result.get("applied"):
        result["dispatch_message"] = (
            "Optimized parameters successfully dispatched to Distributed "
            "Control System (DCS) — operator-confirmed action."
        )
        agents.log_event("dispatch", result["dispatch_message"], PLANT.get("state"))
    else:
        result["dispatch_message"] = "No dispatch: " + str(result.get("reason", "not approved"))
    return jsonify(result)


@app.route("/api/export")
def api_export():
    """Tier 1 #8 -- download a full snapshot (current state + event log +
    trend history) as JSON, e.g. for a shift-handover report."""
    s = get_refinery_state()
    snapshot = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "project": TEAM_METADATA["project_name"],
        "current_state": _ui_state(s),
        "history": list(HISTORY),
        "event_log": agents.EVENT_LOG[-100:],
    }
    body = json.dumps(snapshot, indent=2, default=str)
    return Response(body, mimetype="application/json",
                    headers={"Content-Disposition": "attachment; filename=refinery_snapshot.json"})


@app.route("/api/preview", methods=["POST"])
def api_preview():
    """Preview the full predicted downstream impact of a manual knob change
    WITHOUT applying it to the live plant. Powers Idea 3's impact panel."""
    try:
        changes = (request.json or {}).get("changes", {})
        changes = {k: float(v) for k, v in changes.items()}
        snapshot = get_refinery_state()
        pred = sim.simulate_proposal(changes, snapshot)
        lim = sim.CFG["limits"]; spec = sim.CFG["specs"]
        limit_report = agents.check_all_limits(pred)
        breaches = [c for c in limit_report["checks"] if not c["ok"]]
        return jsonify({
            "proposed_changes": changes,
            # economic impact
            "margin_delta_usd_day": round(pred["margin_delta_usd_day"], 0),
            "margin_usd_bbl_before": round(snapshot["margin_usd_bbl"], 2),
            "margin_usd_bbl_after": round(pred["margin_usd_bbl"], 2),
            # product slate
            "gasoline_pool_bpd_before": round(snapshot["gasoline_pool_bpd"], 0),
            "gasoline_pool_bpd_after": round(pred["gasoline_pool_bpd"], 0),
            "diesel_pool_bpd_before": round(snapshot["diesel_pool_bpd"], 0),
            "diesel_pool_bpd_after": round(pred["diesel_pool_bpd"], 0),
            "jet_bpd_before": round(snapshot["jet_bpd"], 0),
            "jet_bpd_after": round(pred["jet_bpd"], 0),
            # quality
            "pool_octane_before": round(snapshot["pool_octane_RON"], 2),
            "pool_octane_after": round(pred["pool_octane_RON"], 2),
            "diesel_sulfur_ppm_before": round(snapshot["diesel_sulfur_wt_pct"]*1e4, 1),
            "diesel_sulfur_ppm_after": round(pred["diesel_sulfur_wt_pct"]*1e4, 1),
            # unit constraints
            "fcc_coke_before": round(snapshot["coke_make_pct"], 2),
            "fcc_coke_after": round(pred["coke_make_pct"], 2),
            "h2_demand_before": round(snapshot["h2_demand_scfd"]/1e6, 2),
            "h2_demand_after": round(pred["h2_demand_scfd"]/1e6, 2),
            "h2_available": round(pred["h2_available_scfd"]/1e6, 2),
            "energy_mmbtu_before": round(snapshot["total_energy_mmbtu_day"]/1000, 1),
            "energy_mmbtu_after": round(pred["total_energy_mmbtu_day"]/1000, 1),
            # feed routing
            "fcc_feed_before": round(snapshot["fcc_feed_actual_bpd"], 0),
            "fcc_feed_after": round(pred["fcc_feed_actual_bpd"], 0),
            "hc_feed_before": round(snapshot["hc_feed_actual_bpd"], 0),
            "hc_feed_after": round(pred["hc_feed_actual_bpd"], 0),
            # safety
            "all_safe": limit_report["all_ok"],
            "breaches": [{"limit": b["limit"], "value": b["value"],
                         "bound": b["bound"]} for b in breaches],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/optimize_preset", methods=["POST"])
def api_optimize_preset():
    """Manual Control 'smart preset' buttons. A REAL grid search over
    simulate_proposal() -- no LLM involved, zero token cost, deterministic.
    ONE-CLICK AUTO-APPLY: the winning configuration is already guaranteed
    safe (every candidate is filtered through check_all_limits() during the
    search itself), so we apply it directly to the live plant -- no separate
    preview/confirm step, and no redundant LLM Safety-agent re-check (which
    would just re-verify what the deterministic search already proved).
    If NO safe configuration exists in the grid, nothing is applied and the
    response says so plainly (consistent with the HOLD / human-intervention
    language used elsewhere)."""
    objective = (request.json or {}).get("objective")
    if objective not in PRESET_OBJECTIVES:
        return jsonify({"error": f"unknown objective '{objective}'"}), 400
    try:
        snapshot = get_refinery_state()
        result = run_preset_search(objective, snapshot)
        label = PRESET_OBJECTIVES[objective]["label"]

        applied = False
        if result["changes"] and not result["fell_back_unsafe"]:
            for name, val in result["changes"].items():
                PLANT["knobs"][name] = sim.clamp_knob(name, val)
            new_state = step()            # actually apply + advance the live plant
            applied = True
            note = (f"Applied — scanned {result['scanned']} configurations "
                    f"({result['safe_found']} safe), optimizing for {label.lower()}. "
                    f"Adjusted: {', '.join(result['dims_searched'])}.")
        else:
            new_state = snapshot          # nothing changed
            note = ("No safe configuration found in the search grid under current "
                    "conditions — setpoints unchanged. Human/SME review recommended.")

        agents.log_event("preset_applied" if applied else "preset_search",
                          f"{label}: {note}", new_state)

        out = _ui_state(new_state, record_history=True)
        out.update({
            "objective": objective,
            "label": label,
            "applied": applied,
            "changes": result["changes"] if applied else {},
            "note": note,
            "scanned": result["scanned"],
            "safe_found": result["safe_found"],
            "fell_back_unsafe": result["fell_back_unsafe"],
            "dispatch_message": (f"{label} — optimized parameters dispatched to "
                                 f"Distributed Control System (DCS).") if applied else None,
        })
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": f"preset search failed: {e}"}), 400



@app.route("/api/manual", methods=["POST"])
def api_manual():
    """Operator manual knob change - routed through the Safety Agent."""
    changes = (request.json or {}).get("changes", {})
    # numeric coercion
    changes = {k: float(v) for k, v in changes.items()}
    result = agents.operator_manual_change(changes, apply_if_safe=True, session_ctx=_session_ctx())
    v = result["verdict"]
    return jsonify({
        "verdict": v.get("verdict"),
        "applied": result["applied"],
        "binding_limits": [b["limit"] for b in v.get("binding_limits", [])],
        "reasoning": v.get("reasoning"),
        "margin_delta": result["predicted_margin_delta_usd_day"],
    })


@app.route("/api/assistant", methods=["POST"])
def api_assistant():
    """Operator Assistant - conversational, preview-only."""
    body = request.json or {}
    question = body.get("question", "")
    uploaded = body.get("uploaded_text") or None
    result = agents.operator_assistant(question, uploaded_text=uploaded, session_ctx=_session_ctx())
    return jsonify(result)


@app.route("/api/log")
def api_log():
    n = int(request.args.get("n", 12))
    return jsonify({"events": agents.EVENT_LOG[-n:]})


@app.route("/api/session/status")
def api_session_status():
    """What mode this browser session is in, and whether it's using its own
    key or the project default. Never returns the actual key value."""
    return jsonify(_session_public_status())


@app.route("/api/session/key", methods=["POST"])
def api_session_key():
    """Set this browser session's key choice:
       {"use_own_key": false}                -> use the project default key
       {"use_own_key": true, "api_key": "…"}  -> use the visitor's own key
    Either choice AUTO-SWITCHES this session to LIVE mode (per design), so
    picking a key is a single action, not two clicks. The key is stored only
    in the server-side SESSION_STORE for this session id -- never echoed
    back, logged, or written to the event log / export snapshot."""
    body = request.json or {}
    use_own = bool(body.get("use_own_key"))
    sid = _get_session_id()
    st = SESSION_STORE[sid]

    if use_own:
        key = (body.get("api_key") or "").strip()
        if not key:
            return jsonify({"error": "api_key required when use_own_key is true"}), 400
        st["api_key"] = key
        st["using_own_key"] = True
    else:
        st["api_key"] = None
        st["using_own_key"] = False

    st["mode"] = "LIVE"     # auto-switch, per design decision
    return jsonify(_session_public_status())


@app.route("/api/session/mode", methods=["POST"])
def api_session_mode():
    """Explicitly switch THIS session's mode (e.g. back to MOCK) without
    changing the key choice already on file for this session."""
    m = (request.json or {}).get("mode", "MOCK").upper()
    if m not in ("MOCK", "LIVE", "REPLAY"):
        return jsonify({"error": "invalid mode"}), 400
    sid = _get_session_id()
    SESSION_STORE[sid]["mode"] = m
    return jsonify(_session_public_status())


# The dashboard HTML is defined in the companion file and injected here at
# import time (keeps this backend file focused on logic).
from dashboard_html import DASHBOARD_HTML


if __name__ == "__main__":
    # start a fresh, calm plant
    clear_faults()
    print("=" * 60)
    print("  MARATHON REFINERY DASHBOARD")
    print("  Open:  http://127.0.0.1:5000")
    print(f"  LLM mode: {agents.LLM_CONFIG['mode']}  "
          f"(switch to LIVE from the UI or LLM_CONFIG)")
    print("=" * 60)
    port = int(os.environ.get("PORT", 5000))     # cloud hosts set PORT; local defaults to 5000
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"   # 0.0.0.0 = reachable publicly
    app.run(host=host, port=port, debug=False, threaded=True)
