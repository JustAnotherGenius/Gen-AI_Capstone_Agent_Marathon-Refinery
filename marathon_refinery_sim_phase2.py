# ============================================================================
#  MARATHON PETROLEUM REFINERY OPTIMIZATION ADVISOR
#  PHASE 2 (COMPLETE)  -  Steps 1-7 : The Refinery Simulator & Fault System
# ----------------------------------------------------------------------------
#  STEP 1  Configuration & constants   (real anchors, sourced inline)
#  STEP 2  Six unit transfer functions (couplings = the data flow)
#  STEP 3  run_refinery() + baseline calibration vs EIA/Marathon
#  STEP 4  step()  - the continuously-running plant
#  STEP 5  trigger_scenario_A/B() + six sandbox faults
#  STEP 6  Agent tool functions (snapshot-isolated)
#  STEP 7  ~180-day dataset + full validation
#
#  COLAB: paste each STEP block into its own cell, run top-to-bottom.
#  pip installs:  !pip install numpy pandas   (pre-installed on Colab)
# ============================================================================

import numpy as np
import pandas as pd
from copy import deepcopy

RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)
GAL_PER_BBL = 42.0

# ============================================================================
#  STEP 1  -  CONFIGURATION
#  Tags: [SOURCE: ...] = real anchor   [APPROX] = honest simplification
#  [CALIBRATED] = tuned so baseline reproduces the real anchors
# ----------------------------------------------------------------------------
#  MARGIN DEFINITION NOTE: MPC reports R&M margin ($16.87/bbl FY2025) as
#  revenues less FEEDSTOCK costs per bbl throughput - operating cost
#  (~$5.65/bbl) is reported SEPARATELY. We match that definition: our
#  margin_usd_bbl is gross of opex; net margin also computed for honesty.
#  PRICING NOTE: refineries earn WHOLESALE (crude + crack spread), not the
#  EIA retail $3.20/gal. Cracks below are calibrated to land near MPC margin.
# ============================================================================

REFINERY = {
    "name": "Marathon Gulf Coast Refinery (representative)",
    "crude_capacity_bpd": 250_000,   # [SOURCE: dimensioned from MPC ~3M bbl/d / 13 refineries]
    "baseline_utilization": 0.94,    # [SOURCE: MPC FY2025 ~94%]
    "baseline_throughput_bpd": 235_000,
}

ECONOMICS = {
    "retail_gasoline_usd_gal": 3.20,   # [SOURCE: EIA STEO] context only
    "retail_diesel_usd_gal":   3.60,   # [SOURCE: EIA STEO] context only
    "crude_cost_usd_bbl": 76.0,        # [SOURCE: EIA Brent ~$76 (2025)]
    "gasoline_crack_usd_bbl": 27.0,    # [CALIBRATED to MPC margin]
    "diesel_crack_usd_bbl":   37.0,    # [CALIBRATED; diesel crack > gasoline]
    "jet_crack_usd_bbl":      31.0,    # [CALIBRATED; between the two]
    "lpg_price_usd_bbl":   40.0,       # [APPROX]
    "coke_price_usd_bbl":  15.0,       # [APPROX]
    "fueloil_price_usd_bbl": 60.0,     # [APPROX]
    "purchased_blendstock_cost_usd_bbl": 95.0,  # [APPROX]
    "energy_cost_usd_mmbtu": 3.20,     # [APPROX typical US NG]
    "gasoline_demand_bpd": 110_000,    # [APPROX around EIA slate]
    "diesel_demand_bpd":    75_000,
}

EIA_BASELINE_SLATE = {   # [SOURCE: EIA U.S. Refinery Yield, Mar 2026]
    "gasoline_pct": 46.0, "distillate_pct": 30.0, "jet_pct": 11.0, "coke_pct": 4.5,
}
MARGIN_TARGET_USD_BBL  = 16.87   # [SOURCE: MPC FY2025 R&M margin, excl. opex]
OPERATING_COST_USD_BBL = 5.65    # [SOURCE: MPC FY2025 opex, reported separately]

SPECS = {
    "gasoline_octane_floor_RON": 87.0,   # [SOURCE: US regular 87 AKI]
    "diesel_sulfur_cap_wt_pct": 0.0015,  # [SOURCE: ULSD 15 ppm]
}

# *** AUDIT #2: Blending Octane Values (non-linear octane via blending
#     indices - the standard industry simplification). [APPROX, CALIBRATED
#     so baseline pool lands ~89.5-90 RON: headroom exists but is finite] ***
BOV = {
    "reformate_base": 91.0, "reformate_sev_gain": 9.0,
    "fcc_base": 88.0,       "fcc_sev_gain": 2.5,
    "hydrocracker_gasoline": 80.0,
    "isomerate_light_naphtha": 82.0,
    "coker_naphtha": 70.0,
    "alkylate": 94.0,
    "purchased_blendstock": 89.0,
}

