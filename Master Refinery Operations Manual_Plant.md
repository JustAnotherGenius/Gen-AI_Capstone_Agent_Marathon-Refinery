# MARATHON PETROLEUM PROCESS OPERATIONS
## MASTER REFINERY OPERATIONS MANUAL: HIGH-CONVERSION ARCHITECTURE

* **Document No:** REF-OPS-MAN-2026-REV5
* **Target Audience:** Control Room Operators, Field Technicians, Operations Engineers
* **Project Context:** Clean Air Task Force / Worley Consulting "Refinery of the Future" Deployment Framework
* **Status:** CONTROLLED DOCUMENT

---

## CONTEXT & HOW TO SCALE THIS DOCUMENT
**Operational Blueprint Notice:** This document serves as the exhaustive master framework and technical operational baseline designed to populate a 100+ page comprehensive operating manual for the asset. To fully achieve the target volume, expand each unit's section using site-specific Piping and Instrumentation Diagrams (P&IDs), Emergency Shutdown (ESD) Cause-and-Effect charts, vendor-specific equipment data sheets, and local environmental permit mandates.

---

## SECTION 1: CRUDE SEPARATION LAYER (CDU / VDU)

### 1.1 Crude Distillation Unit (CDU)

#### 1.1.1 Process Objective & Governing Theory
The primary objective of the CDU is the physical separation of raw crude oil into distinct hydrocarbon fractions based on their relative boiling points at atmospheric pressure. This is the foundational separation step before catalytic conversion or final product blending.

$$\text{Raw Crude} \rightarrow \text{[Desalter (Emulsion Breaking)]} \rightarrow \text{(Pre-Flash Tower)} \rightarrow \text{[Furnace (340°C - 400°C)]} \rightarrow \text{[Atmospheric Fractionator]}$$

#### 1.1.2 Stream Routing Matrix
The following table delineates the exact operational tracking for all CDU streams:

| Stream Name | Phase | Source Unit / Tankage | Destination Unit PNGRB+ 1 | Operational Critical Quality Metric |
| :--- | :--- | :--- | :--- | :--- |
| **Raw Crude Oil** | Liquid | Unit Battery Limit | Crude Tank Farm | API Gravity, BS&W, Total Sulfur |
| **Light Ends** | Vapor/Liq | Tower Overhead | Saturated Gas Plant | Vapor Pressure ($RVP$), ratio |
| **Straight-Run Naphtha** | Liquid | Overhead Receiver | Naphtha Hydrotreater (NHT) | Final Boiling Point (FBP), Nitrogen |
| **Kerosene** | Liquid | Upper Side-Draw | Merox Treater / DHT | Freeze Point, Flash Point, Mercaptans |
| **Atmospheric Gas Oil** | Liquid | Middle Side-Draw | Diesel Hydrotreater (DHT) | Cetane Index, Sulfur, Viscosity |
| **Atmospheric Residue** | Liquid | Column Bottoms | Vacuum Distillation Unit (VDU) | Concarbon Residue, Nickel/Vanadium |
| **Sour Water** | Liquid | Reflux Drums | Sour Water Stripper (SWS) | $\text{H}_2\text{S}$ and $\text{NH}_3$ weight percentages |

#### 1.1.3 Detailed Standard Operating Procedures (SOP)

##### Phase I: Cold Circulation & Leak Testing
* Align the pump suctions from crude storage through the heat exchanger train to the atmospheric fractionator bottoms.
* Establish a low-flow cold crude loop at ambient temperature. Pressurize the loop to check for flange leaks, valve packing weeping, and instrument manifold integrity.
* Activate the desalting wash-water injection pumps to establish a steady 5% to 10% water-to-crude ratio upstream of the mixing valve.

##### Phase II: Warm Circulation & Fired Heater Soft-Start
* Transition the loop to warm circulation by introducing low-pressure steam to the shell-side of the preheat exchangers.
* Purge the fired heater firebox with instrument air or utility steam to remove any residual combustibles. Verify gas-free status using an explosive gas meter.
* Light the pilot burners sequentially. Establish a minimum continuous pass flow through the furnace tubes to prevent localized thermal cracking or hot spots.
* Raise the coil outlet temperature (COT) gradually at a controlled rate of 20°C to 25°C per hour to prevent thermal stress on the furnace refractory and header boxes.

##### Phase III: Tower Line-Up, Fractionation, & Stabilization
* As the furnace COT approaches 340°C to 400°C, vapor-liquid separation initiates within the flash zone of the atmospheric fractionator.
* Monitor the tower top temperature closely. Establish overhead reflux pump operations to control the top tower temperature, ensuring light naphtha does not carry over into the gas plant feed.
* Introduce stripping steam to the bottom of the column and individual side-cut steam strippers to maximize the separation of light ends from the diesel and kerosene cuts.
* Once the products meet lab specifications (Flash point for kerosene, distillation 95% point for diesel), line up individual streams to downstream hydrotreaters.

