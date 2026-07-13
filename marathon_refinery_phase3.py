# ============================================================================
#  MARATHON PETROLEUM REFINERY OPTIMIZATION ADVISOR
#  PHASE 3 (COMPLETE)  -  The Multi-Agent Advisory Layer + Operator Assistant
# ----------------------------------------------------------------------------
#  Builds the "brain" on top of the Phase 2 simulator. Four agents:
#     1. Monitoring     - diagnoses plant state (reads S+O)
#     2. Optimization   - proposes knob moves (moves K, grounded via tools)
#     3. Safety         - approve/reject/counter (guards L)
#     4. Operator Assistant - conversational what-if / manual Q&A (PREVIEW-ONLY)
#
#  Plus: orchestrator (pipeline + counter-loops), fault event logger,
#        manual-control->Safety path, and a headless test harness.
#
#  *** BUILT KEYLESS ***  Three LLM modes:
#     MOCK   - canned structured responses (no API). Tests ALL plumbing now.
#     LIVE   - real Groq calls (flip when key arrives; prompts already written)
#     REPLAY - cached rehearsal responses (demo-safe, no API dependency)
#
#  COLAB:
#     !pip install groq        # only needed for LIVE mode
#     (Phase 2 file must be in the same runtime / importable.)
# ============================================================================

import os
import json
import time
import re
from copy import deepcopy
from datetime import datetime

# Import the Phase 2 world + tools (already validated).
from marathon_refinery_sim_phase2 import (
    CFG, PLANT, run_refinery, step, clear_faults,
    trigger_scenario_A, trigger_scenario_B, inject_fault, SANDBOX_FAULTS,
    get_refinery_state, simulate_proposal, check_all_limits,
    baseline_knobs, clamp_knob,
)

# ============================================================================
#  STEP 1  -  THE call_llm() WRAPPER  (MOCK / LIVE / REPLAY + hardening)
# ----------------------------------------------------------------------------
#  Every agent call goes through here. One place for: mode switching, JSON
#  enforcement, retry, timeout, and graceful degradation. The always-running
#  loop can never crash on a bad LLM response.
# ============================================================================

LLM_CONFIG = {
    "mode": "MOCK",                 # "MOCK" | "LIVE" | "REPLAY"
    "model": "meta-llama/llama-4-scout-17b-16e-instruct",   # Groq model (used in LIVE)
    "temperature": 0.2,             # low = consistent, non-creative reasoning
    "max_tokens": 1024,
    "timeout_s": 30,
    "max_retries": 1,               # one retry on parse/network failure
    "api_key_env": "GROQ_API_KEY",  # read key from this env var (never hard-code)
    # --- rate-limit handling (free-tier tokens-per-minute) ---
    "pace_seconds": 3,              # wait this long BEFORE each LIVE call (spreads bursts)
    "rate_limit_cooldown_s": 20,    # on a RateLimitError, wait this long then retry
    "rate_limit_retries": 3,        # how many cooldown-retries before giving up
}

# Populated by register_mock() below; keyed by agent name.
_MOCK_RESPONDERS = {}
# Cache of real responses captured in LIVE for later REPLAY (demo-safe).
_REPLAY_CACHE = {}
_LAST_GOOD = {}     # last valid parsed output per agent (graceful fallback)


def register_mock(agent_name, responder_fn):
    """Register a function(context_dict) -> dict that returns a canned,
    correctly-SHAPED response for an agent. Lets us test all plumbing keyless."""
    _MOCK_RESPONDERS[agent_name] = responder_fn


def _extract_json(text):
    """Pull a JSON object out of an LLM text response. Handles ```json fences
    and leading/trailing prose. Raises ValueError if nothing parseable."""
    if text is None:
        raise ValueError("empty LLM response")
    # strip code fences
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(),
                     flags=re.MULTILINE).strip()
    # try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # fall back: grab the outermost {...}
    m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise ValueError(f"no JSON found in response: {text[:200]}")


def _get_api_key():
    """Fetch the Groq key. Tries Colab Secrets first (userdata), then a plain
    environment variable. Colab's 'Secrets' tab does NOT populate os.environ
    automatically, so we must ask userdata explicitly."""
    try:
        from google.colab import userdata          # only exists inside Colab
        k = userdata.get(LLM_CONFIG["api_key_env"])
        if k:
            return k
    except Exception:                               # not in Colab, or no secret set
        pass
    return os.environ.get(LLM_CONFIG["api_key_env"])


def _call_groq_live(system_prompt, user_prompt, api_key_override=None):
    """Real Groq call. Only invoked in LIVE mode. Imported lazily so the
    module works without the groq package installed (MOCK/REPLAY).
    api_key_override: if given (e.g. a visitor's own pasted key from the
    dashboard), use it instead of the shared project key -- lets each
    browser session bring its own key without touching global state."""
    from groq import Groq
    key = api_key_override or _get_api_key()
    if not key:
        raise RuntimeError(
            f"No API key found. In Colab: add '{LLM_CONFIG['api_key_env']}' in the "
            f"Secrets tab (key icon, left sidebar) and enable notebook access. "
            f"Or set it as an env var, or switch LLM_CONFIG['mode'] to 'MOCK'.")
    client = Groq(api_key=key)
    resp = client.chat.completions.create(
        model=LLM_CONFIG["model"],
        temperature=LLM_CONFIG["temperature"],
        max_tokens=LLM_CONFIG["max_tokens"],
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}],
    )
    return resp.choices[0].message.content