CRUDE_BASELINE = {"api_gravity": 32.0, "sulfur_wt_pct": 1.4}   # [APPROX medium-sour]

# Purchased butanes/oxygenates blended in [APPROX, CALIBRATED to close balance]
PURCHASED_BLENDSTOCK_BPD = 11_000

KNOBS = {
    "cdu_throughput_bpd":  {"baseline": 235_000, "min": 180_000, "max": 250_000},
    "cdu_furnace_temp_C":  {"baseline": 365.0,   "min": 340.0,   "max": 400.0},
        # band 340-400C [SOURCE: Worley Table 1-2]
    "vdu_severity":        {"baseline": 0.70,    "min": 0.40,    "max": 0.85},
    "fcc_feed_bpd":        {"baseline": 52_000,  "min": 20_000,  "max": 80_000},
    "fcc_severity":        {"baseline": 0.65,    "min": 0.40,    "max": 0.90},
    "reformer_feed_bpd":   {"baseline": 41_000,  "min": 15_000,  "max": 45_000},
    "reformer_severity":   {"baseline": 0.70,    "min": 0.40,    "max": 0.88},
    # *** LEAD OPTIMIZATION UNIT ***
    "hydrocracker_feed_bpd":   {"baseline": 23_000, "min": 10_000, "max": 45_000},
    "hydrocracker_conversion": {"baseline": 0.75,  "min": 0.60,   "max": 0.98},
        # single-stage 65-70%, two-stage 95-98% [SOURCE: Shell white paper]
}

LIMITS = {   # illustrative, set within sourced bands [APPROX]
    "cdu_furnace_temp_max_C":      370.0,
    "cdu_throughput_max_bpd":      250_000,
    "vdu_severity_max":            0.85,
    "fcc_feed_max_bpd":            80_000,
    "fcc_coke_make_max_pct":       6.0,
    "reformer_severity_max":       0.88,
    "hydrocracker_conversion_max": 0.98,
    "h2_makeup_supply_scfd":       25_000_000.0,   # [APPROX]
}

SIM_CONTROL = {
    "tick_seconds": 3.0, "noise_enabled": False,
    "noise_magnitude": 0.01, "drift_magnitude": 0.004,
}

CFG = {"refinery": REFINERY, "economics": ECONOMICS, "eia_slate": EIA_BASELINE_SLATE,
       "margin_target": MARGIN_TARGET_USD_BBL, "operating_cost": OPERATING_COST_USD_BBL,
       "specs": SPECS, "bov": BOV, "crude": CRUDE_BASELINE,
       "knobs": KNOBS, "limits": LIMITS, "sim": SIM_CONTROL}

def baseline_knobs():     return {k: v["baseline"] for k, v in CFG["knobs"].items()}
def baseline_economics(): return deepcopy(CFG["economics"])
def baseline_crude():     return deepcopy(CFG["crude"])
def clamp_knob(name, value):
    s = CFG["knobs"][name]
    return float(np.clip(value, s["min"], s["max"]))

# "Adjustments" carry FAULT physics into the simulator so that BOTH the live
# plant AND simulate_proposal() see identical fault conditions. (Without
# this, the Safety Agent would evaluate proposals in a fault-free world -
# a correctness bug caught during build.)
DEFAULT_ADJUSTMENTS = {
    "h2_makeup_factor": 1.0,        # <1.0 = external H2 supply derated
    "reformate_bov_penalty": 0.0,   # catalyst deactivation lowers octane
    "purchased_bov_override": None, # e.g. butane restriction -> low-BOV stock
}

# ============================================================================
#  STEP 2  -  UNIT TRANSFER FUNCTIONS  (thin, monotonic, directionally correct)
# ============================================================================

def cdu(throughput_bpd, furnace_temp_C, crude_api, crude_sulfur):
    """Unit 1 - CDU, the master splitter (Coupling 1). Higher furnace temp ->
    heavier material vaporized -> more diesel/AGO, less residue. Higher API
    (lighter crude) -> more naphtha, less residue."""
    dT, dAPI = furnace_temp_C - 365.0, crude_api - 32.0
    naphtha_light = 0.060 + 0.0020 * dAPI
    naphtha_heavy = 0.175 + 0.0030 * dAPI
    jet           = 0.110 + 0.0004 * dT
    diesel        = 0.185 + 0.0009 * dT + 0.0010 * dAPI
    ago           = 0.140 + 0.0011 * dT
    light_ends    = 0.040
    residue = max(1.0 - (naphtha_light + naphtha_heavy + jet + diesel + ago + light_ends), 0.05)
    energy = throughput_bpd / 24.0 * (0.090 + 0.00035 * max(dT, 0) + 6e-6 * dT * dT)
    return {"naphtha_light_bpd": throughput_bpd * naphtha_light,
            "naphtha_heavy_bpd": throughput_bpd * naphtha_heavy,
            "jet_bpd": throughput_bpd * jet,
            "cdu_diesel_bpd": throughput_bpd * diesel,
            "ago_bpd": throughput_bpd * ago,
            "residue_bpd": throughput_bpd * residue,
            "light_ends_bpd": throughput_bpd * light_ends,
            "cdu_energy_mmbtu_hr": energy}