#### 1.1.4 Troubleshooting & Advanced Process Control (APC)
* **[High Desalter Pressure Drop]** Check for Water Injection Valve Failure or Heavy Sludge.
* **[Tower Top Temperature Spike]** Increase Reflux Flow Immediately to Prevent Heavy End Carryover.

* **Symptom: High Desalter Water Carryover**
  * *Root Cause:* Excess mixing valve differential pressure, degraded demulsifier chemical dosing, or a failure in the electrical grid transformer inside the desalter vessel.
  * *Immediate Action:* Reduce the mixing valve differential pressure across the grid. Check the Buckman emulsion breaker chemical dosing pump stroke. Verify the high-voltage electrostatic grid current readings on the control panel.
* **Symptom: Fractionator Column Flooding (High Differential Pressure)**
  * *Root Cause:* Excessive stripping steam injection or high internal liquid traffic due to over-refluxing.
  * *Immediate Action:* Cut stripping steam flow by 15%. Slightly reduce the internal reflux rate while tracking product flash points.

#### 1.1.5 Safety, Health, and Environmental (SHE) Guardrails
> ⚠️ **CRITICAL OPERATIONAL RISK:** Low-temperature hydrogen attack and ammonium chloride salt deposition occur near the tower top overhead line. Continuous water wash must be maintained to mitigate catastrophic corrosion. Never exceed a fired heater COT of 400°C to prevent rapid thermal decomposition and coking inside the furnace tubes.

---

### 1.2 Vacuum Distillation Unit (VDU)

#### 1.2.1 Process Objective & Governing Theory
The VDU processes heavy atmospheric residue from the CDU bottoms. Operating under deep vacuum conditions (15 to 50 mm Hg absolute pressure), it lowers the boiling points of high-molecular-weight hydrocarbons. This allows the separation of valuable Vacuum Gas Oils (VGO) from heavy vacuum residue without reaching temperatures that cause severe thermal cracking and furnace tube coking.

$$\text{Atmospheric Residue} \rightarrow \text{[Vacuum Fired Heater (400°C - 425°C)]} \rightarrow \text{[Vacuum Distillation Column]} \rightarrow \begin{cases} \text{LVGO / MVGO / HVGO} \\ \text{Vacuum Residue} \end{cases}$$

#### 1.2.2 Process Streams & Target Destinations
* **Light Vacuum Gas Oil (LVGO):** Routed directly to the VGO Hydrocracker or FCC Feed Hydrotreater Unit.
* **Heavy Vacuum Gas Oil (HVGO):** Routed to the Fluid Catalytic Cracker (FCC) or Hydrocracker for conversion into transportation fuels.
* **Vacuum Residue (VR):** Routed to the Delayed Coker Unit (DCU), Visbreaker, or Asphalt Blowing Unit depending on the regional archetype configuration.

#### 1.2.3 Technical Troubleshooting Matrix

| Operational Deviation | Probable Root Cause | Field/Console Remedial Action |
| :--- | :--- | :--- |
| **Loss of Vacuum Pressure** | Ejector steam pressure drop; condenser fouling; leaking vacuum breaker valve. | Verify motive steam pressure to the ejectors; switch to backup ejector train; clear non-condensable vents. |
| **Dark HVGO Product Color** | Entrainment of vacuum residue (column entrainment / tray damage). | Reduce furnace COT slightly; increase overflash grid wash-oil rate to wash down heavy residue. |
| **High Vacuum Furnace Tube Skin Temp** | Internal coke buildup inside the furnace coils. | Initiate online steam-air decoking or reduce throughput to limit heat flux; schedule pigging during turnaround. |

---

## SECTION 2: LIGHT ENDS & NAPHTHA UPGRADING LAYER

### 2.1 Naphtha Hydrotreater (NHT) & Naphtha Splitter

#### 2.1.1 Core Process Description
The NHT removes sulfur, nitrogen, and organometallic trace contaminants from full-range naphtha cuts via catalytic hydrodesulfurization over fixed-bed cobalt-molybdenum (CoMo) catalysts. Clean feed is mandatory for downstream operations because sulfur and nitrogen are severe poisons to the precious metal (Platinum/Rhenium) catalysts used in the Continuous Catalytic Reformer (CCR).

