# Operator Manual
## Marathon Gulf Coast Refinery — Digital Twin & Advisory System

**Purpose of this document:** explain, in plain but precise terms, how the simulated refinery works — every unit, every variable, how they connect, and the exact equations behind them. This manual is read by two audiences: **you** (as project documentation) and **the Operator Assistant agent** (as its knowledge base for answering operator questions).

Every number in this manual matches the live `CFG` configuration in the simulator code. If you change a constant in the code, update it here too.

---

## 1. What This System Is

A **representative Marathon Petroleum Gulf Coast refinery** (~250,000 bbl/day crude capacity, ~94% utilization), modeled as a network of **six process units**. Crude oil enters one end; gasoline, diesel, and jet fuel exit the other. Between them, six units transform the crude in a specific order, and — critically — **the units are coupled**: a decision made at one unit changes what's available to the next.

The **Hydrocracker is the lead optimization unit** — it's the main lever for shifting production between gasoline and diesel, mirroring how Marathon actually operates its real hydrocrackers (e.g., the Garyville unit).

Three advisory agents watch this plant continuously: **Monitoring** (diagnoses), **Optimization** (proposes profitable moves), and **Safety** (approves, rejects, or counters every proposal against hard limits). A fourth, the **Operator Assistant**, answers your questions and previews "what-if" scenarios — it never changes the plant itself.

---

## 2. The Six Units, In Order

Crude flows through the units in this sequence:

```
CRUDE → [1 CDU] → [2 VDU] ─┬─→ [3 FCC] ──┐
                            └─→ [5 HYDROCRACKER] ──┤
                [4 REFORMER] ───────────────────────┤
                                                      ▼
                                          [6 BLENDING POOL] → PRODUCTS
```

### Unit 1 — CDU (Crude Distillation Unit)
**What it does:** the "master splitter." Heats crude and separates it by boiling point into fractions: light naphtha, heavy naphtha, jet, diesel, atmospheric gas oil (AGO), and residue (the leftover heavy material).

**You control:**
| Knob | Baseline | Range | What it does |
|---|---|---|---|
| `cdu_throughput_bpd` | 235,000 | 180,000 – 250,000 | How much crude/day flows through the whole plant |
| `cdu_furnace_temp_C` | 365°C | 340 – 400°C | How hot the crude is heated before separation |

**The equation (simplified):** raising furnace temperature vaporizes progressively heavier material, shifting yield toward diesel and AGO and away from residue. Raising throughput scales everything proportionally but pushes energy use up.

```
naphtha_light  = 0.060 + 0.0020 × (crude_API − 32)
naphtha_heavy  = 0.175 + 0.0030 × (crude_API − 32)
jet            = 0.110 + 0.0004 × (furnace_temp − 365)
diesel         = 0.185 + 0.0009 × (furnace_temp − 365) + 0.0010 × (crude_API − 32)
ago            = 0.140 + 0.0011 × (furnace_temp − 365)
residue        = 1.0 − (sum of the above + fixed light-ends fraction)
```
(All fractions are of crude throughput; residue is floored so it never goes negative.)

**Energy cost** rises non-linearly above the 365°C baseline — pushing the furnace hot is not free.

**Hard limits:**
- Furnace temp ≤ **370°C** (metallurgical tube limit)
- Throughput ≤ **250,000 bbl/day** (hydraulic capacity)

---

### Unit 2 — VDU (Vacuum Distillation Unit)
**What it does:** takes the CDU's leftover residue and pulls further value from it by distilling under vacuum (which lets heavy material boil at a lower temperature without cracking it). Recovers **VGO** (vacuum gas oil — valuable, feeds the conversion units) from otherwise low-value residue.

**You control:**
| Knob | Baseline | Range | What it does |
|---|---|---|---|
| `vdu_severity` | 0.70 | 0.40 – 0.85 | How hard the unit pulls VGO from residue |