def vdu(residue_feed_bpd, severity):
    """Unit 2 - VDU (Coupling 2): recovers VGO from CDU residue."""
    vgo = residue_feed_bpd * (0.40 + 0.32 * severity)
    return {"vgo_bpd": vgo, "vacres_bpd": residue_feed_bpd - vgo,
            "vdu_energy_mmbtu_hr": residue_feed_bpd / 24.0 * (0.030 + 0.050 * severity**2)}

def coker(vacres_bpd):
    """Delayed coker, FIXED yields [APPROX] - closes the coke/gasoline
    balance honestly (US archetype includes a DCU, Worley Fig 2-3)."""
    return {"coker_coke_bpd": vacres_bpd * 0.30,
            "coker_gasoil_bpd": vacres_bpd * 0.40,
            "coker_naphtha_bpd": vacres_bpd * 0.15,
            "coker_gas_bpd": vacres_bpd * 0.15}

def fcc(feed_bpd, severity):
    """Unit 3 - FCC (Coupling 5): severity raises gasoline & octane but
    coke rises quadratically toward its hard limit; LCO falls."""
    return {"fcc_gasoline_bpd": feed_bpd * (0.35 + 0.32 * severity),
            "alkylate_bpd": feed_bpd * (0.10 + 0.12 * severity) * 0.90,
            "lco_bpd": feed_bpd * (0.24 - 0.18 * severity),
            "fcc_coke_bpd": feed_bpd * (3.0 + 4.5 * severity**2) / 100.0,
            "coke_make_pct": 3.0 + 4.5 * severity**2,
            "fcc_bov": CFG["bov"]["fcc_base"] + CFG["bov"]["fcc_sev_gain"] * severity,
            "fcc_energy_mmbtu_hr": feed_bpd / 24.0 * (0.040 + 0.070 * severity**2)}

def reformer(feed_bpd, severity, bov_penalty=0.0):
    """Unit 4 - Reformer: octane machine AND H2 producer (Coupling 4).
    Severity: octane & H2 up, volume down (Coupling 5)."""
    return {"reformate_bpd": feed_bpd * (0.92 - 0.14 * severity),
            "reformate_bov": (CFG["bov"]["reformate_base"]
                              + CFG["bov"]["reformate_sev_gain"] * severity - bov_penalty),
            "h2_production_scfd": feed_bpd * (600.0 + 500.0 * severity),
            "reformer_energy_mmbtu_hr": feed_bpd / 24.0 * (0.050 + 0.090 * severity**2)}

def hydrocracker(feed_bpd, conversion, h2_available_scfd):
    """Unit 5 - HYDROCRACKER (LEAD UNIT). Low conversion -> diesel-heavy,
    high -> gasoline-heavy. Consumes H2 (Coupling 4). ~10% volume swell."""
    h2_demand = feed_bpd * (1200.0 + 1400.0 * conversion)
    converted = feed_bpd * conversion * 1.10
    gshare = float(np.clip(0.20 + 0.45 * (conversion - 0.60) / 0.38, 0.15, 0.70))
    return {"hc_gasoline_bpd": converted * gshare,
            "hc_diesel_bpd": converted * (1.0 - gshare),
            "uco_bpd": feed_bpd * (1.0 - conversion),
            "h2_demand_scfd": h2_demand,
            "h2_ok": h2_demand <= h2_available_scfd,
            "hc_energy_mmbtu_hr": feed_bpd / 24.0 * (0.060 + 0.080 * conversion**2)}