def call_llm(agent_name, system_prompt, user_prompt, context, expect_json=True,
             session_ctx=None):
    """The single entry point for every agent's LLM interaction.

    agent_name  : identifies the agent (for mock routing, caching, fallback)
    system/user : the prompts (written now; used live later)
    context     : dict the MOCK responder reads to build a shaped reply
    expect_json : if True, response is parsed to a dict; else returned as text
    session_ctx : optional dict {"session_id", "mode", "api_key"} -- when
                  given (always the case from the multi-user dashboard),
                  its mode/key OVERRIDE the global LLM_CONFIG for THIS call
                  only, and fallback caches are kept per-session so two
                  browser tabs never see each other's degraded/cached state.
                  When None (e.g. the standalone Colab test harness), the
                  original global-LLM_CONFIG behavior is used unchanged.

    Returns: parsed dict (expect_json) or str. On total failure, returns the
    agent's last-good output, or a minimal safe stub - never raises upward."""
    ctx = session_ctx or {}
    mode = ctx.get("mode", LLM_CONFIG["mode"])
    api_key_override = ctx.get("api_key")
    # per-session cache namespace -- falls back to the shared global cache
    # when no session_id is given, preserving old single-user behavior.
    sid = ctx.get("session_id", "_global")
    cache_key = f"{sid}::{agent_name}"

    try:
        if mode == "MOCK":
            if agent_name not in _MOCK_RESPONDERS:
                raise RuntimeError(f"no mock responder for '{agent_name}'")
            out = _MOCK_RESPONDERS[agent_name](context)
            # mocks return dicts (json-mode) or strings (chat-mode) directly
            result = out

        elif mode == "REPLAY":
            if cache_key not in _REPLAY_CACHE:
                raise RuntimeError(f"no replay cache for '{agent_name}'")
            raw = _REPLAY_CACHE[cache_key]
            result = _extract_json(raw) if expect_json else raw

        elif mode == "LIVE":
            last_err = None
            # Pacing: space calls out so bursts stay under the per-minute
            # token limit. Configurable via LLM_CONFIG["pace_seconds"].
            pace = LLM_CONFIG.get("pace_seconds", 0)
            if pace:
                time.sleep(pace)
            for attempt in range(LLM_CONFIG["max_retries"] + 1):
                try:
                    nudge = ("" if attempt == 0 else
                             "\n\nIMPORTANT: return ONLY valid JSON, no prose.")
                    raw = _call_groq_live(system_prompt, user_prompt + nudge,
                                          api_key_override=api_key_override)
                    _REPLAY_CACHE[cache_key] = raw     # capture for REPLAY
                    result = _extract_json(raw) if expect_json else raw
                    break
                except Exception as e:               # noqa: BLE001
                    last_err = e
                    # A rate limit is temporary, not a real failure: wait
                    # the configured cooldown and retry a few extra times
                    # before giving up to the fallback stub.
                    if type(e).__name__ == "RateLimitError":
                        cooldown = LLM_CONFIG.get("rate_limit_cooldown_s", 20)
                        for _ in range(LLM_CONFIG.get("rate_limit_retries", 3)):
                            time.sleep(cooldown)
                            try:
                                raw = _call_groq_live(system_prompt, user_prompt,
                                                      api_key_override=api_key_override)
                                _REPLAY_CACHE[cache_key] = raw
                                result = _extract_json(raw) if expect_json else raw
                                last_err = None
                                break
                            except Exception as e2:  # noqa: BLE001
                                last_err = e2
                        if last_err is None:
                            break
                    time.sleep(0.5)
            else:
                raise last_err
            if last_err is not None:
                raise last_err
        else:
            raise ValueError(f"unknown LLM mode '{mode}'")

        _LAST_GOOD[cache_key] = result               # remember good output
        return result

    except Exception as e:                           # noqa: BLE001 - graceful degrade
        # 1) last-good output for this agent, if any
        if cache_key in _LAST_GOOD:
            fb = deepcopy(_LAST_GOOD[cache_key])
            if isinstance(fb, dict):
                fb["_degraded"] = f"reused last-good ({type(e).__name__})"
            return fb
        # 2) rule-based stub (defined per-agent below); guarantees the loop lives
        stub = _RULE_STUBS.get(agent_name)
        if stub:
            s = stub(context)
            if isinstance(s, dict):
                s["_degraded"] = f"rule-based stub ({type(e).__name__})"
            return s
        # 3) absolute last resort
        return {"_degraded": f"hard fallback ({type(e).__name__})",
                "error": str(e)[:160]}


# Rule-based stubs: deterministic fallbacks that keep the system correct even
# with zero LLM. Populated after the agents are defined (see STEP 2 end).
_RULE_STUBS = {}


# ============================================================================
#  STEP 2  -  THE THREE PIPELINE AGENTS
# ----------------------------------------------------------------------------
#  Each agent = a system prompt (written now, used in LIVE) + a builder that
#  assembles the user prompt from state + a MOCK responder that returns a
#  correctly-shaped reply so we can test the whole pipeline keyless.
#
#  Reasoning is a STRUCTURED object citing tool numbers (your no-ambiguity
#  requirement): every verdict traces to specific values.
# ============================================================================

# ---- helper: compact the big state dict into what an agent needs to see ----
def _state_digest(s):
    """A small, LLM-friendly summary of the plant state (keeps prompts lean)."""
    return {
        "tick": s.get("tick"),
        "active_faults": s.get("active_faults", []),
        "margin_usd_bbl": round(s["margin_usd_bbl"], 2),
        "margin_usd_day": round(s["margin_usd_day"], 0),
        "slate": {"gasoline_pct": round(s["slate_gasoline_pct"], 1),
                  "distillate_pct": round(s["slate_distillate_pct"], 1),
                  "jet_pct": round(s["slate_jet_pct"], 1)},
        "pool_octane_RON": round(s["pool_octane_RON"], 2),
        "octane_floor": CFG["specs"]["gasoline_octane_floor_RON"],
        "diesel_sulfur_ppm_equiv": round(s["diesel_sulfur_wt_pct"] * 1e4, 1),
        "sulfur_cap_ppm": round(CFG["specs"]["diesel_sulfur_cap_wt_pct"] * 1e4, 0),
        "fcc_coke_pct": round(s["coke_make_pct"], 2),
        "fcc_coke_limit": CFG["limits"]["fcc_coke_make_max_pct"],
        "h2_demand_MMscfd": round(s["h2_demand_scfd"] / 1e6, 2),
        "h2_available_MMscfd": round(s["h2_available_scfd"] / 1e6, 2),
        "feed_pool_bpd": round(s["feed_pool_bpd"], 0),
        "fcc_feed_bpd": round(s["fcc_feed_actual_bpd"], 0),
        "hc_feed_bpd": round(s["hc_feed_actual_bpd"], 0),
        "economics": {"gasoline_crack": round(s["economics"]["gasoline_crack_usd_bbl"], 1),
                      "diesel_crack": round(s["economics"]["diesel_crack_usd_bbl"], 1),
                      "energy_cost": round(s["economics"]["energy_cost_usd_mmbtu"], 2)},
        "knobs": {k: round(v, 4) for k, v in s["knobs"].items()},
    }


