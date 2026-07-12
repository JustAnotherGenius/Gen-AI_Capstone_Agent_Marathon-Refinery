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
#    POST /api/scenario    -> trigger scenario A or B
#    POST /api/fault       -> inject a sandbox fault
#    POST /api/clear       -> clear all faults
#    POST /api/advise      -> run one full advisory cycle (the 3 agents)
#    POST /api/manual      -> operator manual knob change (routed through Safety)
#    POST /api/assistant   -> ask the Operator Assistant (preview-only)
#    GET  /api/log         -> the event log
#    GET  /api/config      -> knob ranges, limits, specs (for UI sliders/gauges)
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
from flask import Flask, request, jsonify, Response

# --- import the simulator (Phase 2) and the agents (Phase 3) ---
import marathon_refinery_sim_phase2 as sim
import marathon_refinery_phase3 as agents
from marathon_refinery_sim_phase2 import (
    CFG, PLANT, step, clear_faults, trigger_scenario_A, trigger_scenario_B,
    inject_fault, SANDBOX_FAULTS, get_refinery_state,
)

app = Flask(__name__)

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
def _ui_state(s):
    """Trim the big state dict to what the dashboard displays."""
    lim = CFG["limits"]; spec = CFG["specs"]
    return {
        "tick": s.get("tick"),
        "active_faults": s.get("active_faults", []),
        "margin_usd_bbl": round(s["margin_usd_bbl"], 2),
        "margin_usd_day": round(s["margin_usd_day"], 0),
        "slate": {
            "gasoline": round(s["slate_gasoline_pct"], 1),
            "distillate": round(s["slate_distillate_pct"], 1),
            "jet": round(s["slate_jet_pct"], 1),
        },
        "pool_octane": round(s["pool_octane_RON"], 2),
        "octane_floor": spec["gasoline_octane_floor_RON"],
        "diesel_sulfur_ppm": round(s["diesel_sulfur_wt_pct"] * 1e4, 1),
        "sulfur_cap_ppm": round(spec["diesel_sulfur_cap_wt_pct"] * 1e4, 0),
        "fcc_coke_pct": round(s["coke_make_pct"], 2),
        "fcc_coke_limit": lim["fcc_coke_make_max_pct"],
        "h2_demand": round(s["h2_demand_scfd"] / 1e6, 2),
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
        "mode": agents.LLM_CONFIG["mode"],
    }


# ---------------------------------------------------------------------------
#  Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return Response(DASHBOARD_HTML, mimetype="text/html")


@app.route("/api/config")
def api_config():
    """Knob ranges, limits, specs, fault list - so the UI can build controls."""
    return jsonify({
        "knobs": CFG["knobs"],
        "limits": CFG["limits"],
        "specs": CFG["specs"],
        "sandbox_faults": SANDBOX_FAULTS,
        "scenarios": ["scenario_A_gasoline_opportunity", "scenario_B_diesel_coldsnap"],
    })


@app.route("/api/tick")
def api_tick():
    """Advance the plant one tick (the live heartbeat)."""
    s = step()
    return jsonify(_ui_state(s))


@app.route("/api/state")
def api_state():
    s = get_refinery_state()
    return jsonify(_ui_state(s))


@app.route("/api/scenario", methods=["POST"])
def api_scenario():
    which = (request.json or {}).get("which", "A")
    if which == "A":
        s = trigger_scenario_A()
        agents.log_event("scenario", "Scenario A: gasoline opportunity triggered", s)
    else:
        s = trigger_scenario_B()
        agents.log_event("scenario", "Scenario B: cold-snap diesel spike triggered", s)
    return jsonify(_ui_state(s))


@app.route("/api/fault", methods=["POST"])
def api_fault():
    fid = (request.json or {}).get("fault")
    if fid not in SANDBOX_FAULTS:
        return jsonify({"error": f"unknown fault '{fid}'"}), 400
    s = inject_fault(fid)
    agents.log_event("fault", f"sandbox fault injected: {fid}", s)
    return jsonify(_ui_state(s))


@app.route("/api/clear", methods=["POST"])
def api_clear():
    s = clear_faults()
    agents.log_event("clear", "all faults cleared; plant reset to baseline", s)
    return jsonify(_ui_state(s))


@app.route("/api/advise", methods=["POST"])
def api_advise():
    """Run ONE full advisory cycle: Monitor -> Optimize -> Safety (+ loops)."""
    card = agents.run_advisory_cycle(verbose=False)
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
    return jsonify({
        "outcome": card["outcome"],
        "loops": card["loops"],
        "monitoring": card["monitoring"],
        "attempts": attempts,
        "final_changes": card["final_changes"],
    })


@app.route("/api/apply", methods=["POST"])
def api_apply():
    """Operator accepts an approved recommendation -> apply to live plant."""
    card = agents.run_advisory_cycle(verbose=False)
    result = agents.apply_recommendation(card)
    return jsonify(result)


@app.route("/api/preview", methods=["POST"])
def api_preview():
    """Preview the full predicted downstream impact of a manual knob change
    WITHOUT applying it to the live plant. Powers Idea 3's impact panel."""
    changes = (request.json or {}).get("changes", {})
    changes = {k: float(v) for k, v in changes.items()}
    snapshot = get_refinery_state()
    try:
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



@app.route("/api/manual", methods=["POST"])
def api_manual():
    """Operator manual knob change - routed through the Safety Agent."""
    changes = (request.json or {}).get("changes", {})
    # numeric coercion
    changes = {k: float(v) for k, v in changes.items()}
    result = agents.operator_manual_change(changes, apply_if_safe=True)
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
    result = agents.operator_assistant(question, uploaded_text=uploaded)
    return jsonify(result)


@app.route("/api/log")
def api_log():
    n = int(request.args.get("n", 12))
    return jsonify({"events": agents.EVENT_LOG[-n:]})


@app.route("/api/mode", methods=["POST"])
def api_mode():
    """Switch LLM mode (MOCK / LIVE / REPLAY) from the UI."""
    m = (request.json or {}).get("mode", "MOCK").upper()
    if m in ("MOCK", "LIVE", "REPLAY"):
        agents.LLM_CONFIG["mode"] = m
        return jsonify({"mode": m})
    return jsonify({"error": "invalid mode"}), 400


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