def blending_pool(s, crude_sulfur, purchased_bov):
    """Unit 6 - Blending Pool (Coupling 6). *** AUDIT #2: BOV blending ***
    Diesel sulfur: hydrotreaters implicit; product S ~ 0.001 x crude S,
    calibrated so baseline lands just UNDER the 15 ppm cap."""
    comps = [(s["fcc_gasoline_bpd"], s["fcc_bov"]),
             (s["reformate_bpd"], s["reformate_bov"]),
             (s["hc_gasoline_bpd"], CFG["bov"]["hydrocracker_gasoline"]),
             (s["naphtha_light_bpd"], CFG["bov"]["isomerate_light_naphtha"]),
             (s["coker_naphtha_bpd"], CFG["bov"]["coker_naphtha"]),
             (s["alkylate_bpd"], CFG["bov"]["alkylate"]),
             (s["purchased_blendstock_bpd"], purchased_bov)]
    v = sum(x for x, _ in comps)
    return {"gasoline_pool_bpd": v,
            "pool_octane_RON": sum(x*b for x, b in comps) / max(v, 1e-9),
            "diesel_pool_bpd": (s["cdu_diesel_bpd"] + s["hc_diesel_bpd"]
                                + s["lco_bpd"] + s["coker_gasoil_bpd"]),
            "diesel_sulfur_wt_pct": crude_sulfur * 0.001}

# ============================================================================
#  STEP 3  -  run_refinery() + BASELINE VALIDATION
# ============================================================================

def run_refinery(knobs, economics, crude, adjustments=None):
    """knobs + economics + crude (+fault adjustments) -> full plant state."""
    adj = {**DEFAULT_ADJUSTMENTS, **(adjustments or {})}
    k, e, c = knobs, economics, crude

    s = cdu(k["cdu_throughput_bpd"], k["cdu_furnace_temp_C"],
            c["api_gravity"], c["sulfur_wt_pct"])
    s.update(vdu(s["residue_bpd"], k["vdu_severity"]))
    s.update(coker(s["vacres_bpd"]))

    # Coupling 3: finite feed pool, FCC draws first, HC gets the rest
    pool = s["ago_bpd"] + s["vgo_bpd"]
    fcc_feed = min(k["fcc_feed_bpd"], pool)
    hc_feed  = max(min(k["hydrocracker_feed_bpd"], pool - fcc_feed), 0.0)
    s.update({"feed_pool_bpd": pool, "fcc_feed_actual_bpd": fcc_feed,
              "hc_feed_actual_bpd": hc_feed,
              "feed_pool_slack_bpd": pool - fcc_feed - hc_feed})

    ref_feed = min(k["reformer_feed_bpd"], s["naphtha_heavy_bpd"])
    s.update(reformer(ref_feed, k["reformer_severity"], adj["reformate_bov_penalty"]))
    s["reformer_feed_actual_bpd"] = ref_feed
    s.update(fcc(fcc_feed, k["fcc_severity"]))

    h2_avail = (s["h2_production_scfd"]
                + CFG["limits"]["h2_makeup_supply_scfd"] * adj["h2_makeup_factor"])
    s.update(hydrocracker(hc_feed, k["hydrocracker_conversion"], h2_avail))
    s["h2_available_scfd"] = h2_avail

    s["purchased_blendstock_bpd"] = PURCHASED_BLENDSTOCK_BPD
    pbov = adj["purchased_bov_override"] or CFG["bov"]["purchased_blendstock"]
    s.update(blending_pool(s, c["sulfur_wt_pct"], pbov))

    thr = k["cdu_throughput_bpd"]
    total_coke = s["coker_coke_bpd"] + s["fcc_coke_bpd"]
    s["slate_gasoline_pct"]   = 100 * s["gasoline_pool_bpd"] / thr
    s["slate_distillate_pct"] = 100 * s["diesel_pool_bpd"] / thr
    s["slate_jet_pct"]        = 100 * s["jet_bpd"] / thr
    s["slate_coke_pct"]       = 100 * total_coke / thr

    s["total_energy_mmbtu_day"] = 24.0 * (
        s["cdu_energy_mmbtu_hr"] + s["vdu_energy_mmbtu_hr"]
        + s["fcc_energy_mmbtu_hr"] + s["reformer_energy_mmbtu_hr"]
        + s["hc_energy_mmbtu_hr"])

    p_gas, p_die, p_jet = (e["crude_cost_usd_bbl"] + e["gasoline_crack_usd_bbl"],
                           e["crude_cost_usd_bbl"] + e["diesel_crack_usd_bbl"],
                           e["crude_cost_usd_bbl"] + e["jet_crack_usd_bbl"])
    revenue = (s["gasoline_pool_bpd"] * p_gas + s["diesel_pool_bpd"] * p_die
               + s["jet_bpd"] * p_jet + s["uco_bpd"] * e["fueloil_price_usd_bbl"]
               + total_coke * e["coke_price_usd_bbl"]
               + s["light_ends_bpd"] * e["lpg_price_usd_bbl"])
    feed_cost = (thr * e["crude_cost_usd_bbl"]
                 + PURCHASED_BLENDSTOCK_BPD * e["purchased_blendstock_cost_usd_bbl"]
                 + s["total_energy_mmbtu_day"] * e["energy_cost_usd_mmbtu"])
    # MPC-definition margin (gross of opex); net shown for honesty
    s["margin_usd_day"] = revenue - feed_cost
    s["margin_usd_bbl"] = s["margin_usd_day"] / thr
    s["net_margin_usd_bbl"] = s["margin_usd_bbl"] - CFG["operating_cost"]

    s["knobs"], s["economics"], s["crude"] = dict(knobs), dict(economics), dict(crude)
    s["adjustments"] = dict(adj)
    return s