# ---------------------------------------------------------------- MONITORING
MONITORING_SYSTEM_PROMPT = """You are the MONITORING AGENT for a Marathon Petroleum Gulf Coast refinery advisory system.
Your ONLY job is to DIAGNOSE the current plant state. You do NOT propose changes (that is the Optimization Agent's job).

You are given a digest of the live plant state including margin, product slate, product-spec status (octane floor, sulfur cap), unit constraints (FCC coke, H2 balance), the feed-pool split, and today's economics.

PAY CLOSE ATTENTION TO THE ECONOMICS BLOCK. Compare gasoline_crack and diesel_crack against each other and against their normal baseline levels (gasoline_crack ~27, diesel_crack ~37 under normal conditions). A crack spread that is significantly ABOVE its normal level (roughly 20% or more) means that product is unusually valuable right now and the plant may be leaving money on the table if it is not maximizing that product - this is an OPPORTUNITY, not a normal state, even if every hard limit currently passes. Do not classify the plant as "normal" when a crack spread is significantly elevated versus baseline.

Identify:
- Is the plant NORMAL, sitting on an OPPORTUNITY (money being left on the table), or facing a PROBLEM (a spec/limit violated or at risk)?
- Which single constraint or opportunity is most important right now (the "binding" one)?
- Any product spec already violated (octane < floor, sulfur > cap) or unit limit exceeded.

Respond with ONLY a JSON object of this exact shape:
{
  "status": "normal" | "opportunity" | "problem",
  "observations": [{"variable": "<name>", "value": <num>, "vs_target": "<short>"}],
  "binding_constraint": "<name or null>",
  "headline": "<one plain-English sentence>",
  "reasoning": {"observed": "<what you see in numbers>", "why_it_matters": "<impact>", "conclusion": "<the diagnosis>"}
}
You MUST cite actual numbers from the provided state digest in every observation and in your reasoning (e.g. "pool octane 89.4 vs floor 87" or "gasoline_crack 39 vs normal ~27, a 44% premium"). Never make a claim without the number that supports it. No prose outside the JSON."""

def _build_monitoring_prompt(snapshot):
    d = _state_digest(snapshot)
    return (f"Current plant state digest:\n{json.dumps(d, indent=2)}\n\n"
            f"Diagnose the plant. Return the JSON.")

def monitoring_agent(snapshot, session_ctx=None):
    """Agent 1. Reads snapshot -> diagnosis JSON."""
    user = _build_monitoring_prompt(snapshot)
    return call_llm("monitoring", MONITORING_SYSTEM_PROMPT, user,
                    context={"snapshot": snapshot}, expect_json=True,
                    session_ctx=session_ctx)


# ------------------------------------------------------------- OPTIMIZATION
OPTIMIZATION_SYSTEM_PROMPT = """You are the OPTIMIZATION AGENT for a Marathon Petroleum refinery advisory system.
Given the Monitoring Agent's diagnosis and the plant state, propose a COORDINATED set of knob changes that MAXIMIZES refinery margin while respecting the physics couplings.

The LEAD knob is hydrocracker_conversion (0.60-0.98): HIGH -> more gasoline, LOW -> more diesel.
Other knobs: cdu_throughput_bpd, cdu_furnace_temp_C, vdu_severity, fcc_feed_bpd, fcc_severity, reformer_feed_bpd, reformer_severity, hydrocracker_feed_bpd.

KEY COUPLINGS to reason about:
- FCC and Hydrocracker compete for a finite VGO/AGO feed pool (route a barrel to FCC->gasoline, or to Hydrocracker->diesel).
- The Reformer PRODUCES hydrogen; the Hydrocracker CONSUMES it. Raise reformer severity to free up H2 for more hydrocracking.
- Raising FCC or Reformer severity lifts octane but raises coke/energy and shrinks volume.
- Every gasoline stream pools to a volume-weighted octane that must stay >= the floor.

BE AMBITIOUS, NOT CAUTIOUS. Your job is to find the move that captures the MOST margin available given today's economics - do not self-limit to a small, safe-feeling nudge. Checking whether a move is safe is EXCLUSIVELY the Safety Agent's job, not yours - it will run check_all_limits() on your proposal and reject or counter it if it is unsafe. If the diagnosis flags an OPPORTUNITY (e.g. an elevated crack spread), propose a move that aggressively captures it: increase relevant feed rates AND severities together, not just one small knob change. A proposal that is rejected and needs a counter-round is a NORMAL and EXPECTED outcome of this process, not a failure on your part - propose your best, most ambitious idea first.

Your predicted margin delta MUST be positive (a real improvement) - if your first idea does not improve margin, reconsider it before proposing.

You MUST ground your proposal: state the knob changes; the system will run simulate_proposal() and give you the TRUE predicted margin delta. If a prior attempt was rejected by Safety, you will be given counter_guidance - respect it, and propose the least-conservative change that satisfies that guidance (do not over-correct to something overly timid).

Respond with ONLY this JSON:
{
  "proposed_changes": {"<knob>": <value>, ...},
  "reasoning": {"goal": "<what you're optimizing for and why>", "which_knobs_and_why": "<per-knob rationale>", "couplings_considered": "<which couplings and how>", "tradeoff": "<what you give up>", "conclusion": "<the move in one line>"}
}
You MUST reference actual numbers from the state digest (current margin, cracks, feed-pool split, H2 balance) in your reasoning. No prose outside the JSON."""

def _build_optimization_prompt(snapshot, diagnosis, counter_guidance=None):
    d = _state_digest(snapshot)
    parts = [f"Plant state digest:\n{json.dumps(d, indent=2)}",
             f"\nMonitoring diagnosis:\n{json.dumps(diagnosis, indent=2)}"]
    if counter_guidance:
        parts.append(f"\nSafety REJECTED your previous proposal. Counter guidance "
                     f"you MUST respect:\n{counter_guidance}")
    parts.append("\nPropose knob changes. Return the JSON.")
    return "\n".join(parts)

def optimization_agent(snapshot, diagnosis, counter_guidance=None, session_ctx=None):
    """Agent 2. Proposes knobs, then GROUNDS via simulate_proposal().
    Returns the proposal enriched with the tool's true predicted numbers."""
    user = _build_optimization_prompt(snapshot, diagnosis, counter_guidance)
    proposal = call_llm("optimization", OPTIMIZATION_SYSTEM_PROMPT, user,
                        context={"snapshot": snapshot, "diagnosis": diagnosis,
                                 "counter_guidance": counter_guidance},
                        expect_json=True, session_ctx=session_ctx)
    # --- TOOL GROUNDING: numbers come from simulate_proposal(), never invented
    changes = proposal.get("proposed_changes", {})
    try:
        predicted = simulate_proposal(changes, snapshot)
        proposal["predicted_margin_delta_usd_day"] = round(
            predicted["margin_delta_usd_day"], 0)
        proposal["predicted_state"] = predicted        # full state for Safety
        proposal["predicted_summary"] = {
            "margin_usd_bbl": round(predicted["margin_usd_bbl"], 2),
            "pool_octane_RON": round(predicted["pool_octane_RON"], 2),
            "fcc_coke_pct": round(predicted["coke_make_pct"], 2),
            "h2_demand_MMscfd": round(predicted["h2_demand_scfd"] / 1e6, 2),
            "h2_available_MMscfd": round(predicted["h2_available_scfd"] / 1e6, 2)}
    except Exception as e:                              # bad knob name etc.
        proposal["_tool_error"] = str(e)[:160]
        proposal["predicted_state"] = deepcopy(snapshot)
        proposal["predicted_margin_delta_usd_day"] = 0
    return proposal