**The equation:**
```
vgo_fraction = 0.40 + 0.32 × severity        (e.g. at 0.70 → 62.4% of residue becomes VGO)
vgo_bpd      = residue_feed × vgo_fraction
vacuum_residue_bpd = residue_feed − vgo_bpd
```
Higher severity = more VGO recovered, but energy use rises with the square of severity, and above the limit the process risks coking inside the unit.

**Hard limit:** severity ≤ **0.85**.

---

### Unit 3 — FCC (Fluid Catalytic Cracker) — *secondary gasoline lever*
**What it does:** cracks VGO/AGO into gasoline using a catalyst. This is the traditional "gasoline engine" of a refinery — and it competes with the Hydrocracker for the same feed pool (see Coupling 3 below).

**You control:**
| Knob | Baseline | Range | What it does |
|---|---|---|---|
| `fcc_feed_bpd` | 52,000 | 20,000 – 80,000 | How much of the VGO/AGO pool is routed here |
| `fcc_severity` | 0.65 | 0.40 – 0.90 | How hard the cracking reaction runs |

**The equation:**
```
fcc_gasoline_bpd = feed × (0.35 + 0.32 × severity)
coke_make_pct    = 3.0 + 4.5 × severity²          ← rises FAST at high severity
fcc_bov          = 88.0 + 2.5 × severity           (octane contribution; see §4)
```
Coke is the key trap here: it climbs with the *square* of severity, so a small push near the top of the range can jump the plant into a limit violation quickly. This is deliberate — it's the mechanism behind the "approve-with-counter" behavior you'll see from the agents.

**Hard limits:** feed ≤ **80,000 bbl/day**; coke make ≤ **6.0%**.

---

### Unit 4 — Reformer (Catalytic Reformer)
**What it does:** two jobs at once — it converts naphtha into high-octane gasoline blendstock (**reformate**), AND it produces **hydrogen** as a byproduct. That hydrogen is essential fuel for Unit 5, the Hydrocracker. This dual role is the single most important coupling in the whole plant (Coupling 4).

**You control:**
| Knob | Baseline | Range | What it does |
|---|---|---|---|
| `reformer_feed_bpd` | 41,000 | 15,000 – 45,000 | How much heavy naphtha is processed |
| `reformer_severity` | 0.70 | 0.40 – 0.88 | Octane vs. volume/H₂ trade-off |

**The equation:**
```
reformate_bpd       = feed × (0.92 − 0.14 × severity)     ← volume SHRINKS as severity rises
reformate_bov        = 91.0 + 9.0 × severity                ← octane RISES as severity rises
h2_production_scfd   = feed × (600 + 500 × severity)        ← more severity = more H2
```
This is a genuine trade-off unit: pushing severity for octane costs you reformate *volume*, but it also frees up hydrogen for the Hydrocracker — which is exactly the "elegant counter-move" the Optimization Agent uses in Scenario B.

**Hard limit:** severity ≤ **0.88**.

---

### Unit 5 — Hydrocracker — ★ LEAD OPTIMIZATION UNIT ★
**What it does:** the flexibility engine of the whole refinery. It cracks VGO into a mix of gasoline and diesel, and — uniquely — **you control the ratio directly** via the conversion knob. This is the unit Marathon's real Garyville facility was expanded around (77,000 → 115,000 bbl/day), and it's why we made it the lead knob in this system.

**You control:**
| Knob | Baseline | Range | What it does |
|---|---|---|---|
| `hydrocracker_feed_bpd` | 23,000 | 10,000 – 45,000 | How much VGO is routed here |
| `hydrocracker_conversion` | 0.75 | 0.60 – 0.98 | **LOW → diesel-heavy. HIGH → gasoline-heavy.** |