def validate_baseline(verbose=True):
    s = run_refinery(baseline_knobs(), baseline_economics(), baseline_crude())
    rows = [("Gasoline  %", s["slate_gasoline_pct"], CFG["eia_slate"]["gasoline_pct"]),
            ("Distillate %", s["slate_distillate_pct"], CFG["eia_slate"]["distillate_pct"]),
            ("Jet       %", s["slate_jet_pct"], CFG["eia_slate"]["jet_pct"]),
            ("Coke      %", s["slate_coke_pct"], CFG["eia_slate"]["coke_pct"]),
            ("Margin $/bbl", s["margin_usd_bbl"], CFG["margin_target"])]
    if verbose:
        print("=" * 66)
        print("  BASELINE VALIDATION  -  simulated vs. real anchors")
        print("=" * 66)
        print(f"  {'Metric':<14}{'Simulated':>12}{'Real anchor':>14}{'Delta':>10}")
        print("-" * 66)
        for n, sim, real in rows:
            print(f"  {n:<14}{sim:>12.2f}{real:>14.2f}{sim-real:>+10.2f}")
        print("-" * 66)
        print(f"  Pool octane {s['pool_octane_RON']:.2f} RON (floor 87, headroom "
              f"{s['pool_octane_RON']-87:+.2f}) | Diesel S "
              f"{s['diesel_sulfur_wt_pct']*1e4:.1f} vs 15 ppm | net margin "
              f"${s['net_margin_usd_bbl']:.2f}/bbl (after ${CFG['operating_cost']}/bbl opex)")
        print(f"  H2 {s['h2_demand_scfd']/1e6:.1f} vs {s['h2_available_scfd']/1e6:.1f} MMscfd "
              f"({'OK' if s['h2_ok'] else 'SHORT'}) | feed pool {s['feed_pool_bpd']:,.0f} "
              f"(FCC {s['fcc_feed_actual_bpd']:,.0f} + HC {s['hc_feed_actual_bpd']:,.0f}, "
              f"slack {s['feed_pool_slack_bpd']:,.0f})")
    d = {n: abs(sim - r) for n, sim, r in rows}
    ok = (d["Gasoline  %"] <= 3.0 and d["Distillate %"] <= 3.0 and
          d["Jet       %"] <= 2.0 and d["Coke      %"] <= 1.5 and
          d["Margin $/bbl"] <= 2.5)
    if verbose:
        print(f"  VALIDATION {'PASSED' if ok else 'FAILED'} "
              f"(slate +/-3, jet +/-2, coke +/-1.5, margin +/-$2.5)")
        print("=" * 66)
    return ok, s

# ============================================================================
#  STEP 4  -  THE LIVE PLANT
# ============================================================================

PLANT = {"tick": 0, "knobs": baseline_knobs(), "economics": baseline_economics(),
         "crude": baseline_crude(), "active_faults": {}, "state": None}

def _apply_drift(p):
    m = CFG["sim"]["drift_magnitude"]
    for key in ["gasoline_crack_usd_bbl", "diesel_crack_usd_bbl",
                "gasoline_demand_bpd", "diesel_demand_bpd"]:
        p["economics"][key] *= float(1.0 + rng.uniform(-m, m))
    p["crude"]["api_gravity"]   *= float(1.0 + rng.uniform(-m, m) * 0.3)
    p["crude"]["sulfur_wt_pct"] *= float(1.0 + rng.uniform(-m, m) * 0.5)

def _apply_faults(p):
    """Re-impose active fault effects each tick (persistent until cleared).
    Returns the combined 'adjustments' dict for run_refinery."""
    e, c, k, F = p["economics"], p["crude"], p["knobs"], p["active_faults"]
    adj = dict(DEFAULT_ADJUSTMENTS)
    if "scenario_A_gasoline_opportunity" in F:
        e["gasoline_crack_usd_bbl"] = 39.0; e["gasoline_demand_bpd"] = 135_000
    if "scenario_B_diesel_coldsnap" in F:
        e["diesel_crack_usd_bbl"] = 56.0; e["diesel_demand_bpd"] = 105_000
        adj["h2_makeup_factor"] = min(adj["h2_makeup_factor"], 0.5)
    if "heavy_sour_crude" in F:
        c["api_gravity"], c["sulfur_wt_pct"] = 24.0, 2.6
    if "h2_shortfall" in F:
        adj["h2_makeup_factor"] = min(adj["h2_makeup_factor"], 0.35)
    if "fcc_coke_excursion" in F:
        k["fcc_severity"] = min(k["fcc_severity"] + 0.18, KNOBS["fcc_severity"]["max"])
    if "energy_cost_spike" in F:
        e["energy_cost_usd_mmbtu"] = 9.5
    if "octane_floor_risk" in F:
        k["reformer_severity"] = 0.45
        adj["reformate_bov_penalty"] = 5.0        # catalyst deactivation
        adj["purchased_bov_override"] = 78.0      # butane restriction
    if "cdu_throughput_constraint" in F:
        k["cdu_throughput_bpd"] = 195_000
    return adj