# -------------------------------------------------------------------- SAFETY
SAFETY_SYSTEM_PROMPT = """You are the SAFETY & COMPLIANCE AGENT for a Marathon Petroleum refinery advisory system.
You are the last line of defense. Given the Optimization Agent's proposal and its PREDICTED plant state, you decide: APPROVE, REJECT, or COUNTER.

The system has already run check_all_limits() on the predicted state and given you the pass/fail for every hard limit and product spec (furnace temp, throughput, severities, FCC coke, H2 balance, pool octane floor, diesel sulfur cap). You must base your verdict on those hard results - never override a failing check.

Rules (check BOTH, in this order):
1. FIRST check the predicted_margin_delta_usd_day field. If it is NEGATIVE (the move loses money), you must REJECT regardless of whether limits pass, citing the negative margin as the reason - a proposal that loses money is never acceptable even if it is "safe."
2. THEN check the limit results. If ALL checks pass AND margin is positive -> APPROVE. If any check FAILS -> REJECT (or COUNTER if you can name a specific safe adjustment).

When you reject/counter, cite EXACTLY which condition failed (negative margin, or which limit, with its value vs bound), and give concrete counter_guidance the Optimization Agent can act on. When giving counter_guidance for an over-aggressive proposal, ask for a SPECIFIC smaller adjustment (e.g. "reduce fcc_severity increase to about half of what you proposed") rather than a vague "be safer" - the goal is to preserve as much of the captured margin as possible while fixing the violation, not to retreat to doing nothing.

Respond with ONLY this JSON:
{
  "verdict": "APPROVE" | "REJECT" | "COUNTER",
  "binding_limits": [{"limit": "<name>", "value": <num>, "bound": <num>, "exceeded_by": <num>}],
  "counter_guidance": "<concrete instruction or null>",
  "reasoning": {"checked": "<what was verified>", "what_failed": "<failing checks with numbers, or 'none'>", "why": "<physical/commercial consequence>", "conclusion": "<the verdict in one line>"}
}
No prose outside the JSON."""

def _build_safety_prompt(proposal, limit_report):
    return (f"Proposed knob changes:\n{json.dumps(proposal.get('proposed_changes', {}), indent=2)}\n\n"
            f"Predicted margin delta: ${proposal.get('predicted_margin_delta_usd_day', 0):,.0f}/day\n"
            f"Predicted summary:\n{json.dumps(proposal.get('predicted_summary', {}), indent=2)}\n\n"
            f"check_all_limits() results on the predicted state:\n"
            f"{json.dumps(limit_report, indent=2)}\n\n"
            f"Issue your verdict. Return the JSON.")

def safety_agent(proposal, session_ctx=None):
    """Agent 3. Runs check_all_limits() on the predicted state, then verdicts."""
    predicted = proposal.get("predicted_state")
    limit_report = check_all_limits(predicted)
    user = _build_safety_prompt(proposal, limit_report)
    verdict = call_llm("safety", SAFETY_SYSTEM_PROMPT, user,
                       context={"proposal": proposal, "limit_report": limit_report},
                       expect_json=True, session_ctx=session_ctx)
    verdict["_limit_report"] = limit_report   # attach ground truth for the log
    return verdict


# ============================================================================
#  RULE-BASED STUBS  (graceful degradation - correct even with zero LLM)
# ============================================================================

def _stub_monitoring(context):
    s = context["snapshot"]
    rpt = check_all_limits(s)
    failed = [c for c in rpt["checks"] if not c["ok"]]
    if failed:
        return {"status": "problem",
                "observations": [{"variable": c["limit"], "value": c["value"],
                                  "vs_target": f"limit {c['bound']}"} for c in failed],
                "binding_constraint": failed[0]["limit"],
                "headline": f"{failed[0]['limit']} out of bounds",
                "reasoning": {"observed": "limit check failed", "why_it_matters":
                              "spec/limit breach", "conclusion": "problem state"}}
    return {"status": "normal", "observations": [],
            "binding_constraint": None,
            "headline": f"Plant nominal at ${s['margin_usd_bbl']:.2f}/bbl",
            "reasoning": {"observed": "all checks pass", "why_it_matters":
                          "stable", "conclusion": "monitor only"}}

def _stub_optimization(context):
    # deterministic fallback: nudge hydrocracker conversion toward the more
    # valuable product per current cracks (uses the lead knob, safely small).
    s = context["snapshot"]
    e = s["economics"]
    conv = s["knobs"]["hydrocracker_conversion"]
    target = min(conv + 0.03, 0.90) if e["gasoline_crack_usd_bbl"] >= \
        e["diesel_crack_usd_bbl"] else max(conv - 0.03, 0.65)
    return {"proposed_changes": {"hydrocracker_conversion": round(target, 3)},
            "reasoning": {"goal": "rule-based margin nudge via lead knob",
                          "which_knobs_and_why": "hydrocracker conversion only",
                          "couplings_considered": "gasoline vs diesel crack",
                          "tradeoff": "conservative single-knob move",
                          "conclusion": "small safe conversion adjustment"}}

def _stub_safety(context):
    rpt = context["limit_report"]
    failed = [c for c in rpt["checks"] if not c["ok"]]
    if not failed:
        return {"verdict": "APPROVE", "binding_limits": [], "counter_guidance": None,
                "reasoning": {"checked": "all limits", "what_failed": "none",
                              "why": "within all bounds", "conclusion": "approve"}}
    bl = [{"limit": c["limit"], "value": c["value"], "bound": c["bound"],
           "exceeded_by": round(abs(c["value"] - c["bound"]), 4)} for c in failed]
    return {"verdict": "REJECT", "binding_limits": bl,
            "counter_guidance": f"resolve {failed[0]['limit']}",
            "reasoning": {"checked": "all limits", "what_failed":
                          str([c['limit'] for c in failed]), "why": "hard breach",
                          "conclusion": "reject"}}

_RULE_STUBS.update({"monitoring": _stub_monitoring,
                    "optimization": _stub_optimization,
                    "safety": _stub_safety})