**The equation:**
```
h2_demand_scfd     = feed × (1200 + 1400 × conversion)     ← MUST NOT exceed H2 supply
converted_bpd       = feed × conversion × 1.10               (10% volume swell)
gasoline_share      = clip(0.20 + 0.45 × (conversion − 0.60)/0.38, 0.15, 0.70)
hc_gasoline_bpd     = converted × gasoline_share
hc_diesel_bpd       = converted × (1 − gasoline_share)
```
Real-world reference: single-stage hydrocrackers run 65–70% conversion; two-stage units run 95–98%. Our range (0.60–0.98) spans both.

**Hard limits:** conversion ≤ **0.98**; and critically, **hydrogen demand must not exceed hydrogen available** (production from the Reformer + a small external makeup buffer). This is not a fixed number — it's *dynamic*, computed fresh every cycle from Unit 4's output.

---

### Unit 6 — Blending Pool
**What it does:** every gasoline stream from every unit (FCC, Reformer, Hydrocracker, plus small coker/purchased streams) is mixed together here. This is where all the upstream trade-offs finally "cash out" into a real product that must meet **hard specifications** — or it's worthless.

**No knob** — this unit is a pure consequence of everything upstream.

**The octane equation (Blending Octane Values, not a simple average):**

Octane does **not** blend linearly by volume in real refineries — aromatics and volatility interact non-linearly. We approximate this with a **Blending Octane Value (BOV)** per component:

```
Pool Octane (RON) = Σ(Volume_i × BOV_i) / Σ(Volume_i)
```

| Component | BOV |
|---|---|
| Reformate | 91.0 + 9.0 × reformer_severity |
| FCC gasoline | 88.0 + 2.5 × fcc_severity |
| Hydrocracker gasoline | 80.0 (fixed — paraffinic, low octane) |
| Light naphtha (isomerate) | 82.0 |
| Coker naphtha | 70.0 |
| Alkylate | 94.0 |
| Purchased blendstock | 89.0 |

Notice hydrocracker gasoline has the *lowest* BOV of the major streams — it's high in volume but "dilutes" the pool. Reformate and alkylate are the octane workhorses. This is why the Reformer's severity setting matters so much to the final product spec.

**The diesel sulfur equation (simplified hydrotreating):**
```
diesel_sulfur_wt% = crude_sulfur_wt% × 0.001
```

**Hard specs (real US regulatory values):**
- Pool octane ≥ **87.0 RON**
- Diesel sulfur ≤ **0.0015 wt% (15 ppm — ULSD)**

---

## 3. The Six Couplings — Why This Is a Network, Not Six Calculators

No unit can be optimized alone. Here is exactly how they connect:

**Coupling 1 — CDU sets everyone's feed.** Furnace temperature and throughput determine how much of every downstream fraction exists. Push the furnace and you get more diesel/AGO, but the residue shrinks — meaning less feed for the VDU.