def step(plant=PLANT):
    """Advance ONE tick: drift E/S, apply faults, re-run the refinery."""
    plant["tick"] += 1
    _apply_drift(plant)
    adj = _apply_faults(plant)
    plant["state"] = run_refinery(plant["knobs"], plant["economics"],
                                  plant["crude"], adjustments=adj)
    plant["state"]["tick"] = plant["tick"]
    plant["state"]["active_faults"] = list(plant["active_faults"].keys())
    return plant["state"]

# ============================================================================
#  STEP 5  -  SCENARIOS (guaranteed demo spine) + SANDBOX FAULTS
# ============================================================================

def trigger_scenario_A(plant=PLANT):
    """A - Gasoline opportunity -> APPROVE-WITH-COUNTER path."""
    plant["active_faults"]["scenario_A_gasoline_opportunity"] = {}
    return step(plant)

def trigger_scenario_B(plant=PLANT):
    """B - Cold-snap diesel spike + tight H2 -> REJECT path."""
    plant["active_faults"]["scenario_B_diesel_coldsnap"] = {}
    return step(plant)

SANDBOX_FAULTS = ["heavy_sour_crude", "h2_shortfall", "fcc_coke_excursion",
                  "energy_cost_spike", "octane_floor_risk", "cdu_throughput_constraint"]

def inject_fault(fault_id, plant=PLANT):
    if fault_id not in SANDBOX_FAULTS:
        raise ValueError(f"unknown fault '{fault_id}'; valid = {SANDBOX_FAULTS}")
    plant["active_faults"][fault_id] = {}
    return step(plant)

def clear_faults(plant=PLANT):
    plant["active_faults"] = {}
    plant["economics"], plant["crude"] = baseline_economics(), baseline_crude()
    plant["knobs"] = baseline_knobs()
    return step(plant)

# ============================================================================
#  STEP 6  -  AGENT TOOLS  (*** AUDIT #3: snapshot-isolation ***)
# ============================================================================

def get_refinery_state(plant=PLANT):
    """TOOL 1 (Monitoring). Immutable deep-copy snapshot: the whole agent
    pipeline reasons against THIS while the live plant keeps ticking."""
    if plant["state"] is None:
        step(plant)
    return deepcopy(plant["state"])

def simulate_proposal(knob_changes, snapshot):
    """TOOL 2 (Optimization). What-if on the SNAPSHOT (same economics, same
    crude, SAME FAULT ADJUSTMENTS - so Safety verdicts stay correct under
    active faults). Never touches the live plant."""
    knobs = dict(snapshot["knobs"])
    for name, val in knob_changes.items():
        if name not in knobs:
            raise ValueError(f"unknown knob '{name}'")
        knobs[name] = clamp_knob(name, val)
    pred = run_refinery(knobs, snapshot["economics"], snapshot["crude"],
                        adjustments=snapshot["adjustments"])
    pred["margin_delta_usd_day"] = pred["margin_usd_day"] - snapshot["margin_usd_day"]
    pred["proposed_knob_changes"] = dict(knob_changes)
    return pred