$$\text{Raw Naphtha} + \text{Hydrogen Gas} \rightarrow \text{[Fired Charge Heater]} \rightarrow \text{[Fixed Bed Reactor]} \rightarrow \text{[High-Pressure Separator]} \rightarrow \text{[Naphtha Splitter]}$$

The downstream Naphtha Splitter fractionates the desulfurized full-range naphtha into:
* **Light Hydrotreated Naphtha (C5 and lighter):** Sent directly to the Isomerization (ISOM) Unit to convert straight-chain paraffins to high-octane branched isomers.
* **Heavy Hydrotreated Naphtha:** Sent to the CCR Reforming Unit to produce high-octane aromatic blendstocks.

#### 2.1.2 Naphtha Hydrotreater Operating Envelope Controls
**[NHT PROCESS VARIABLE WINDOW]**
* **Pressure Window:** 35–50 barg (Normal) | *Low Limit:* 0 barg (Coke risk) | *High Limit:* 70 barg (Design limit)
* **Temperature Window:** 300°C–360°C (Normal) | *Low Limit:* 150°C (Incomplete Desulfurization) | *High Limit:* 400°C (Catalyst Deactivation/Reactions)

* **Reactor Operating Pressure:** Maintain tightly between 35 to 50 barg to ensure adequate hydrogen partial pressure, preventing catalyst coking.
* **Weighted Average Bed Temperature (WABT):** Maintain between 300°C and 360°C. Increasing the temperature balances natural catalyst deactivation over the cycle length, but going too high causes undesired cracking and gas formation.
* **Splitter Bottoms Benzene Precursor Control:** Regulate the Naphtha Splitter cutpoint temperature to ensure benzene precursors (such as cyclohexane and methylcyclopentane) are directed overhead into the Light Naphtha stream. This minimizes benzene formation in the downstream Reformer, helping meet strict environmental specifications for finished gasoline.

---

### 2.2 Continuous Catalytic Reformer (CCR)

#### 2.2.1 Operational Mechanism & Conversion Theory
The CCR transforms low-octane heavy naphtha (paraffins and naphthenes) into high-octane aromatic molecules like benzene, toluene, and xylene (BTX). This reaction takes place across a series of reactors over a moving platinum catalyst bed. The primary reactions—naphthene dehydrogenation and paraffin dehydrocyclization—are highly endothermic, requiring interheaters between reaction stages to restore the target reaction temperature.

$$\text{Heavy Naphtha} \rightarrow \text{[Heater 1} \rightarrow \text{Reactor 1]} \rightarrow \text{[Heater 2} \rightarrow \text{Reactor 2]} \rightarrow \text{[Heater 3} \rightarrow \text{Reactor 3]} \rightarrow \text{[Debutanizer]} \rightarrow \begin{cases} \text{Reformate Product} \\ \text{High Purity Hydrogen Gas} \end{cases}$$

#### 2.2.2 Reactor-Regenerator Loop Management
Because of the high-severity reactions, a small amount of carbon (coke) deposits continuously on the catalyst, which deactivates active sites. The CCR system avoids shutdowns by utilizing a continuous loop that transfers spent catalyst to a dedicated regeneration tower. Here, the coke is burned off under strict, low-oxygen conditions before the catalyst is re-chlorinated, reduced with hydrogen, and returned to the primary reactor train.

$$\text{Spent Catalyst From Reactor Bottom} \rightarrow \text{[Regeneration Tower (Controlled } \text{O}_2 \text{ Burn)]} \rightarrow \text{[Re-chlorination Zone]} \rightarrow \text{[Reduction Zone]} \rightarrow \text{Back to Reactor Top}$$

#### 2.2.3 Troubleshooting & Safety Interlocks
* **Emergency Interlock - High Oxygen in Regeneration Burn Zone:** If oxygen levels spike above the safety threshold, an automatic nitrogen purge trips. This prevents runaway thermal damage to the internal metallurgy of the regeneration tower.
* **Moisture-to-Chlorine Ratio:** Monitor the catalyst chloride levels daily via lab samples. An imbalance causes catalyst sintering (loss of active surface area) or high downstream equipment corrosion from hydrochloric acid ($\text{HCl}$) carryover.

---

### 2.3 Alkylation Unit (Sulfuric Acid Catalyst)

#### 2.3.1 Process Summary & Chemical Dynamics
The Alkylation unit combines light olefin streams (primarily butenes from the FCC unit) with isobutane over a highly concentrated sulfuric acid ($\text{H}_2\text{SO}_4$, 98 wt%) catalyst. This highly exothermic reaction produces alkylate, a high-octane, low-vapor-pressure paraffinic blending component free of sulfur and olefins.

