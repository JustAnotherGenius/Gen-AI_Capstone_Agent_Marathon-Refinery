# MARATHON PETROLEUM
## Refinery Process Optimization Advisor
### A Plain-Language Guide to How the Plant and the AI Agents Work Together

**Multi-Agent AI Advisory System**
*IIM Mumbai - PGPEX Co'27 Capstone Project*
*Prepared for operators, reviewers, and anyone unfamiliar with refining*

---

## Contents
1. Why This Document Exists
2. The Big Picture in One Diagram
3. How the Plant Works Unit by Unit
4. Why the Units Can't Be Optimized Alone
5. Does Our Simulated Plant Behave Like a Real One?
6. Meet the Four AI Agents
7. Watching the Agents Work: Two Real Examples
8. How You, the Operator, Use This System
9. Quick Reference Card

---

## 1. Why This Document Exists
This system simulates a real oil refinery and puts a team of AI "advisors" in charge of watching it, 24 hours a day. You do not need any background in chemical engineering to understand this guide — everything is explained from the ground up, with the actual formulas shown so you can see there's no magic involved, just arithmetic.

**In one sentence:** Crude oil goes in one end of six connected processing units, and gasoline, diesel, and jet fuel come out the other end — and because the units are all connected, a change in one place always changes something somewhere else. That's the whole reason the AI agents exist: to think through those connections faster and more consistently than a person could, while never overriding hard safety limits.

---

## 2. The Big Picture in One Diagram

```text
CRUDE OIL 
   │
   ▼
[1. CDU] ──(Lighter Fractions: Naphtha, Jet, Diesel)──► [6. BLENDING POOL] ──► FINAL PRODUCTS
   │                                                            ▲
   ├──(Heavy Residue)──► [2. VDU]                               │
   │                        │                                   │
   │                        ▼ (Shared Feed Pool)                │
   │                 ┌──────┴──────┐                            │
   │                 ▼             ▼                            │
   │              [3. FCC]    [5. HYDROCRACKER] ────────────────┤
   │                 │             ▲  (Main Control Lever)      │
   │                 ▼             │                            │
   │         (Gasoline Engine #1)  │                            │
   │                               │ (Hydrogen Coupling Gas)    │
   └────────(Heavy Naphtha)────► [4. REFORMER] ─────────────────┘