def check_all_limits(state):
    """TOOL 3 (Safety). Every hard limit + spec -> pass/fail + which bind."""
    L, SP, k = CFG["limits"], CFG["specs"], state["knobs"]
    checks = [
        ("CDU furnace temp",  k["cdu_furnace_temp_C"], "<=", L["cdu_furnace_temp_max_C"], "C"),
        ("CDU throughput",    k["cdu_throughput_bpd"], "<=", L["cdu_throughput_max_bpd"], "bpd"),
        ("VDU severity",      k["vdu_severity"], "<=", L["vdu_severity_max"], ""),
        ("FCC feed",          state["fcc_feed_actual_bpd"], "<=", L["fcc_feed_max_bpd"], "bpd"),
        ("FCC coke make",     state["coke_make_pct"], "<=", L["fcc_coke_make_max_pct"], "%"),
        ("Reformer severity", k["reformer_severity"], "<=", L["reformer_severity_max"], ""),
        ("HC conversion",     k["hydrocracker_conversion"], "<=", L["hydrocracker_conversion_max"], ""),
        ("H2 balance",        state["h2_demand_scfd"], "<=", state["h2_available_scfd"], "scfd"),
        ("Pool octane",       state["pool_octane_RON"], ">=", SP["gasoline_octane_floor_RON"], "RON"),
        ("Diesel sulfur",     state["diesel_sulfur_wt_pct"], "<=", SP["diesel_sulfur_cap_wt_pct"], "wt%"),
    ]
    res = [{"limit": n, "value": round(float(v), 5), "op": op,
            "bound": round(float(b), 5), "unit": u, "ok": bool(v <= b if op == "<=" else v >= b)}
           for n, v, op, b, u in checks]
    return {"all_ok": all(r["ok"] for r in res), "checks": res}

# ============================================================================
#  STEP 7  -  DATASET (~180 days, audit #4) + FULL VALIDATION
# ============================================================================

def generate_dataset(n_days=180, knob_band=0.12, path="refinery_operating_days.csv"):
    rows = []
    for day in range(n_days):
        econ, crude = baseline_economics(), baseline_crude()
        econ["gasoline_crack_usd_bbl"] *= rng.uniform(0.75, 1.35)
        econ["diesel_crack_usd_bbl"]   *= rng.uniform(0.75, 1.40)
        econ["energy_cost_usd_mmbtu"]  *= rng.uniform(0.70, 1.80)
        econ["gasoline_demand_bpd"]    *= rng.uniform(0.85, 1.15)
        econ["diesel_demand_bpd"]      *= rng.uniform(0.85, 1.15)
        crude["api_gravity"]   = rng.uniform(26.0, 38.0)
        crude["sulfur_wt_pct"] = rng.uniform(0.5, 2.2)
        knobs = {n: clamp_knob(n, sp["baseline"] * (1 + rng.uniform(-knob_band, knob_band)))
                 for n, sp in CFG["knobs"].items()}
        s = run_refinery(knobs, econ, crude)
        rows.append({"day": day + 1, "crude_api": crude["api_gravity"],
                     "crude_sulfur_wt_pct": crude["sulfur_wt_pct"],
                     "gasoline_crack": econ["gasoline_crack_usd_bbl"],
                     "diesel_crack": econ["diesel_crack_usd_bbl"],
                     "energy_cost": econ["energy_cost_usd_mmbtu"],
                     **{f"knob_{k}": v for k, v in knobs.items()},
                     "gasoline_pool_bpd": s["gasoline_pool_bpd"],
                     "diesel_pool_bpd": s["diesel_pool_bpd"],
                     "jet_bpd": s["jet_bpd"], "pool_octane_RON": s["pool_octane_RON"],
                     "fcc_coke_pct": s["coke_make_pct"],
                     "h2_demand_scfd": s["h2_demand_scfd"],
                     "energy_mmbtu_day": s["total_energy_mmbtu_day"],
                     "margin_usd_bbl": s["margin_usd_bbl"]})
    df = pd.DataFrame(rows); df.to_csv(path, index=False)
    return df


def generate_baseline_dataset(n_days=100, path="refinery_baseline_days.csv"):
    """CONTROL dataset: knobs FIXED at baseline, only markets (E) and crude
    quality (S) vary. Isolates 'how do external conditions alone move the
    plant?' - the companion to the exploratory knob-varying dataset
    ('how do operational choices move it?'). Control-vs-treatment framing."""
    return generate_dataset(n_days=n_days, knob_band=0.0, path=path)