$$\text{Isobutane Recycle} + \text{Olefin Feed} \rightarrow \text{[Refrigerated Contactor Reactor]} \rightarrow \begin{cases} \text{Spent Acid to Regeneration Unit} \\ \text{Hydrocarbon Effluent to Fractionation [Acid Settler Vessel]} \end{cases}$$

#### 2.3.2 Critical Control Parameters & Operating Matrix

| Control Parameter | Target Operating Specification | Failure Consequence / Process Impact |
| :--- | :--- | :--- |
| **Isobutane-to-Olefin (I:O) Ratio** | 10:1 to 12:1 (Internal Reactor Ratio) | Low ratios cause polymerization reactions, leading to heavy "acid oils" and rapid acid dilution. |
| **Acid Concentration** | 89% to 92 wt% Minimum | Dropping below 85 wt% runs a severe risk of an "acid runaway" explosion due to rapid exothermic polymerization. |
| **Reaction Temperature** | 4°C to 10°C | Higher temperatures increase oxidized byproduct formation and accelerate overall asset corrosion rates. |

---

## SECTION 3: MIDDLE & HEAVY DISTILLATES HYDROPROCESSING LAYER

### 3.1 Diesel Hydrotreater (DHT)

#### 3.1.1 Process Summary & Flow Architecture
The DHT processes straight-run diesel, light cycle oil (LCO), and coker gas oils to remove sulfur and nitrogen compounds down to ultra-low levels (Ultra-Low Sulfur Diesel, or ULSD, requires $<10\text{ ppm}$ sulfur).

$$\text{Raw Diesel/LCO Mix} \rightarrow \text{[Fired Charge Heater]} \rightarrow \text{[Fixed Bed Hydrotreating Reactor]} \rightarrow \text{[High Pressure Separator]} \rightarrow \text{[Stripper Column]} \rightarrow \text{[Product Vacuum Dryer]} \rightarrow \text{Finished ULSD Storage}$$

#### 3.1.2 Detailed Operating Procedures
* **Startup & Catalyst Pre-Sulfiding:** The unit must undergo initial pre-sulfiding using a sulfur donor chemical like dimethyl disulfide (DMDS) injected into a breakthrough gas loop. This transforms the metal oxide catalyst into its active metal-sulfide form ($\text{CoMoS}$).
* **Normal Operations:** Adjust the reactor Weighted Average Bed Temperature (WABT) to match the feed blend sulfur levels. For example, increase the heat when processing high-sulfur cracked stocks like LCO from the FCC or coker gas oil.
* **Emergency Shutdown (ESD) - Reactor Thermal Runaway:** If any bed thermocouple registers a temperature spike greater than 5°C per minute, activate the emergency high-pressure hydrogen quench valves between the catalyst beds immediately to cool the reactor and arrest the runaway reaction.

---

### 3.2 VGO Hydrocracker Unit (HCU)

#### 3.2.1 Deep Process Theory & Configuration Modes
The HCU cracks heavy, high-boiling vacuum gas oils into high-value light products like aviation jet fuel, ultra-low sulfur diesel, and high-quality naphtha using hydrogen and dual-functional catalysts (combining an acidic cracking support with hydrogenating metals).

* **Single-Stage Mode:** Achieves 65% to 70% conversion per pass; remaining unconverted oil (UCO) is routed to the FCC or fuel oil pool.
* **Two-Stage Configuration:** Maximizes conversion efficiency up to 95% to 98%. The first stage removes sulfur and nitrogen compounds, which act as temporary poisons to the cracking catalyst. An inter-stage separation system then strips away hydrogen sulfide ($\text{H}_2\text{S}$) and ammonia ($\text{NH}_3$). This allows the clean fractionator bottoms to enter an optimized cracking environment in the second-stage reactor loop.

$$\text{[Stage 1: Hydrotreating \& Partial Cracking]} \rightarrow \text{[Inter-stage Separation (H}_2\text{S/NH}_3\text{ Strip)]} \rightarrow \text{[Stage 2: High Severity Cracking Loop]} \rightarrow \text{[Fractionation System]}$$

#### 3.2.2 Yield Maximization Matrix
**[HYDROCRACKER YIELD TUNING]**
* *Low Temperature / Low Conversion Mode:* Maximize Ultra-Low Sulfur Diesel.
* *High Temperature / High Conversion Mode:* Maximize Petrochemical Naphtha & LPG.

Operators must adjust the catalyst bed temperature profiles based on the target product slate:
* **Jet Fuel / Diesel Maximization Mode:** Operate at moderate cracking temperatures with lower conversion per pass. This preserves mid-boiling-range molecules and maximizes high-smoke-point kerosene/jet fuel fractions.
* **Naphtha / Petrochemical Feed Mode:** Increase the reactor bed temperatures to raise conversion severity. This breaks down mid-distillates into light and heavy naphtha streams destined for downstream chemical production.