# ============================================================================
#  STEP 5 (built early - needed by logger)  -  FAULT EVENT LOGGER
# ----------------------------------------------------------------------------
#  Simple audit trail: every fault/scenario/manual-change/agent-verdict.
#  Doubles as "log-as-memory" the Operator Assistant can reference.
# ============================================================================

EVENT_LOG = []
EVENT_LOG_MAX = 500   # keep last N events (prevents unbounded growth on long runs)

def log_event(event_type, details, state=None):
    """Append an event. event_type: fault|scenario|manual_change|agent_cycle|verdict"""
    entry = {"timestamp": datetime.now().isoformat(timespec="seconds"),
             "tick": (state or PLANT.get("state") or {}).get("tick"),
             "event_type": event_type, "details": details}
    if state is not None:
        entry["margin_usd_bbl"] = round(state["margin_usd_bbl"], 2)
        rpt = check_all_limits(state)
        entry["binding_limits"] = [c["limit"] for c in rpt["checks"] if not c["ok"]]
    EVENT_LOG.append(entry)
    if len(EVENT_LOG) > EVENT_LOG_MAX:      # prune oldest, keep memory bounded
        del EVENT_LOG[:-EVENT_LOG_MAX]
    return entry

def log_summary(n=None):
    """Human-readable recent log (for the assistant's memory + demo panel)."""
    rows = EVENT_LOG[-n:] if n else EVENT_LOG
    return "\n".join(
        f"[t{e.get('tick')}] {e['event_type']}: {e['details']}"
        + (f" | margin ${e['margin_usd_bbl']}/bbl" if 'margin_usd_bbl' in e else "")
        + (f" | binds {e['binding_limits']}" if e.get('binding_limits') else "")
        for e in rows) or "(no events logged yet)"


# ============================================================================
#  STEP 3  -  THE ORCHESTRATOR  (pipeline + counter-loops + graceful exhaust)
# ----------------------------------------------------------------------------
#  Monitor -> Optimize -> Safety, with up to MAX_LOOPS counter-proposal
#  rounds. Reasons against an immutable snapshot (audit #3) while the live
#  plant keeps ticking. Returns a single recommendation card.
# ============================================================================

# max_loops=2 is DELIBERATE: both locked demo scenarios are reject-then-counter
# (2 attempts to reach approval). Setting this to 1 would make Scenario A and B
# conclude "HOLD" after one rejection - breaking the headline demos. Configurable
# 1-3 for other runs, but 2 is the correct default here.
ORCH_CONFIG = {"max_loops": 2}   # counter-proposal rounds (config 1-3; default 2)

def run_advisory_cycle(snapshot=None, verbose=False, session_ctx=None):
    """One full advisory pass over an immutable snapshot. Returns a card:
       {status, monitoring, optimization, safety, applied_changes, loops, outcome}
    session_ctx: optional per-browser-session {"session_id","mode","api_key"}
    -- see call_llm() docstring. None = old global-LLM_CONFIG behavior."""
    if snapshot is None:
        snapshot = get_refinery_state()          # immutable deep copy (audit #3)

    card = {"tick": snapshot.get("tick"), "monitoring": None,
            "attempts": [], "outcome": None, "final_changes": {},
            "loops": 0}

    # --- MONITOR ---
    diagnosis = monitoring_agent(snapshot, session_ctx=session_ctx)
    card["monitoring"] = diagnosis
    if verbose:
        degraded = diagnosis.get("_degraded")
        flag = f"  [DEGRADED: {degraded}]" if degraded else ""
        print(f"  [MONITOR] {diagnosis.get('headline')}  "
              f"(status={diagnosis.get('status')}){flag}")

    # --- OPTIMIZE -> SAFETY loop ---
    counter_guidance = None
    for loop in range(ORCH_CONFIG["max_loops"] + 1):
        card["loops"] = loop + 1
        proposal = optimization_agent(snapshot, diagnosis, counter_guidance,
                                      session_ctx=session_ctx)
        verdict = safety_agent(proposal, session_ctx=session_ctx)
        attempt = {"loop": loop + 1,
                   "proposed_changes": proposal.get("proposed_changes", {}),
                   "predicted_margin_delta_usd_day":
                       proposal.get("predicted_margin_delta_usd_day"),
                   "verdict": verdict.get("verdict"),
                   "binding_limits": verdict.get("binding_limits", []),
                   "opt_reasoning": proposal.get("reasoning"),
                   "safety_reasoning": verdict.get("reasoning")}
        card["attempts"].append(attempt)
        if verbose:
            opt_flag = f"  [DEGRADED: {proposal.get('_degraded')}]" if proposal.get("_degraded") else ""
            safety_flag = f"  [DEGRADED: {verdict.get('_degraded')}]" if verdict.get("_degraded") else ""
            print(f"  [OPTIMIZE #{loop+1}] {proposal.get('proposed_changes')} "
                  f"-> margin {proposal.get('predicted_margin_delta_usd_day'):+,.0f} $/day{opt_flag}")
            print(f"  [SAFETY   #{loop+1}] {verdict.get('verdict')}  "
                  f"binds={[b['limit'] for b in verdict.get('binding_limits', [])]}{safety_flag}")

        if verdict.get("verdict") == "APPROVE":
            card["outcome"] = "APPROVED"
            card["final_changes"] = proposal.get("proposed_changes", {})
            break
        counter_guidance = verdict.get("counter_guidance")
        if loop >= ORCH_CONFIG["max_loops"]:
            # graceful exhaustion - a correct, trust-building behavior
            card["outcome"] = "HOLD_NO_SAFE_IMPROVEMENT"
            card["final_changes"] = {}
            break

    log_event("agent_cycle",
              f"outcome={card['outcome']} loops={card['loops']} "
              f"changes={card['final_changes']}", snapshot)
    return card


def apply_recommendation(card, plant=PLANT):
    """Apply an APPROVED card's changes to the LIVE plant (operator accepts)."""
    if card["outcome"] != "APPROVED" or not card["final_changes"]:
        return {"applied": False, "reason": card["outcome"]}
    for name, val in card["final_changes"].items():
        plant["knobs"][name] = clamp_knob(name, val)
    st = step(plant)
    log_event("applied", f"applied {card['final_changes']}", st)
    return {"applied": True, "new_margin_usd_bbl": round(st["margin_usd_bbl"], 2)}


# ============================================================================
#  STEP 4  -  MANUAL CONTROL -> SAFETY PATH  (decisions B & C)
# ----------------------------------------------------------------------------
#  When an OPERATOR changes a value directly, it still passes through Safety.
#  Nothing bypasses Safety. Returns Safety's verdict; only applies if safe.
# ============================================================================