def full_validation():
    print("\n" + "#" * 66)
    print("#  PHASE 2 FULL VALIDATION")
    print("#" * 66)

    ok, base = validate_baseline(verbose=True)
    assert ok, "Baseline calibration failed - tune constants!"

    clear_faults(); m0 = PLANT["state"]["margin_usd_bbl"]
    for _ in range(5): st = step()
    print(f"\n[step] 5 ticks: margin {m0:.2f} -> {st['margin_usd_bbl']:.2f} $/bbl "
          f"(drift OK, tick={st['tick']})")

    # --- Scenario A: approve-with-counter path ---
    clear_faults(); sA = trigger_scenario_A()
    snapA = get_refinery_state()
    print(f"\n[Scenario A] gasoline crack ${sA['economics']['gasoline_crack_usd_bbl']:.0f}/bbl, "
          f"FCC {sA['fcc_feed_actual_bpd']:,.0f}/{CFG['limits']['fcc_feed_max_bpd']:,.0f} bpd, "
          f"octane headroom {sA['pool_octane_RON']-87:+.2f} RON")
    propA = simulate_proposal({"fcc_feed_bpd": snapA["knobs"]["fcc_feed_bpd"] + 12_000,
                               "fcc_severity": snapA["knobs"]["fcc_severity"] + 0.17}, snapA)
    bindA = [c["limit"] for c in check_all_limits(propA)["checks"] if not c["ok"]]
    propA2 = simulate_proposal({"fcc_feed_bpd": snapA["knobs"]["fcc_feed_bpd"] + 12_000,
                                "fcc_severity": snapA["knobs"]["fcc_severity"] + 0.05}, snapA)
    okA2 = check_all_limits(propA2)["all_ok"]
    print(f"[Scenario A] aggressive: {propA['margin_delta_usd_day']:+,.0f} $/day, binds {bindA}")
    print(f"[Scenario A] counter:    {propA2['margin_delta_usd_day']:+,.0f} $/day, all_ok={okA2}")
    assert "FCC coke make" in bindA and okA2, "Scenario A path broken!"
    print("[Scenario A] APPROVE-WITH-COUNTER path confirmed")

    # --- Scenario B: reject path ---
    clear_faults(); sB = trigger_scenario_B()
    snapB = get_refinery_state()
    # Tempting diesel-max move: swing feed FCC->HC (rivalry), push furnace,
    # drop conversion for diesel. Breaches BOTH furnace temp AND H2 balance.
    propB = simulate_proposal({"cdu_furnace_temp_C": 374.0,
                               "hydrocracker_conversion": 0.62,
                               "fcc_feed_bpd": snapB["knobs"]["fcc_feed_bpd"] - 15_000,
                               "hydrocracker_feed_bpd": snapB["knobs"]["hydrocracker_feed_bpd"] + 15_000},
                              snapB)
    bindB = [c["limit"] for c in check_all_limits(propB)["checks"] if not c["ok"]]
    # Elegant counter (Coupling 4): RAISE reformer severity to MAKE more H2,
    # modest HC feed/conversion shift, furnace stays under the limit.
    propB2 = simulate_proposal({"cdu_furnace_temp_C": 368.0,
                                "reformer_severity": 0.80,
                                "hydrocracker_feed_bpd": 25_000,
                                "hydrocracker_conversion": 0.66,
                                "fcc_feed_bpd": 50_000}, snapB)
    okB2 = check_all_limits(propB2)["all_ok"]
    print(f"\n[Scenario B] diesel crack ${sB['economics']['diesel_crack_usd_bbl']:.0f}/bbl; "
          f"tempting move binds {bindB}")
    print(f"[Scenario B] safe counter: {propB2['margin_delta_usd_day']:+,.0f} $/day, all_ok={okB2}")
    assert "CDU furnace temp" in bindB and "H2 balance" in bindB and okB2, "Scenario B path broken!"
    print("[Scenario B] REJECT-then-COUNTER path confirmed")

    # --- Sandbox faults ---
    print("\n[sandbox faults]")
    for fid in SANDBOX_FAULTS:
        clear_faults(); st = inject_fault(fid)
        flags = [c["limit"] for c in check_all_limits(st)["checks"] if not c["ok"]]
        print(f"  {fid:<28} margin {st['margin_usd_bbl']:>6.2f} $/bbl | "
              f"binds: {flags if flags else 'none (economic fault)'}")
    clear_faults()

    # --- Snapshot isolation ---
    snap = get_refinery_state(); before = snap["margin_usd_bbl"]
    for _ in range(3): step()
    assert snap["margin_usd_bbl"] == before, "snapshot mutated!"
    print("\n[snapshot-isolation] snapshot unchanged after 3 live ticks -> OK")

    # --- Dataset ---
    df = generate_dataset()
    num = df.select_dtypes("number")
    bad = bool((num.drop(columns=["margin_usd_bbl"]) < 0).any().any() or df.isna().any().any())
    print(f"[dataset] {len(df)} days -> refinery_operating_days.csv | "
          f"negatives/NaN: {'FOUND - BUG!' if bad else 'none'} | margin "
          f"${df['margin_usd_bbl'].min():.2f} to ${df['margin_usd_bbl'].max():.2f}/bbl")
    corr = df[["knob_hydrocracker_conversion", "gasoline_pool_bpd", "diesel_pool_bpd"]].corr()
    print(f"[dataset] HC conversion corr: gasoline {corr.iloc[0,1]:+.2f} | "
          f"diesel {corr.iloc[0,2]:+.2f}  (lead-knob story visible in data)")
    assert not bad, "dataset instability!"

    print("\n" + "#" * 66)
    print("#  PHASE 2 VALIDATION COMPLETE - ALL CHECKS PASSED")
    print("#" * 66)
    return df


if __name__ == "__main__":
    df = full_validation()
