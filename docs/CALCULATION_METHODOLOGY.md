# Riser Design Analysis - Calculation Methodology

## Document Overview

This document provides a comprehensive explanation of all structural integrity checks, equations, calculation methods, and safety factors implemented in the Riser Design Analysis Tool per **API RP 1111** (3rd Edition, 1999) and **ASME B31.4/B31.8** standards.

---

## Table of Contents

1. [Position-Dependent Analysis Framework](#1-position-dependent-analysis-framework)
2. [Structural Integrity Checks (7 Checks)](#2-structural-integrity-checks)
   - [Check 1: Burst Pressure](#check-1-burst-pressure)
   - [Check 2: External Collapse](#check-2-external-collapse)
   - [Check 3: Propagation Buckling](#check-3-propagation-buckling)
   - [Check 4: Hoop Stress](#check-4-hoop-stress)
   - [Check 5: Combined Bending + Pressure](#check-5-combined-bending--pressure)
   - [Check 6: Longitudinal Tension](#check-6-longitudinal-tension)
   - [Check 7: Combined Loading](#check-7-combined-loading)
3. [Life Cycle Conditions (6 Conditions)](#3-life-cycle-conditions)
4. [Pipe Weight Calculations](#4-pipe-weight-calculations)
5. [Design Factors Summary](#5-design-factors-summary)
6. [Conservative Loading Strategy](#6-conservative-loading-strategy)

---

## 1. Position-Dependent Analysis Framework

The analysis evaluates **six position-dependent conditions** representing combinations of three life cycle stages and two critical positions:

### Three Life Cycle Stages

| Stage | Wall Thickness | Internal Pressure | Description |
|-------|----------------|-------------------|-------------|
| **Installation** | Nominal | 0 psi (empty) | Pipe lowering/installation operations |
| **Hydrotest** | Nominal | 1.25 × Design Pressure | Pressure testing phase |
| **Operation** | Nominal - Mill Tol - Corrosion | Design/Shut-in Pressure* | Normal service conditions |

\* **Pressure Strategy in Operation:**
- **Design pressure** used for: Burst, Hoop, Longitudinal, Combined checks
- **Shut-in pressure** used for: Collapse, Propagation checks (more conservative)

### Two Critical Positions

| Position | External Pressure | Axial Tension | Physical Condition |
|----------|-------------------|---------------|-------------------|
| **Top** | 14.7 psi (atmospheric) | Maximum (T_a = W_sub × L) | Sea surface - full suspended weight |
| **Bottom** | 14.7 + Hydrostatic psi | Zero (T_a = 0) | Mudline/seabed - supported |

### Why Position Matters

- **Top position** is conservative for:
  - Burst (less external to counteract internal)
  - Hoop stress (maximum internal)
  - Longitudinal tension (maximum self-weight)
  - Combined loading (tension-dominated)

- **Bottom position** is conservative for:
  - External collapse (maximum external pressure)
  - Propagation buckling (maximum net external)
  - Bending interaction (pressure-dominated)

### Buoyancy Consideration

All tension calculations use **void_submerged_weight** which inherently accounts for buoyancy:

```
void_submerged_weight = void_dry_weight - (ρ_water × V_displaced)
```

Where:
- `ρ_water` = 64 lb/ft³ (seawater) or 62.4 lb/ft³ (freshwater)
- `V_displaced` = π/4 × OD² × 1 ft

---

## 2. Structural Integrity Checks

Each of the six position-dependent conditions evaluates **7 structural checks**:

---

### Check 1: Burst Pressure

**Standard:** API RP 1111 Section 4.3.1

**Purpose:** Prevent pipe rupture from excessive internal pressure

#### Equation

**Burst Pressure Capacity:**
```
P_b = 0.45 × (SMYS + UTS) × ln(D / D_i)
```

Where:
- `P_b` = Burst pressure capacity (psi or ksi)
- `SMYS` = Specified Minimum Yield Strength (psi or ksi)
- `UTS` = Ultimate Tensile Strength (psi or ksi)
- `D` = Outer diameter (inches)
- `D_i` = Inner diameter = OD - 2×t (inches)
- `ln` = Natural logarithm

**Design Check Criterion:**
```
(P_i - P_o) ≤ f_d × f_e × f_t × P_b
```

Where:
- `P_i` = Internal design pressure (psi)
- `P_o` = External pressure (psi)
- `f_d` = Design factor (location-dependent)
- `f_e` = Weld joint efficiency factor
- `f_t` = Temperature derating factor

#### Safety Factors

**Design Factor (f_d):**
| Scenario Type | f_d | Basis |
|--------------|-----|-------|
| Riser | 0.75 | API RP 1111 |
| Flowline | 0.75 | API RP 1111 |
| Pipeline | 0.90 | API RP 1111 |

**Weld Factor (f_e):**
| Manufacturing | f_e | Note |
|---------------|-----|------|
| Seamless | 1.0 | No weld seam |
| ERW (Electric Resistance Welded) | 1.0 | Full penetration |
| DSAW (Double Submerged Arc Welded) | 0.85 | Longitudinal seam |
| SAW (Submerged Arc Welded) | 0.85 | Longitudinal seam |
| EFW (Electric Fusion Welded) | 0.85 | Longitudinal seam |

**Temperature Factor (f_t):**
- Standard offshore ambient temperature: **f_t = 1.0**

#### Calculation Method

1. Calculate inner diameter: `ID = OD - 2t`
2. Calculate D/D_i ratio
3. Compute burst pressure: `P_b = 0.45 × (SMYS + UTS) × ln(D/D_i)`
4. Calculate allowable burst: `P_allow = f_d × f_e × f_t × P_b`
5. Calculate net internal pressure: `ΔP = P_i - P_o`
6. Check criterion: `ΔP ≤ P_allow`
7. Calculate safety factor: `SF = P_allow / ΔP`

#### Special Cases

- **Empty pipe (Installation):** P_i = 0, resulting in negative ΔP → Burst check automatically passes (SF = ∞)
- **External > Internal:** Results in compressive hoop stress → Not a burst concern

---

### Check 2: External Collapse

**Standard:** API RP 1111 Section 4.3.2

**Purpose:** Prevent pipe collapse from external pressure exceeding internal pressure

#### Equations

**Step 1: Yield Collapse Pressure**
```
P_y = (2 × SMYS × (t/D)) / (1 - ν²)
```

**Step 2: Elastic Collapse Pressure**
```
P_e = (2 × E × (t/D)³) / [(1 - ν²) × (1 + 12δ²)]
```

**Step 3: Critical Collapse Pressure**

The collapse mode depends on P_y/P_e ratio:

- **If P_y/P_e ≥ 4.0:** *Yield Collapse*
  ```
  P_c = P_y
  ```

- **If P_y/P_e < 4.0:** *Elastic or Plastic Collapse*
  ```
  P_c = P_e × √(P_y / 2P_e) × [1 - P_y / 4P_e]
  ```

  Sub-modes:
  - P_y/P_e ≤ 1.5 → Elastic
  - 1.5 < P_y/P_e < 4.0 → Plastic

Where:
- `P_y` = Yield collapse pressure (ksi)
- `P_e` = Elastic collapse pressure (ksi)
- `P_c` = Critical collapse pressure (ksi)
- `t` = Wall thickness (inches)
- `D` = Outer diameter (inches)
- `E` = Young's modulus = 30,000 ksi (steel)
- `ν` = Poisson's ratio = 0.3 (steel)
- `δ` = Ovality = (D_max - D_min) / D_nominal (typically 0.005)

**Design Check Criterion:**
```
(P_o - P_i) ≤ f_o × P_c
```

Where:
- `P_o` = External pressure (ksi)
- `P_i` = Internal pressure (ksi)
- `f_o` = Collapse design factor

#### Safety Factors

**Collapse Factor (f_o):**
| Manufacturing | f_o | Basis |
|---------------|-----|-------|
| Seamless | 0.70 | API RP 1111 |
| ERW | 0.70 | API RP 1111 |
| DSAW | 0.60 | API RP 1111 |
| SAW | 0.60 | API RP 1111 |
| Cold Expanded | 0.60 | API RP 1111 |
| EFW | 0.60 | API RP 1111 |

#### Calculation Method

1. Calculate t/D ratio
2. Compute yield collapse: `P_y = 2SMYS(t/D) / (1-ν²)`
3. Compute elastic collapse: `P_e = 2E(t/D)³ / [(1-ν²)(1+12δ²)]`
4. Calculate P_y/P_e ratio to determine collapse mode
5. Compute critical collapse P_c based on mode
6. Calculate allowable collapse: `P_allow = f_o × P_c`
7. Calculate net external pressure: `ΔP = P_o - P_i`
8. Check criterion: `ΔP ≤ P_allow`
9. Calculate safety factor: `SF = P_allow / ΔP`

#### Special Cases

- **Internal ≥ External:** Net external pressure ≤ 0 → Collapse not a concern (SF = ∞)
- **High D/t ratio:** Tends toward elastic collapse mode
- **Low D/t ratio:** Tends toward yield collapse mode

---

### Check 3: Propagation Buckling

**Standard:** API RP 1111 Section 4.3.2.3

**Purpose:** Prevent buckle propagation along pipe length once initiated

#### Equation

**Propagation Pressure:**
```
P_p = 24 × SMYS × (t/D)^2.4
```

Where:
- `P_p` = Propagation pressure (ksi)
- `SMYS` = Specified Minimum Yield Strength (ksi)
- `t/D` = Wall thickness to diameter ratio

**Design Check Criterion:**
```
(P_o - P_i) ≤ 0.80 × P_p
```

Where:
- `P_o - P_i` = Net external pressure (ksi)
- 0.80 = Fixed safety factor per API RP 1111

#### Safety Factor

**Propagation Safety Factor:**
- **Fixed at 0.80** (or 80% of theoretical propagation pressure)
- **Not adjustable** - specified by API RP 1111 Section 4.3.2.3

#### Calculation Method

1. Calculate t/D ratio
2. Compute propagation pressure: `P_p = 24 × SMYS × (t/D)^2.4`
3. Calculate allowable pressure: `P_allow = 0.80 × P_p`
4. Calculate net external: `ΔP = P_o - P_i`
5. Check criterion: `ΔP ≤ P_allow`
6. Calculate safety factor: `SF = P_allow / ΔP`

#### Special Cases

- **Internal ≥ External:** Net external ≤ 0 → Propagation not a concern (SF = ∞)
- **Very thin wall (low t/D):** Results in low P_p due to 2.4 exponent
- **Thick wall (high t/D):** Results in high P_p, check easily satisfied

#### Physical Interpretation

Once a local buckle forms under external pressure, it can propagate along the pipe like a "zipper" at the propagation pressure P_p. This pressure is typically **lower** than the critical collapse pressure P_c, making it a critical design consideration for deepwater pipelines.

---

### Check 4: Hoop Stress

**Standard:** ASME B31.4 Section 402.3 / ASME B31.8

**Purpose:** Limit circumferential stress from internal pressure

#### Equation

**Barlow's Formula (Thin-Wall Approximation):**
```
S_H = (P_i × D) / (2 × t)
```

Where:
- `S_H` = Hoop stress (psi)
- `P_i` = **Internal gage pressure only** (psi)
- `D` = Outer diameter (inches)
- `t` = Wall thickness (inches)

**CRITICAL NOTE:** Per ASME B31.4 Section 402.3, hoop stress is calculated from internal design gage pressure **only**. External pressure is **NOT** subtracted. This differs from the net pressure approach used in burst/collapse checks.

**Design Check Criterion:**
```
S_H ≤ F × SMYS
```

Where:
- `F` = Design factor (code and location dependent)
- `SMYS` = Specified Minimum Yield Strength (psi)

#### Safety Factors

**Design Factor (F):**

**ASME B31.4 (Liquid Pipelines):**
| Location | F | Application |
|----------|---|-------------|
| Onshore | 0.72 | Standard |
| Offshore | 0.72 | Risers, flowlines |

**ASME B31.8 (Gas Pipelines):**
| Location Class | F | Population Density |
|----------------|---|-------------------|
| Class 1 | 0.72 | Rural, low density |
| Class 2 | 0.60 | Fringe areas |
| Class 3 | 0.50 | Suburban, high density |
| Class 4 | 0.40 | Urban, very high density |
| Offshore | 0.72 | Offshore structures |

**For Offshore Risers:** Typically use **F = 0.72** per ASME B31.4

Alternative design factors for risers by fluid type:
- Gas risers: F = 0.50 to 0.60
- Liquid risers: F = 0.60 to 0.72

#### Calculation Method

1. Calculate hoop stress: `S_H = (P_i × OD) / (2t)`
2. Calculate allowable stress: `S_allow = F × SMYS`
3. Check criterion: `S_H ≤ S_allow`
4. Calculate safety factor: `SF = S_allow / S_H`

#### Special Cases

- **Empty pipe (Installation):** P_i = 0 → S_H = 0 → Check automatically passes (SF = ∞)
- **D/t < 20:** Barlow's formula may not be applicable per ASME B31.4 note

#### Thick-Wall Alternative (Lame's Equation)

For thick-walled pipes (D/t < 20), use Lame's equation:
```
S_H = [(P_i × r_i² - P_o × r_o²) / (r_o² - r_i²)] + [(P_i - P_o) × r_i² × r_o²] / [r² × (r_o² - r_i²)]
```

However, most offshore risers have D/t > 20, so Barlow's formula is appropriate.

---

### Check 5: Combined Bending + Pressure

**Standard:** API RP 1111 Section 4.3.2.2

**Purpose:** Ensure pipe can withstand simultaneous bending and external pressure

#### Equations

**Allowable Bending Strain:**
```
ε_b = (2 × t × SMYS) / (D × E)
```

**Ovality Function:**
```
g(δ) = 1 - 3.5δ    (for δ ≤ 0.03)
```

Where:
- `δ` = Ovality = (D_max - D_min) / D_nominal
- Typically 0.005 for new pipe, up to 0.03 for used pipe

**Interaction Equation:**
```
(ε / ε_b) + [(P_o - P_i) / P_c] ≤ g(δ)
```

Where:
- `ε` = Applied bending strain (dimensionless)
- `ε_b` = Allowable bending strain (dimensionless)
- `P_o` = External pressure (ksi)
- `P_i` = Internal pressure (ksi)
- `P_c` = Critical collapse pressure (ksi)
- `g(δ)` = Ovality function (dimensionless, typically 0.9825 for δ=0.005)

#### Components

**Bending Component:**
```
Bending Ratio = ε / ε_b
```

**Pressure Component:**
```
Pressure Ratio = (P_o - P_i) / P_c
```

**Interaction Ratio:**
```
IR = Bending Ratio + Pressure Ratio
```

#### Safety Factor

```
SF = g(δ) / IR = g(δ) / [(ε/ε_b) + (P_o-P_i)/P_c]
```

Pass if: `SF ≥ 1.0` (equivalently, `IR ≤ g(δ)`)

#### Calculation Method

1. Calculate allowable bending strain: `ε_b = 2t×SMYS / (D×E)`
2. Calculate ovality function: `g(δ) = 1 - 3.5δ`
3. Calculate bending component: `ε / ε_b`
4. Get critical collapse from Check 2: `P_c`
5. Calculate pressure component: `(P_o - P_i) / P_c`
6. Calculate interaction ratio: `IR = bending + pressure components`
7. Check criterion: `IR ≤ g(δ)`
8. Calculate safety factor: `SF = g(δ) / IR`

#### Special Cases

- **Zero bending strain:** Reduces to pure collapse check
- **Internal > External:** Pressure component becomes negative → Favorable (helps resist bending)
- **IR ≤ 0:** Extremely favorable condition (SF = ∞)

#### Physical Interpretation

Bending causes localized ovalization (flattening), which reduces collapse resistance. This interaction equation ensures the pipe can safely handle both effects simultaneously. Internal pressure helps "stiffen" the pipe against bending, while external pressure exacerbates bending-induced ovalization.

---

### Check 6: Longitudinal Tension

**Standard:** API RP 1111 Section 4.3.1.1

**Purpose:** Limit axial tension from self-weight and pressure end-cap effects

#### Equation

**Effective Longitudinal Tension:**
```
T_eff = T_a - P_i × A_i + P_o × A_o
```

Where:
- `T_eff` = Effective tension accounting for pressure end-cap effects (lb)
- `T_a` = Applied axial tension from self-weight (lb) - **Position Dependent**
- `P_i` = Internal pressure (psi)
- `P_o` = External pressure (psi)
- `A_i` = Internal cross-sectional area = π/4 × ID² (in²)
- `A_o` = External cross-sectional area = π/4 × OD² (in²)

**Yield Tension:**
```
T_y = SMYS × A_steel
```

Where:
- `A_steel` = Steel cross-sectional area = π/4 × (OD² - ID²) (in²)

**Design Check Criterion:**
```
T_eff ≤ 0.60 × T_y
```

#### Position-Dependent Applied Tension

**Top Position (Sea Surface):**
```
T_a = W_submerged × L
```
Where:
- `W_submerged` = Void submerged weight (lb/ft) - already includes buoyancy
- `L` = Riser length (ft)

**Bottom Position (Mudline/Seabed):**
```
T_a = 0
```
(Pipe rests on seabed, no self-weight tension)

#### Safety Factor

**Fixed design factor:** 0.60 (60% of yield tension)

```
SF = Allowable Tension / Effective Tension
   = (0.60 × T_y) / T_eff
```

Pass if: `SF ≥ 1.0`

#### Calculation Method

1. Calculate pipe weights using effective wall thickness
2. Get void submerged weight: `W_sub` (includes buoyancy)
3. Determine position-dependent applied tension:
   - Top: `T_a = W_sub × L`
   - Bottom: `T_a = 0`
4. Calculate cross-sectional areas: `A_i, A_o, A_steel`
5. Calculate pressure end-cap forces:
   - Internal force (reduces tension): `F_i = P_i × A_i`
   - External force (increases tension): `F_o = P_o × A_o`
6. Calculate effective tension: `T_eff = T_a - F_i + F_o`
7. Calculate yield tension: `T_y = SMYS × A_steel`
8. Calculate allowable: `T_allow = 0.60 × T_y`
9. Check criterion: `T_eff ≤ T_allow`
10. Calculate safety factor: `SF = T_allow / T_eff`

#### Special Cases

- **Bottom position:** T_a = 0, check may pass easily unless high pressure differential
- **Compression:** T_eff ≤ 0 → Check not applicable (SF = ∞, marked as "Compression N/A")
- **High internal pressure:** Reduces effective tension (favorable)
- **High external pressure:** Increases effective tension (unfavorable)

#### Buoyancy Note

The `void_submerged_weight` calculation already accounts for buoyancy:
```
W_submerged = W_dry - (ρ_water × Volume_displaced)
            = W_dry - (64 lb/ft³ × π/4 × OD²/144)
```

This is the **true suspended weight in water**, not the dry weight.

---

### Check 7: Combined Loading

**Standard:** API RP 1111 Section 4.3.1.2

**Purpose:** Ensure pipe can withstand simultaneous pressure and longitudinal loading

#### Equation

**Combined Load Interaction:**
```
√[(P_i - P_o)² / P_b²  +  (T_eff / T_y)²] ≤ Design Factor
```

Where:
- `P_i - P_o` = Net pressure (burst if positive, collapse if negative) (psi)
- `P_b` = Burst pressure capacity (psi)
- `T_eff` = Effective longitudinal tension (lb) - **Position Dependent**
- `T_y` = Yield tension (lb)
- Design Factor = Condition-dependent (0.90 to 0.96)

#### Components

**Pressure Component:**
```
PC = (P_i - P_o) / P_b
```

**Tension Component:**
```
TC = T_eff / T_y
```

**Combined Ratio:**
```
CR = √(PC² + TC²)
```

#### Safety Factors

**Design Factor (by Condition):**
| Condition | Design Factor | Application |
|-----------|---------------|-------------|
| Operation | 0.90 | Normal operating loads |
| Hydrotest | 0.96 | Test pressure loads |
| Installation | 0.96 | Extreme/installation loads |

```
SF = Design Factor / Combined Ratio
```

Pass if: `SF ≥ 1.0` (equivalently, `CR ≤ Design Factor`)

#### Calculation Method

1. Get burst pressure P_b from Check 1
2. Get longitudinal tension T_eff, T_y from Check 6 (position-dependent)
3. Calculate pressure component: `PC = (P_i - P_o) / P_b`
4. Calculate tension component: `TC = T_eff / T_y`
5. Calculate combined ratio: `CR = √(PC² + TC²)`
6. Determine design factor based on condition
7. Check criterion: `CR ≤ Design Factor`
8. Calculate safety factor: `SF = Design Factor / CR`

#### Special Cases

- **Top position:** High tension component dominates
- **Bottom position:** Low/zero tension, pressure component dominates
- **CR = 0:** No loading → SF = ∞
- **Empty pipe (Installation, Top):** High tension, zero pressure difference

#### Physical Interpretation

This is the **most comprehensive check**, combining:
1. Pressure loading (burst/collapse tendency)
2. Longitudinal loading (tension from weight + pressure end-caps)

The interaction is a root-sum-square (√(PC² + TC²)), meaning both effects contribute quadratically. This is more realistic than simple addition, as it reflects the von Mises stress combination.

---

## 3. Life Cycle Conditions

### Three Life Cycle Stages × Two Positions = Six Conditions

| # | Condition | Position | Wall Thickness | Internal P | External P | Axial Tension |
|---|-----------|----------|----------------|------------|------------|---------------|
| 1 | Installation | Top | Nominal | 0 | Atmospheric | Maximum |
| 2 | Installation | Bottom | Nominal | 0 | Atm + Hydrostatic | Zero |
| 3 | Hydrotest | Top | Nominal | 1.25×Design | Atmospheric | Maximum |
| 4 | Hydrotest | Bottom | Nominal | 1.25×Design | Atm + Hydrostatic | Zero |
| 5 | Operation | Top | Nom - Tol - Corr | Design/Shut-in* | Atmospheric | Maximum |
| 6 | Operation | Bottom | Nom - Tol - Corr | Design/Shut-in* | Atm + Hydrostatic | Zero |

\* Operation uses design pressure for Burst/Hoop/Longitudinal/Combined, shut-in pressure for Collapse/Propagation

### Wall Thickness Treatment

**Installation & Hydrotest:**
- Use **nominal wall thickness**
- No corrosion allowance applied
- No mill tolerance applied
- Rationale: New pipe at full thickness

**Operation:**
- Apply **mill tolerance** (typically -12.5%)
- Apply **corrosion allowance** (design-specific, e.g., 0.08")
- Effective WT = Nominal × (1 - tol%) - corrosion
- Rationale: End-of-life conservative case

### Pressure Strategy

**Pressure Application by Check Type:**

**For All Checks:**
- Uses **single water_depth** value for external pressure calculation
- External pressure = 14.7 psi (atmospheric) + Hydrostatic pressure

**For Hoop Stress:**
- Uses internal pressure only (external not considered per ASME B31.4)

---

## 4. Pipe Weight Calculations

**Standard:** API RP 1111 Appendix A

### Weight Types

#### 1. Void (Empty) Pipe

**Dry Weight:**
```
W_void_dry = ρ_steel × A_steel × 1 ft
           = 490 lb/ft³ × π/4 × (OD² - ID²) ft²
```

**Submerged Weight:**
```
W_void_sub = W_void_dry - ρ_water × A_outer
           = W_void_dry - ρ_water × π/4 × OD² ft²
```

#### 2. Flooded Pipe (Water-Filled)

**Dry Weight:**
```
W_flood_dry = W_void_dry + ρ_water × A_void
            = W_void_dry + ρ_water × π/4 × ID² ft²
```

**Submerged Weight:**
```
W_flood_sub = W_flood_dry - ρ_water × A_outer
            = W_steel_dry (steel weight only, water cancels out)
```

#### 3. Product-Filled Pipe (Fluid-Filled)

**Dry Weight:**
```
W_prod_dry = W_void_dry + ρ_fluid × A_void
           = W_void_dry + (SG_fluid × ρ_freshwater) × π/4 × ID² ft²
```

**Submerged Weight:**
```
W_prod_sub = W_prod_dry - ρ_seawater × A_outer
```

### Material Properties

| Property | Value | Unit |
|----------|-------|------|
| Steel density | 490 | lb/ft³ |
| Seawater density | 64 | lb/ft³ |
| Freshwater density | 62.4 | lb/ft³ |

### Usage in Design Checks

- **Longitudinal tension (Check 6):** Uses `W_void_sub` (empty pipe submerged weight)
- **Buoyancy:** Already accounted for in submerged weights
- **Axial stress:** `σ_axial = (W × L) / A_steel`

---

## 5. Design Factors Summary

### Complete Design Factor Table

| Check | Parameter | Value | Manufacturing/Type | Standard |
|-------|-----------|-------|-------------------|----------|
| **Burst** | f_d | 0.75 | Riser/Flowline | API RP 1111 |
| | f_d | 0.90 | Pipeline | API RP 1111 |
| | f_e | 1.0 | Seamless, ERW | API RP 1111 |
| | f_e | 0.85 | DSAW, SAW, EFW | API RP 1111 |
| | f_t | 1.0 | Ambient temp | API RP 1111 |
| **Collapse** | f_o | 0.70 | Seamless, ERW | API RP 1111 |
| | f_o | 0.60 | DSAW, SAW, Cold Exp | API RP 1111 |
| **Propagation** | (fixed) | 0.80 | All | API RP 1111 |
| **Hoop** | F | 0.72 | Offshore (B31.4) | ASME B31.4 |
| | F | 0.50-0.72 | Class/Location | ASME B31.8 |
| **Bending** | g(δ) | 1-3.5δ | Ovality dependent | API RP 1111 |
| **Longitudinal** | (fixed) | 0.60 | All | API RP 1111 Sec 4.3.1.1 |
| **Combined** | DF | 0.90 | Operation | API RP 1111 Sec 4.3.1.2 |
| | DF | 0.96 | Hydrotest | API RP 1111 Sec 4.3.1.2 |
| | DF | 0.96 | Installation/Extreme | API RP 1111 Sec 4.3.1.2 |

---

## 6. External Pressure Calculation

The analysis uses a **single water depth** value for all checks:

### External Pressure Calculation

**For Conventional Risers:**
```
P_external = 14.7 psi (atmospheric) + ρ_water × g × h / 144
           = 14.7 + (64 lb/ft³ × depth_ft / 144)
```

Where:
- 14.7 psi = Atmospheric pressure at sea level
- ρ_water = 64 lb/ft³ (seawater density)
- depth_ft = water_depth_m × 3.28084 (meters to feet conversion)
- 144 = conversion factor from psf to psi

**For PIP (Pipe-in-Pipe) Systems:**
```
P_external = Design annulus pressure (specified)
```

### Position-Dependent External Pressure

**Top Position (Sea Surface):**
```
P_external = 14.7 psi (atmospheric only)
```
- No hydrostatic component at sea surface
- Conservative for burst checks (less external to counteract internal)

**Bottom Position (Mudline/Seabed):**
```
P_external = 14.7 + Hydrostatic psi
```
- Full hydrostatic pressure at water depth
- Conservative for collapse/propagation checks (maximum external pressure)

### Example Calculation

**For 40m water depth:**
- depth_ft = 40 × 3.28084 = 131.23 ft
- Hydrostatic = 64 lb/ft³ × 131.23 ft / 144 = 58.3 psi
- **Top:** P_external = 14.7 psi
- **Bottom:** P_external = 14.7 + 58.3 = 73.0 psi

---

## 7. Units and Conventions

### Pressure Units
- Internal/external pressures: **psi** (pounds per square inch)
- Material strengths: **ksi** (kilo-psi = 1000 psi) or **psi**
- Conversion: 1 ksi = 1000 psi

### Dimension Units
- Outer diameter (OD): **inches**
- Wall thickness (t): **inches**
- Water depth: **meters** (converted to feet internally)
- Riser length: **meters** (converted to feet for weight calculations)

### Weight Units
- Pipe weight: **lb/ft** (pounds per linear foot)
- Forces/tensions: **lb** (pounds) or **kips** (1 kip = 1000 lb)

### Stress Units
- Stress: **psi** or **ksi**
- Hoop stress, longitudinal stress: **psi**

### Strain Units
- Bending strain: **dimensionless** (ε = 0.001 = 0.1%)

---

## 8. Pass/Fail Criteria Summary

| Check | Pass Criterion | Safety Factor Definition |
|-------|----------------|--------------------------|
| Burst | (P_i - P_o) ≤ f_d × f_e × f_t × P_b | SF = (f_d × f_e × f_t × P_b) / (P_i - P_o) |
| Collapse | (P_o - P_i) ≤ f_o × P_c | SF = (f_o × P_c) / (P_o - P_i) |
| Propagation | (P_o - P_i) ≤ 0.80 × P_p | SF = (0.80 × P_p) / (P_o - P_i) |
| Hoop | S_H ≤ F × SMYS | SF = (F × SMYS) / S_H |
| Bending | (ε/ε_b) + (P_o-P_i)/P_c ≤ g(δ) | SF = g(δ) / IR |
| Longitudinal | T_eff ≤ 0.60 × T_y | SF = (0.60 × T_y) / T_eff |
| Combined | √[(P/P_b)² + (T/T_y)²] ≤ DF | SF = DF / CR |

**Overall Pass:** All 7 checks must pass for each of 6 conditions (42 total checks per wall thickness)

---

## 9. References

1. **API RP 1111** (3rd Edition, 1999): Design, Construction, Operation, and Maintenance of Offshore Hydrocarbon Pipelines (Limit State Design)
   - Section 4.3.1: Burst Pressure
   - Section 4.3.1.1: Longitudinal Tension
   - Section 4.3.1.2: Combined Loading
   - Section 4.3.2: External Collapse
   - Section 4.3.2.2: Combined Bending and Pressure
   - Section 4.3.2.3: Propagation Buckling
   - Appendix A: Pipe Weight Calculations

2. **ASME B31.4**: Pipeline Transportation Systems for Liquids and Slurries
   - Section 402.3: Hoop Stress Design (Barlow's Formula)

3. **ASME B31.8**: Gas Transmission and Distribution Piping Systems
   - Design factors for gas pipelines

4. **ASME B36.10M**: Welded and Seamless Wrought Steel Pipe
   - Standard pipe dimensions and wall thicknesses

---

## Document Revision History

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2025-12-18 | Initial comprehensive methodology documentation |

---

**End of Document**