**Coupling 2 — CDU residue → VDU → conversion feed.** The only path to VGO (the FCC and Hydrocracker's feedstock) is through the VDU processing the CDU's residue. You cannot crack gas oil you never recovered.

**Coupling 3 — FCC and Hydrocracker share a finite feed pool.** The combined VGO+AGO pool is split between the FCC (draws first) and the Hydrocracker (gets what's left). A barrel routed to FCC becomes gasoline; the same barrel routed to the Hydrocracker becomes diesel (at a hydrogen cost). This is the central economic trade-off the Optimization Agent resolves every cycle.

**Coupling 4 — Reformer produces hydrogen; Hydrocracker consumes it.** This is the plant's hydrogen balance, and it's dynamic: `hydrocracker_h2_demand ≤ reformer_h2_production + external_makeup`. Raising Reformer severity doesn't just make better gasoline — it *frees up hydrogen* that lets the Hydrocracker run harder. This is the mechanism behind the plant's most elegant "counter-move."

**Coupling 5 — Severity has a ceiling, not a straight line.** In both FCC and Reformer, pushing severity raises octane but shrinks liquid volume and (in FCC's case) raises coke *quadratically*. There is a real optimum, not "more is always better."

**Coupling 6 — Everything converges at the Blending Pool, and specs are unforgiving.** You can maximize gasoline *volume* and still fail the octane floor if too much of it came from the low-BOV Hydrocracker stream. Volume and quality are different battles, and Unit 6 is where they're both won or lost.

---

## 4. Economics — What Makes a Move "Profitable"

The plant's single objective is **margin ($/bbl of crude processed)**:

```
Margin ($/day) = Revenue − Feedstock/Purchased-stock/Energy costs
Margin ($/bbl) = Margin ($/day) ÷ crude throughput
```

Revenue is driven by **crack spreads** — the price gasoline/diesel/jet sell for, above the cost of the crude that made them. At baseline, our diesel crack is set *higher* than the gasoline crack (reflecting 2025-26 market conditions), which is why several fault scenarios tempt the agents toward diesel-maximizing moves.

Marathon's real FY2025 refining margin was **$16.87/bbl** (before operating costs of ~$5.65/bbl). Our simulator is calibrated so its baseline reproduces this number closely — that calibration is what lets us claim the simulation is grounded in reality, not invented.

---

## 5. What the Agents Do With All This

- **Monitoring** reads the current numbers above and flags anything abnormal — an opportunity (money on the table) or a problem (a spec already broken).
- **Optimization** proposes specific knob changes (leading with Hydrocracker conversion), and its proposed numbers always come from actually running the equations above — never invented.
- **Safety** checks every hard limit in this manual against the proposal's *predicted* outcome, and only approves if all of them hold. If not, it explains exactly which one failed and by how much, and may suggest a fix (like "raise reformer severity to free up hydrogen").
- **The Operator Assistant** (you'll talk to this one directly) uses this exact manual, plus the live tools, to answer your questions — including "what happens if I change X?", grounded in the real equations, not a guess.

---

## 6. Quick Reference — All Knobs, Limits, and Specs

| Knob | Baseline | Min | Max |
|---|---|---|---|
| CDU throughput (bbl/day) | 235,000 | 180,000 | 250,000 |
| CDU furnace temp (°C) | 365 | 340 | 400 |
| VDU severity | 0.70 | 0.40 | 0.85 |
| FCC feed (bbl/day) | 52,000 | 20,000 | 80,000 |
| FCC severity | 0.65 | 0.40 | 0.90 |
| Reformer feed (bbl/day) | 41,000 | 15,000 | 45,000 |
| Reformer severity | 0.70 | 0.40 | 0.88 |
| Hydrocracker feed (bbl/day) | 23,000 | 10,000 | 45,000 |
| **Hydrocracker conversion ★lead★** | **0.75** | **0.60** | **0.98** |

| Hard Limit | Value |
|---|---|
| CDU furnace temp max | 370 °C |
| CDU throughput max | 250,000 bbl/day |
| VDU severity max | 0.85 |
| FCC feed max | 80,000 bbl/day |
| FCC coke make max | 6.0% |
| Reformer severity max | 0.88 |
| Hydrocracker conversion max | 0.98 |
| Hydrogen balance | demand ≤ supply (dynamic) |

| Product Spec | Value |
|---|---|
| Gasoline octane floor | 87.0 RON |
| Diesel sulfur cap | 0.0015 wt% (15 ppm, ULSD) |

---

## 7. Provenance Note

Structure and scale: Worley Consulting US refinery archetype (2024), mapped onto Marathon Petroleum's public FY2025 filings and its named Garyville hydrocracker (Shell Catalysts & Technologies white paper). Baseline yields: EIA U.S. Refinery Yield (Mar 2026). Product specs: real US regulatory values (87 AKI gasoline, ULSD 15 ppm). Unit transfer functions and blending indices are simplified, honestly-labeled engineering approximations — not proprietary plant data.

---

*This manual is the Operator Assistant's knowledge base. If the simulator's constants change, update the values here to match.*