---

## SECTION 4: RESIDUE UPGRADING & CATALYTIC CRACKING LAYER

### 4.1 Fluid Catalytic Cracker (FCC / RFCC)

#### 4.1.1 Fluidized Reaction Mechanism & Principles
The FCC unit converts heavy vacuum gas oils (or atmospheric residues in RFCC designs) into high-octane gasoline blendstocks and light olefinic gases like propylene. The process uses a continuous, fluidized-bed circulation loop between a vertical riser reactor and a catalyst regenerator.

$$\text{Feedstock} + \text{Hot Regenerated Catalyst} \rightarrow \text{[Riser Cracking (Endothermic, 2-4 sec)]} \rightarrow \text{[Cyclone Separation]} \rightarrow \begin{cases} \text{Vapor to Main Fractionator} \\ \text{Spent Catalyst to Regenerator (Coke Burn-off)} \end{cases}$$

The reaction is endothermic, but the system maintains a heat balance by using the energy generated in the regenerator, where coke deposits are burned off the catalyst using high-pressure air.

#### 4.1.2 Main Fractionator and Slurry System Operation
The cracked vapors enter the bottom of the Main Fractionator column, which separates the mixture into light gases, cracked naphtha, light cycle oil (LCO), and heavy FCC slurry oil.
* **Slurry Backwash Operations:** The heavy slurry bottoms contain entrained catalyst fines carried over from the reactor cyclones. Operators must maintain the slurry backwash filter system at baseline flow rates to prevent these abrasive fines from fouling downstream product storage tanks or heat exchangers.

---

### 4.2 FCC Naphtha Hydrotreater (Selective Desulfurization)

#### 4.2.1 Operating Constraints & Catalyst Chemistry
FCC cracked gasoline is highly olefinic, which provides a major portion of its octane value. If this stream is routed to a standard Naphtha Hydrotreater (NHT), the harsh operating conditions saturate the olefins, leading to a severe drop in octane rating.

To prevent this, a dedicated selective desulfurization unit (such as Axens Prime-G+ technology) is deployed. This configuration utilizes a two-step process:
1. **Selective Hydrogenation Unit (SHU):** A specialized reactor saturates highly reactive di-olefins to prevent polymer fouling downstream, while simultaneously shifting light sulfur species into heavier fractions via mercaptan sulfur alkylation.
2. **Splitter and Selective Hydro-Desulfurizer (SHDS):** The SHU product is fractionated. The olefin-rich light cracked naphtha (LCN) goes straight to the gasoline pool or alkylation unit with minimal treatment. The heavy cracked naphtha undergoes targeted desulfurization in the SHDS reactor, removing stubborn sulfur compounds while preserving mono-olefins to maintain octane levels.

$$\text{FCC Naphtha Feed} \rightarrow \text{[SHU Reactor (Di-olefin Saturation)]} \rightarrow \text{[Naphtha Splitter Column]} \rightarrow \begin{cases} \text{Light Cut: Direct to Gasoline Pool} \\ \text{Heavy Cut: to Selective SHDS Reactor} \end{cases}$$

---

### 4.3 Delayed Coker Unit (DCU)

#### 4.3.1 Process Objective & Governing Theory
The DCU is a severe thermal cracking unit used to upgrade heavy, low-value vacuum residue into lighter liquid hydrocarbons (coker naphtha and coker gas oils), leaving behind a solid, high-carbon petroleum coke byproduct.

$$\text{Vacuum Residue Feed} \rightarrow \text{[Coker Fractionator Bottoms]} \rightarrow \text{[Multi-Pass Coker Fired Heater]} \rightarrow \text{[Active Coke Drum]} \rightarrow \begin{cases} \text{Vapors back to Fractionator} \\ \text{Solid Coke remains in Drum} \end{cases}$$

To prevent fouling, the feed is heated rapidly in a multi-pass furnace to high temperatures, delaying the actual coking reaction until the liquid enters the coke drums.

#### 4.3.2 24-Hour Drum Batch Cycle Management Procedure
* **[Drum A: Online/Coking (24 Hours)]** $\rightarrow$ Vapors to Main Fractionator.
* **[Drum B: Offline Decoking Sequence]** $\rightarrow$ Steam Purge $\rightarrow$ Water Quench $\rightarrow$ Hydraulic Jet Cutting.