def operator_manual_change(knob_changes, plant=PLANT, apply_if_safe=True, session_ctx=None):
    """Operator drags a slider / sets a value. Route through Safety first."""
    snapshot = get_refinery_state(plant)
    # build a proposal shell so we can reuse the Safety agent
    predicted = simulate_proposal(knob_changes, snapshot)
    proposal = {"proposed_changes": knob_changes,
                "predicted_state": predicted,
                "predicted_margin_delta_usd_day": round(predicted["margin_delta_usd_day"], 0),
                "predicted_summary": {
                    "margin_usd_bbl": round(predicted["margin_usd_bbl"], 2),
                    "pool_octane_RON": round(predicted["pool_octane_RON"], 2),
                    "fcc_coke_pct": round(predicted["coke_make_pct"], 2),
                    "h2_demand_MMscfd": round(predicted["h2_demand_scfd"] / 1e6, 2),
                    "h2_available_MMscfd": round(predicted["h2_available_scfd"] / 1e6, 2)}}
    verdict = safety_agent(proposal, session_ctx=session_ctx)
    log_event("manual_change",
              f"operator set {knob_changes} -> Safety {verdict.get('verdict')}",
              snapshot)
    applied = False
    if apply_if_safe and verdict.get("verdict") == "APPROVE":
        for name, val in knob_changes.items():
            plant["knobs"][name] = clamp_knob(name, val)
        step(plant)
        applied = True
    return {"verdict": verdict, "applied": applied,
            "predicted_margin_delta_usd_day": proposal["predicted_margin_delta_usd_day"]}


# ============================================================================
#  STEP 6  -  THE OPERATOR ASSISTANT  (Agent 4, conversational, PREVIEW-ONLY)
# ----------------------------------------------------------------------------
#  Consolidates: manual Q&A (user manual), what-if queries (simulate_proposal),
#  and text-file Q&A. NEVER mutates the live plant (decision B).
# ============================================================================

# Loaded from the user manual file (written separately). Kept short here; the
# real manual text is injected at runtime so the assistant can answer from it.
USER_MANUAL_TEXT = ""   # set via load_user_manual()

def load_user_manual(text):
    global USER_MANUAL_TEXT
    USER_MANUAL_TEXT = text

ASSISTANT_SYSTEM_PROMPT = """You are the OPERATOR ASSISTANT for a Marathon Petroleum refinery advisory system.
You help the operator UNDERSTAND the plant. You are PREVIEW-ONLY: you never change the live plant; you explain and predict.

You can:
1. Answer questions about how the units and variables work, using the USER MANUAL provided.
2. Answer "what-if" questions: when the operator asks what happens if a knob changes, the system runs simulate_proposal() and gives you the TRUE predicted result - explain it in plain language, citing the predicted margin, octane, coke, and H2 numbers, and note any limit that would be breached.
3. Answer questions grounded in an uploaded TEXT document and/or the synthetic operating-data summary, when provided.
4. Reference the recent EVENT LOG if the operator asks what has happened.

Always ground what-if answers in the provided predicted numbers - never guess. Be concise, correct, and operator-friendly. If a change would breach a limit, say so clearly."""

def _parse_whatif(question):
    """Very small NL->knob parser for what-if queries. Returns {knob: value}
    or None.

    NOTE: this is a deliberately simple keyword+number matcher, sufficient for
    MOCK-mode testing and common demo phrasings. In LIVE mode the actual LLM
    handles nuanced/ambiguous phrasing; this regex path is a lightweight
    convenience, not the primary parser. Not intended to be robust NLP."""
    q = question.lower()
    knob_aliases = {
        "hydrocracker_conversion": ["hydrocracker conversion", "conversion", "hydrocracker"],
        "cdu_furnace_temp_C": ["furnace", "furnace temp", "cdu temp"],
        "fcc_severity": ["fcc severity", "cat cracker severity"],
        "fcc_feed_bpd": ["fcc feed"],
        "reformer_severity": ["reformer severity"],
        "cdu_throughput_bpd": ["throughput", "crude rate", "cdu throughput"],
        "vdu_severity": ["vacuum severity", "vdu severity"],
    }
    nums = re.findall(r"[-+]?\d*\.?\d+", q)
    if not nums:
        return None
    val = float(nums[0])
    for knob, aliases in knob_aliases.items():
        if any(a in q for a in aliases):
            return {knob: clamp_knob(knob, val)}
    return None

def _relevant_manual_excerpt(question, budget=5000):
    """Pick the manual content most relevant to THIS question, instead of a
    blind first-N-characters truncation. With three manuals combined into
    ~51K chars, a flat slice would only ever show the start of the first
    file -- meaning a question about a later section would never see it,
    regardless of any rate-limit budget. This is NOT retrieval/embeddings
    (we deliberately stayed away from that complexity) -- it's a simple,
    dependency-free keyword-overlap heuristic: split the manual into
    paragraphs, score each by how many question-words it contains, and
    concatenate the top-scoring ones up to the character budget. Falls back
    to a plain leading slice if the question shares no words with the text
    at all (e.g. a very generic greeting)."""
    if not USER_MANUAL_TEXT:
        return ""
    words = set(re.findall(r"[a-z0-9]{3,}", question.lower()))
    if not words:
        return USER_MANUAL_TEXT[:budget]

    paragraphs = [p for p in re.split(r"\n\s*\n", USER_MANUAL_TEXT) if p.strip()]
    scored = []
    for i, p in enumerate(paragraphs):
        p_words = set(re.findall(r"[a-z0-9]{3,}", p.lower()))
        score = len(words & p_words)
        if score > 0:
            scored.append((score, i, p))

    if not scored:
        return USER_MANUAL_TEXT[:budget]   # no overlap -- safe fallback

    scored.sort(key=lambda x: (-x[0], x[1]))   # best matches first
    picked, total = [], 0
    for score, idx, p in scored:
        if total + len(p) > budget and picked:
            break
        picked.append((idx, p))
        total += len(p)
        if total >= budget:
            break
    picked.sort(key=lambda x: x[0])             # restore original reading order
    return "\n\n".join(p for _, p in picked)