* **Switching Drums:** When the online coke drum reaches its target solid coke level, the console operator opens the automated switch valves. This redirects the hot furnace effluent to the companion offline drum, maintaining continuous unit operation.
* **Steam Purging & Cooling:** The full drum is isolated and steam-purged to recover residual hydrocarbon vapors back to the fractionator. Water is then introduced gradually to quench and cool the hot coke bed safely.
* **Hydraulic Decoking:** Once cooled and vented, the top and bottom heads of the drum are removed. A hydraulic boring tool using high-pressure jet water pumps cuts a center pilot hole through the coke bed, followed by a final cleanout cut from top to bottom. The dislodged coke drops into the dewatering pit for crushing and transport.

---

## SECTION 5: UTILITIES, TREATMENT, & INFRASTRUCTURE LAYER

### 5.1 Hydrogen Plant (Steam Methane Reforming)

#### 5.1.1 Technical Process Description
The Hydrogen Plant supplies high-purity makeup hydrogen to the refinery's hydroprocessing units. It utilizes Steam Methane Reforming (SMR) combined with high-temperature catalytic water-gas shift reactions, followed by final purification in a Pressure Swing Adsorption (PSA) system.

$$\text{Natural Gas / Off-Gas Feed} \rightarrow \text{[Hydrotreating \& ZnO Bed]} \rightarrow \text{[SMR Reformer Furnaces]} \rightarrow \text{[Shift Reactor (CO} \rightarrow \text{CO}_2\text{)]} \rightarrow \text{[PSA Multi-Bed Adsorbers]} \rightarrow \text{High-Purity H}_2$$

#### 5.1.2 Operational Control Loop Matrix
* **Feedstock Pre-treatment:** Raw feed gases pass through a hydrotreating catalyst and zinc oxide (ZnO) beds to remove sulfur, chlorine, and trace metals. This step is critical to prevent poisoning the downstream nickel-based reforming catalyst.
* **Steam-to-Carbon (S/C) Ratio:** Maintain the $S/C$ ratio tightly above 2.8 to 3.0. Dropping below this minimum threshold triggers rapid carbon deposition (coking) on the reformer catalyst, causing tube hotspots and potential catastrophic rupture.
* **PSA Cycle Coordination:** The PSA unit runs continuous cycles across multiple adsorption beds at a constant temperature. Impurities ($\text{CO}, \text{CO}_2, \text{CH}_4$) are adsorbed at high pressures and desorbed at lower pressures, producing a continuous stream of 99.99%+ pure hydrogen. The rejected tail gas is routed back to the reformer furnace to be used as fuel.

---

### 5.2 Amine Regeneration Unit (ARU)

#### 5.2.1 Gas Treating and Stripping Theory
Refinery gases contain hydrogen sulfide ($\text{H}_2\text{S}$), which must be removed before the gases can be safely used as fuel gas. The ARU uses chemical solvents like MDEA or DEA to absorb $\text{H}_2\text{S}$ from light hydrocarbon streams in lean amine contactor towers. The resulting "rich amine" is then routed to a central stripping column, where steam heat breaks the chemical bonds, generating a concentrated sour acid gas stream destined for the Sulfur Recovery Unit (SRU).

$$\text{Rich Amine From Plant Contactors} \rightarrow \text{[Flash Drum (Gas/Oil Skim)]} \rightarrow \text{[Amine Stripper Tower via Reboiler Steam Heat]} \rightarrow \begin{cases} \text{Overhead Acid Gas to SRU} \\ \text{Bottoms Lean Amine Recycled to Contactors} \end{cases}$$

#### 5.2.2 Process Automation & Troubleshooting
* **Amine Foaming Mitigation:** Hydrocarbon liquid carryover or particulate contamination causes amine foaming inside the absorber columns, leading to liquid carryover and poor treating efficiency.
* **Corrective Actions:** If foaming occurs, reduce gas throughput immediately, line up the mechanical carbon filters, and inject an approved anti-foam chemical additive.

---

### 5.3 Sour Water Stripper (SWS)

#### 5.3.1 Process Mechanics & Stripping Parameters
The SWS uses low-pressure steam stripping to remove dissolved hydrogen sulfide ($\text{H}_2\text{S}$) and ammonia ($\text{NH}_3$) from contaminated refinery process waters.

$$\text{Process Sour Water Intermittents} \rightarrow \text{[Sour Water Storage \& Degassing Tank]} \rightarrow \text{[SWS Stripping Column via Bottom Reboiler]} \rightarrow \begin{cases} \text{Overhead Acid Gas to SRU} \\ \text{Bottoms Stripped Water to Desalter Recycle} \end{cases}$$