def operator_assistant(question, uploaded_text=None, plant=PLANT, session_ctx=None):
    """Agent 4. Conversational, preview-only. Routes what-if queries through
    simulate_proposal(); answers manual/data/file questions from context."""
    snapshot = get_refinery_state(plant)
    whatif = _parse_whatif(question)
    whatif_result = None
    if whatif:
        pred = simulate_proposal(whatif, snapshot)
        rpt = check_all_limits(pred)
        breaches = [c for c in rpt["checks"] if not c["ok"]]
        whatif_result = {
            "change": whatif,
            "predicted_margin_delta_usd_day": round(pred["margin_delta_usd_day"], 0),
            "predicted_margin_usd_bbl": round(pred["margin_usd_bbl"], 2),
            "predicted_pool_octane_RON": round(pred["pool_octane_RON"], 2),
            "predicted_fcc_coke_pct": round(pred["coke_make_pct"], 2),
            "predicted_h2_demand_MMscfd": round(pred["h2_demand_scfd"] / 1e6, 2),
            "predicted_h2_available_MMscfd": round(pred["h2_available_scfd"] / 1e6, 2),
            "limit_breaches": [{"limit": c["limit"], "value": c["value"],
                                "bound": c["bound"]} for c in breaches]}

    # Assemble context for the LLM (in LIVE it writes the prose answer).
    context = {"question": question,
               "whatif_result": whatif_result,
               "state_digest": _state_digest(snapshot),
               "manual_excerpt": _relevant_manual_excerpt(question, budget=5000),
               "uploaded_text": (uploaded_text or "")[:3000],
               "recent_log": log_summary(n=8)}
    user = (f"Operator question: {question}\n\n"
            + (f"What-if tool result:\n{json.dumps(whatif_result, indent=2)}\n\n"
               if whatif_result else "")
            + (f"Uploaded document (excerpt):\n{context['uploaded_text']}\n\n"
               if uploaded_text else "")
            + f"Current state digest:\n{json.dumps(context['state_digest'], indent=2)}\n\n"
            + f"User manual (excerpt):\n{context['manual_excerpt']}\n\n"
            + f"Recent events:\n{context['recent_log']}\n\n"
            + "Answer the operator concisely and correctly.")
    answer = call_llm("assistant", ASSISTANT_SYSTEM_PROMPT, user,
                      context=context, expect_json=False, session_ctx=session_ctx)
    return {"answer": answer, "whatif_result": whatif_result}


# ---- assistant MOCK responder + stub (keyless testing) ----
def _mock_assistant(context):
    """Deterministic, correct assistant reply for MOCK/testing. In LIVE the
    real LLM writes nicer prose from the same grounded numbers."""
    q = context["question"]
    w = context.get("whatif_result")
    if w:
        parts = [f"If you apply {w['change']}:",
                 f"- margin would change by ${w['predicted_margin_delta_usd_day']:+,.0f}/day "
                 f"(to ${w['predicted_margin_usd_bbl']}/bbl)",
                 f"- pool octane -> {w['predicted_pool_octane_RON']} RON",
                 f"- FCC coke -> {w['predicted_fcc_coke_pct']}%",
                 f"- H2 demand {w['predicted_h2_demand_MMscfd']} vs "
                 f"{w['predicted_h2_available_MMscfd']} MMscfd available"]
        if w["limit_breaches"]:
            parts.append("WARNING - this would breach: "
                         + ", ".join(f"{b['limit']} ({b['value']} vs {b['bound']})"
                                     for b in w["limit_breaches"]))
        else:
            parts.append("All limits remain satisfied.")
        return "\n".join(parts)
    # non-whatif: echo that it would answer from manual/data (mock)
    return (f"[assistant/mock] I would answer '{q}' using the user manual, "
            f"the synthetic-data summary, and any uploaded text. "
            f"(Live mode generates the full natural-language answer.)")

def _stub_assistant(context):
    return "Assistant temporarily unavailable (LLM unreachable). " \
           "What-if numbers are still computed by the simulator tool."

register_mock("assistant", _mock_assistant)
_RULE_STUBS["assistant"] = _stub_assistant


# ============================================================================
#  MOCK RESPONDERS for the three pipeline agents (keyless plumbing tests)
# ----------------------------------------------------------------------------
#  These read the REAL tool outputs (check_all_limits etc.) and return a
#  correctly-shaped JSON reply - so the whole pipeline is exercised honestly,
#  just without natural-language flair. LIVE swaps in the real model.
# ============================================================================

def _mock_monitoring(context):
    return _stub_monitoring(context)   # the stub is already a correct diagnosis

# Known scenario fault names the mock optimizer recognizes. Guarded so a
# rename fails LOUDLY here rather than silently mis-routing (LLM2 point 2).
# NOTE: this whole function is MOCK-ONLY scaffolding - in LIVE mode the real
# LLM optimizer reads economics and decides for itself; this is discarded.
_MOCK_KNOWN_SCENARIOS = {"scenario_A_gasoline_opportunity", "scenario_B_diesel_coldsnap"}

def _mock_optimization(context):
    """Mock optimizer (MOCK-ONLY, replaced entirely in LIVE): react with a
    sensible coupling-aware move so the pipeline & both scenarios exercise
    realistically. Scenario detection keys off active_faults (robust)."""
    s = context["snapshot"]; diag = context["diagnosis"]
    cg = context.get("counter_guidance")
    k = s["knobs"]; faults = s.get("active_faults", [])
    # guard: if a scenario fault is active but unrecognized, fail loudly
    scen = [f for f in faults if f.startswith("scenario_")]
    for f in scen:
        if f not in _MOCK_KNOWN_SCENARIOS:
            raise RuntimeError(f"mock optimizer: unrecognized scenario '{f}' - "
                               f"update _MOCK_KNOWN_SCENARIOS / mock logic")
    changes = {}
    # Scenario A: gasoline opportunity -> push FCC for gasoline (needs counter)
    if "scenario_A_gasoline_opportunity" in faults:
        sev_bump = 0.05 if cg else 0.17          # counter -> gentler
        changes = {"fcc_feed_bpd": clamp_knob("fcc_feed_bpd", k["fcc_feed_bpd"] + 12_000),
                   "fcc_severity": clamp_knob("fcc_severity", k["fcc_severity"] + sev_bump)}
    # Scenario B: diesel spike -> more diesel, but safely (reject then counter)
    elif "scenario_B_diesel_coldsnap" in faults:
        if cg:   # Safety pushed back: use the elegant H2 counter
            changes = {"cdu_furnace_temp_C": 368.0, "reformer_severity": 0.80,
                       "hydrocracker_feed_bpd": 25_000,
                       "hydrocracker_conversion": 0.66, "fcc_feed_bpd": 50_000}
        else:    # tempting (unsafe) first move
            changes = {"cdu_furnace_temp_C": 374.0, "hydrocracker_conversion": 0.62,
                       "fcc_feed_bpd": clamp_knob("fcc_feed_bpd", k["fcc_feed_bpd"] - 15_000),
                       "hydrocracker_feed_bpd": clamp_knob("hydrocracker_feed_bpd",
                                                            k["hydrocracker_feed_bpd"] + 15_000)}
    else:
        return _stub_optimization(context)   # baseline & sandbox: gentle lead-knob nudge
    return {"proposed_changes": changes,
            "reasoning": {"goal": "mock coupling-aware move",
                          "which_knobs_and_why": str(list(changes)),
                          "couplings_considered": "feed rivalry / H2 balance",
                          "tradeoff": "coke or H2 headroom",
                          "conclusion": "mock proposal"}}