#### 5.3.2 Environmental Compliance & Water Recycling
* **Stripped Water Quality:** Maintain steam reboiler heat inputs to achieve a target specification of less than $10\text{ ppm}$ residual $\text{H}_2\text{S}/\text{NH}_3$ in the stripped water bottoms.
* **Resource Conservation Loop:** Route the hot, stripped water back to the Crude Distillation Unit (CDU) desalters to be used as wash water. This integration minimizes the refinery's fresh water consumption and reduces overall wastewater treatment plant loading.

---

### 5.4 Sulfur Recovery Unit (SRU) - Claus Process

#### 5.4.1 Process Stages & Conversion Principles
The SRU converts toxic acid gases from the amine units and sour water strippers into stable, non-hazardous elemental sulfur[cite: 3].

$$\text{Acid Gas Feed} \rightarrow \text{[Thermal Stage Burner \& WHB (950°C - 1350°C)]} \rightarrow \text{[Multi-Stage Catalytic Reheaters \& Claus Reactors]} \rightarrow \text{[Liquid Sulfur Condensers]} \rightarrow \text{Tail Gas Treatment} \text{[cite: 3]}$$

* **Thermal Stage:** Acid gases are combusted with air in the reaction furnace at high temperatures (950°C to 1350°C), converting one-third of the $\text{H}_2\text{S}$ into sulfur dioxide ($\text{SO}_2$)[cite: 3]:
  $$2\text{H}_2\text{S} + 3\text{O}_2 \rightarrow 2\text{SO}_2 + 2\text{H}_2\text{O}$$
* **Catalytic Stage:** The remaining $\text{H}_2\text{S}$ reacts with the generated $\text{SO}_2$ over an activated alumina catalyst bed at lower temperatures (200°C to 300°C) to yield elemental sulfur[cite: 3]:
  $$2\text{H}_2\text{S} + \text{SO}_2 \rightarrow 3\text{S} + 2\text{H}_2\text{O}$$

#### 5.4.2 Critical Process Operations
* **Air-to-Acid Gas Ratio Control:** The primary process control loop adjusts combustion air rates to maintain a strict 2:1 ratio of $\text{H}_2\text{S}$-to-$\text{SO}_2$ in the downstream catalytic stages. Deviations from this ratio lead to low sulfur recovery efficiencies and accelerate emission breakthrough at the stack.
* **Tail Gas Treatment Integration:** The tail gas from the final Claus condenser is sent to a Tail Gas Treatment Unit (TGTU)[cite: 3]. The TGTU uses a chemical absorption loop to capture remaining sulfur species, boosting the asset's total sulfur recovery efficiency above 99.9%[cite: 3].

---

## SECTION 6: INTEGRATED ARCHITECTURE & PROCESS CHEMICAL ENHANCEMENT

### 6.1 Buckman Process Chemical Additives Management
Maximizing refinery run-lengths and reliability requires the automated dosing of specialized process chemical additives across the key processing blocks[cite: 3]:

| Processing Block | Application | Additive Family Designation | Primary Field Objective & Operational Impact[cite: 3] |
| :--- | :--- | :--- | :--- |
| **CDU Desalting Train** | De-emulsifiers & Water-Wetting Agents | Buckman Delta-S | Accelerates brine separation; minimizes oil carryover in effluent water[cite: 3]. |
| **Crude Unit Overhead Line** | Filming Corrosion Inhibitors | Buckman Shield-Pro | Forms a protective chemical barrier on cold overhead lines to prevent $\text{HCl}$ and acid attack[cite: 3]. |
| **VGO/Residue Feeds** | Antifoulants & Dispersants | Buckman Clean-Flow | Retards polymer degradation and coke fouling inside preheat exchanger tubes[cite: 3]. |
| **Hydroprocessing Reactors** | Catalyst Pre-sulfiding Auxiliaries | Buckman Sulf-Activ | Controls reactor bed heating profiles during DMDS sulfur breakthrough phases[cite: 3]. |
| **Delayed Coker Furnaces** | Coke Minimization Modifiers | Buckman Coke-Stop | Alters the surface properties of heavy furnace tubes to reduce coking rates and extend run lengths[cite: 3]. |

---

### 6.2 Regional Configuration Archetypes
* **[USA GULF COAST]** Gasoline Focused: High FCC + CCR Moving Catalyst Train Capacity[cite: 3].
* **[GCC REGION]** Export/Petchem Integrated: Max Hydrocracking Heavy Naphtha Yields[cite: 3].
* **[EUROPE ARCH]** Diesel & Heavy Infrastructure Driven: High HCU Capacity + Asphalt Production Blending[cite: 3].
* **[SINGAPORE]** High Conversion Clean Export: Integrated ARDS + Residue FCC Complex[cite: 3].

Refinery operations must adapt to the regional asset archetype configuration[cite: 3]:
* **USA Gulf Coast Archetype:** Driven primarily by high gasoline demand[cite: 3]. Operations prioritize high-severity FCC cracking and continuous catalyst regeneration (CCR) reforming to maximize high-octane blending components[cite: 3].
* **GCC Export Archetype:** Large-scale, high-efficiency complexes designed to optimize both transportation fuels and petrochemical feedstocks[cite: 3]. Heavy naphtha cuts are split between gasoline production and direct chemical feedstock sales[cite: 3].
* **European Archetype:** Geared primarily toward high-yield diesel production[cite: 3]. Heavy residues are typically diverted to asphalt blowing units rather than delayed cokers due to regional market demand and strict environmental constraints[cite: 3].
* **Singapore Archetype:** High-conversion, complex export assets[cite: 3]. These designs use Atmospheric Residue Desulfurization (ARDS) units to treat heavy tower bottoms before feeding them into a Residue Fluid Catalytic Cracker (RFCC), providing maximum flexibility to adjust operations based on international market pricing[cite: 3].

---

## SECTION 7: CORE SAFETY PROTOCOLS & INTEGRATED EMERGENCY HANDBOOK

### 7.1 Plant-Wide Emergency Shutdown (ESD) Hierarchy
The refinery's safety infrastructure operates on a tiered Emergency Shutdown (ESD) logic system designed to fail-safe automatically if major process variables deviate from safe limits.

* **[ESD LEVEL 1: TOTAL SITE ISOLATION]**
* **[ESD LEVEL 2: PROCESS UNIT SHUTDOWN]**
* **[ESD LEVEL 3: RECYCLE LOOP/EQUIPMENT ISOLATION]**

* **ESD Level 3 (Equipment Isolation):** Isolates specific equipment blocks, such as a charge pump or compressor, when local sensors detect a fault (e.g., high pump bearing vibrations or a compressor seal oil failure). The main unit remains online via bypass lines or surge drum capacity.
* **ESD Level 2 (Process Unit Shutdown):** Safely isolates an entire unit block (e.g., the NHT or FCC) by tripping the primary fired heaters, closing the main feed valves, and redirecting hydrocarbon process streams to the flare system. This level triggers automatically during a utility failure (such as a total loss of instrument air or power) or a major process upset.
* **ESD Level 1 (Total Site Isolation):** Reserved for catastrophic events. It activates the main refinery isolation valves, cuts incoming raw crude feed lines at the battery limits, shuts down all non-essential utility systems, and prioritizes power to fire water pump networks and emergency command facilities.

---

### 7.2 Permit to Work (PTW) & Safe Isolation Mandates
No operator or technician may perform maintenance, hot work, or equipment entry without an approved Permit to Work (PTW).

> 🛑 **OPERATIONAL MANDATE:** Every piece of process equipment containing hazardous hydrocarbons, high temperatures, or high pressures must follow double-block-and-bleed isolation protocols, combined with mechanical blind installation, before maintenance handover.

$$\text{[PROCESS LIQUID UPSTREAM]} \rightarrow \text{[VALVE 1: CLOSED]} \rightarrow \text{[BLEED VALVE: OPEN TO FLARE]} \rightarrow \text{[VALVE 2: CLOSED]} \rightarrow \text{[ISOLATED EQUIPMENT (Verify Zero Pressure Here)]}$$

* **Double Block and Bleed (DBB):** Close two independent block valves in series and open the intermediate bleed valve to a safe drainage system or flare line. Field operators must verify zero pressure at the bleed point to ensure the upstream valve is holding.
* **Isolation Blinding:** Slide a solid steel spectacle blind or skillet blank into the flange downstream of the DBB setup to create a positive, physical barrier against hydrocarbon migration.
* **Atmospheric Verification:** For vessel or confined space entry, testing with calibrated gas detectors must confirm a "Gas-Free" status. Internal oxygen levels must measure between 19.5% and 21.0% by volume, with flammable vapors at 0% Lower Explosive Limit (LEL) and toxic components ($\text{H}_2\text{S}, \text{CO}$) below occupational exposure limits.

---

### FINAL OPERATIONS NOTE
To finalize this document into a custom 100+ page asset operating manual, insert your local facility's specific tagging lists, localized P&ID drawings, control room DCS screen layouts, and regional regulatory compliance schedules directly into the structural templates provided above. Use these standardized chapters to maintain consistent training benchmarks across all shift operations teams.

***

**Master Refinery Operations Manual REF-OPS-MAN-2026-REV5**
*Prepared by Gemini AI | Formatted for Marathon Petroleum / IIM Mumbai PGPEX Co'27 Capstone*