def _mock_safety(context):
    return _stub_safety(context)       # stub verdicts from real limit checks

register_mock("monitoring", _mock_monitoring)
register_mock("optimization", _mock_optimization)
register_mock("safety", _mock_safety)


# ============================================================================
#  STEP 7 (deferred to dashboard stage): text-file upload Q&A is already
#  supported by operator_assistant(uploaded_text=...). Nothing more needed
#  here - the dashboard just passes the uploaded text through.
# ============================================================================


# ============================================================================
#  STEP 8  -  HEADLESS TEST HARNESS
# ----------------------------------------------------------------------------
#  Exercises the WHOLE Phase 3 system in MOCK mode against baseline + both
#  locked scenarios + sandbox faults + assistant what-ifs + manual/Safety.
#  When the key arrives, set LLM_CONFIG["mode"]="LIVE" and re-run to tune.
# ============================================================================

def phase3_full_test():
    print("\n" + "#" * 70)
    print(f"#  PHASE 3 FULL TEST  (mode={LLM_CONFIG['mode']})")
    print("#" * 70)
    EVENT_LOG.clear()
    load_user_manual("Furnace temp raises middle-distillate cut but energy rises "
                     "non-linearly. Hydrocracker conversion is the lead knob: high "
                     "-> gasoline, low -> diesel. Reformer produces H2 the "
                     "hydrocracker consumes. Pool octane is a BOV volume-weighted "
                     "average that must stay >= 87.")

    # --- Baseline: expect NORMAL, an approved small optimization or a hold ---
    print("\n--- BASELINE ---")
    clear_faults()
    card = run_advisory_cycle(verbose=True)
    print(f"  OUTCOME: {card['outcome']}")

    # --- Scenario A: gasoline opportunity -> APPROVE-WITH-COUNTER ---
    print("\n--- SCENARIO A (gasoline opportunity) ---")
    clear_faults(); trigger_scenario_A()
    cardA = run_advisory_cycle(verbose=True)
    print(f"  OUTCOME: {cardA['outcome']}  (loops={cardA['loops']})")
    assert cardA["outcome"] == "APPROVED", "Scenario A should approve after counter"
    assert cardA["loops"] >= 2, "Scenario A should need a counter loop"
    print("  -> APPROVE-WITH-COUNTER confirmed")

    # --- Scenario B: diesel spike -> REJECT then safe COUNTER ---
    print("\n--- SCENARIO B (cold-snap diesel + tight H2) ---")
    clear_faults(); trigger_scenario_B()
    cardB = run_advisory_cycle(verbose=True)
    first = cardB["attempts"][0]
    print(f"  first attempt verdict: {first['verdict']} "
          f"binds={[b['limit'] for b in first['binding_limits']]}")
    print(f"  OUTCOME: {cardB['outcome']}  (loops={cardB['loops']})")
    assert first["verdict"] in ("REJECT", "COUNTER"), "Scenario B first move must be rejected"
    print("  -> REJECT-then-COUNTER confirmed")

    # --- Sandbox faults: pipeline runs cleanly on each ---
    print("\n--- SANDBOX FAULTS (pipeline robustness) ---")
    for fid in SANDBOX_FAULTS:
        clear_faults(); inject_fault(fid)
        c = run_advisory_cycle(verbose=False)
        print(f"  {fid:<28} monitor={c['monitoring']['status']:<11} "
              f"outcome={c['outcome']}")
    clear_faults()

    # --- Operator Assistant: what-if (preview-only) ---
    print("\n--- OPERATOR ASSISTANT (what-if, preview-only) ---")
    for q in ["What happens if I raise hydrocracker conversion to 0.92?",
              "What if I push furnace temp to 375?",
              "How does the reformer affect the hydrocracker?"]:
        r = operator_assistant(q)
        print(f"  Q: {q}")
        print("     " + r["answer"].replace("\n", "\n     "))
        # preview-only guarantee: live plant knobs unchanged
    base_knobs = baseline_knobs()
    clear_faults()
    assert PLANT["knobs"] == base_knobs, "assistant must NOT change live plant"
    print("  -> assistant left live plant untouched (preview-only) CONFIRMED")

    # --- Manual control -> Safety path ---
    print("\n--- MANUAL CONTROL -> SAFETY ---")
    clear_faults()
    safe = operator_manual_change({"fcc_severity": 0.70})
    print(f"  operator fcc_severity=0.70 -> {safe['verdict']['verdict']}, "
          f"applied={safe['applied']}")
    clear_faults()
    unsafe = operator_manual_change({"cdu_furnace_temp_C": 385.0}, apply_if_safe=True)
    print(f"  operator furnace=385C -> {unsafe['verdict']['verdict']}, "
          f"applied={unsafe['applied']} "
          f"(binds={[b['limit'] for b in unsafe['verdict'].get('binding_limits', [])]})")
    assert unsafe["verdict"]["verdict"] in ("REJECT", "COUNTER") and not unsafe["applied"], \
        "unsafe manual change must be blocked by Safety"
    print("  -> Safety blocked the unsafe manual change CONFIRMED")

    # --- Graceful degradation: force a failure, ensure loop survives ---
    print("\n--- GRACEFUL DEGRADATION ---")
    saved = _MOCK_RESPONDERS.pop("optimization")   # simulate optimizer failure
    _LAST_GOOD.pop("optimization", None)
    clear_faults()
    c = run_advisory_cycle(verbose=False)
    print(f"  optimizer unavailable -> outcome={c['outcome']} "
          f"(system survived via stub)")
    register_mock("optimization", saved)           # restore
    assert c["outcome"] is not None, "system must survive an agent failure"
    print("  -> graceful degradation CONFIRMED")

    # --- Event log ---
    print("\n--- EVENT LOG (tail) ---")
    print("  " + log_summary(n=6).replace("\n", "\n  "))

    print("\n" + "#" * 70)
    print("#  PHASE 3 FULL TEST COMPLETE - ALL CHECKS PASSED")
    print("#" * 70)


if __name__ == "__main__":
    phase3_full_test()
