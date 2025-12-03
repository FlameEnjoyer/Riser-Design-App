# RISER DESIGN ANALYSIS TOOL
**API RP 1111 & ASME B31.4/B31.8 Compliance Checker**

## Quick Start

### 1. Choose Your Type
Open `input_data.json` and set the `type` field for each scenario:
- **`"Pipeline"`** - Buried/protected pipelines (f_d = 0.90)
- **`"Flowline"`** - Subsea flowlines on seabed (f_d = 0.75)
- **`"Riser"`** - Vertical risers with dynamic loads (f_d = 0.75)

See **[TYPE_SELECTION_GUIDE.md](TYPE_SELECTION_GUIDE.md)** for detailed guidance.

### 2. Configure Scenarios
Edit `input_data.json` with your design parameters:

```json
{
  "scenarios": [
    {
      "name": "My Pipeline Design",
      "type": "Pipeline",  // ← CHOOSE TYPE HERE
      "riser_type": "",     // Optional: TTR, SCR, Rigid (documentation only)
      "manufacturing": "DSAW",
      "geometry": {
        "od_inches": 20.0,
        "ovality": 0.005,
        "corrosion_allowance_inches": 0.125,
        "mill_tolerance_percent": 12.5
      },
      "material": {
        "grade": "X-65",
        "smys_ksi": 65.0,
        "uts_ksi": 77.0
      },
      "loads": {
        "design_internal_pressure_psi": 2500.0,
        "bending_strain": 0.0001,
        "depth_lat_m": 100.0,
        "depth_hat_m": 105.0
      }
    }
  ]
}
```

### 3. Run Analysis
```powershell
python main.py
```

### 4. Review Results
The tool will:
- ✅ Check all life cycle conditions (Installation, Hydrotest, Operation)
- ✅ Verify burst, collapse, propagation, bending, and hoop criteria
- ✅ Recommend minimum wall thickness
- ✅ Show safety factors for each check

---

## Type Selection Impact

### What Changes Based on Type?

| Type | Design Factor (f_d) | Wall Thickness | Use Case |
|------|---------------------|----------------|----------|
| **Pipeline** | 0.90 | **Thinnest** | Buried, protected routes |
| **Flowline** | 0.75 | Moderate | Subsea, on seabed |
| **Riser** | 0.75 | Moderate | Vertical, dynamic loads |

**Important:** 
- Type affects **burst pressure calculations only** via design factor
- Bending strain often drives riser thickness regardless of type
- All other checks (collapse, propagation, hoop) use same formulas

---

## Understanding Safety Factors

### Normal Values (SF ≥ 1.0)
- **SF = 1.0** - Minimum acceptable (just meets code)
- **SF = 1.5** - Good margin
- **SF = 2.0+** - Excellent margin

### Special Cases
- **SF = ∞** - Reverse loading (favorable condition, no threat)
  - Example: Internal pressure exceeds external during hydrotest
  - Collapse/propagation can't occur when pipe is pressurized outward
- **N/A** - Not applicable (e.g., burst check when pipe is empty)

### When Does SF = ∞ Appear?

**Hydrotest & Operation Conditions:**
- **Collapse/Propagation:** When `P_internal > P_external`
  - The pipe is being pushed *outward*, not crushed
  - No collapse threat → infinite safety factor
  
- **Combined Bending:** When pressure term is strongly favorable
  - Interaction ratio becomes negative
  - Combined loading is beneficial, not threatening

**Installation Condition:**
- Pipe is empty (P_internal = 0)
- All checks see real external/bending demand
- No infinite SFs (except burst/hoop show N/A)

---

## Life Cycle Conditions

### 1. Installation
- Empty pipe (P_internal = 0)
- External pressure from seawater
- Higher bending strain during laying
- Uses **nominal wall thickness** (no corrosion/tolerance)

### 2. Hydrotest
- Elevated internal pressure (1.25× design)
- External seawater pressure
- Design bending strain
- Uses **nominal wall thickness**

### 3. Operation
- Design internal pressure
- External seawater pressure
- Design bending strain
- Uses **corroded wall thickness** (nominal - mill tolerance - corrosion allowance)

**Critical:** Tool finds thickness that passes **ALL THREE** conditions.

---

## File Structure

```
├── main.py                      # Main analysis engine
├── input_data.json              # YOUR CONFIGURATION (edit this!)
├── input_data_examples.json     # Example scenarios (Pipeline/Flowline/Riser)
├── TYPE_SELECTION_GUIDE.md      # Detailed type selection guidance
├── README_USAGE.md              # This file
│
├── calcs_burst.py               # Burst pressure (uses f_d based on type)
├── calcs_collapse.py            # External collapse
├── calcs_propagation.py         # Propagation buckling
├── calcs_bending.py             # Combined bending + pressure
├── calcs_hoop.py                # Hoop stress (ASME B31.4/B31.8)
│
└── asme_b36_10.py               # Standard pipe dimensions
```

---

## Workflow Example

### Scenario: Design a Subsea Export Pipeline

**Step 1:** Choose type based on installation
- Pipeline will be **buried in trench**
- Stable environment, low bending
- **Decision:** `"type": "Pipeline"` → f_d = 0.90

**Step 2:** Configure in `input_data.json`
```json
{
  "name": "24-inch Export Pipeline",
  "type": "Pipeline",
  "riser_type": "",
  "manufacturing": "DSAW",
  "geometry": {
    "od_inches": 24.0,
    "corrosion_allowance_inches": 0.125,
    "mill_tolerance_percent": 12.5
  },
  "material": {
    "grade": "X-65",
    "smys_ksi": 65.0,
    "uts_ksi": 77.0
  },
  "loads": {
    "design_internal_pressure_psi": 2000.0,
    "bending_strain": 0.0001,
    "depth_lat_m": 50.0,
    "depth_hat_m": 52.0
  }
}
```

**Step 3:** Run analysis
```powershell
python main.py
```

**Step 4:** Review output
```
Type: Pipeline
Manufacturing: DSAW

Check                            Safety Factor   Status
------------------------------------------------------------------------
1. Burst Pressure                2.34            PASS   ← f_d=0.90 used
2. External Collapse             ∞               PASS   ← Reverse loading
3. Propagation Buckling          ∞               PASS   ← Reverse loading
4. Combined Bending+Pressure     5.12            PASS
5. Hoop Stress                   2.10            PASS

OVERALL STATUS                                   PASS

RECOMMENDED THICKNESS: 0.375 inches
```

**Step 5:** Interpret results
- Burst is controlling check (lowest SF = 2.34)
- Higher f_d (0.90) allows thinner wall vs. Flowline/Riser
- Collapse/propagation show ∞ because internal pressure > external
- Design is acceptable with good margin

---

## Comparing Types for Same Design

### Same Configuration, Different Types:

| Type | f_d | Min. Thickness | Burst SF | Result |
|------|-----|----------------|----------|--------|
| Pipeline | 0.90 | **0.375"** | 2.34 | More economical |
| Flowline | 0.75 | **0.438"** | 2.81 | Conservative |
| Riser | 0.75 | **0.438"** | 2.81 | Conservative |

**Lesson:** Type selection directly impacts required thickness via design factor.

---

## Common Questions

### Q1: When should I use Pipeline vs. Flowline?
**A:** Use `Pipeline` only when:
- Physically buried or trenched
- Protected by rock dump/concrete coating
- Code allows higher design factor
- Client/regulator approves

Use `Flowline` for subsea pipelines on seabed without burial.

### Q2: Why is my riser SF = ∞ during operation?
**A:** Your internal pressure exceeds external pressure. The pipe can't collapse when it's being pressurized outward. This is normal and favorable.

### Q3: Does `riser_type` (TTR, SCR, etc.) affect calculations?
**A:** No, `riser_type` is **documentation only**. Only `type` (Pipeline/Flowline/Riser) affects design factors.

### Q4: Why is bending often the controlling check for risers?
**A:** Risers experience high bending strains from:
- Wave-induced motion (floating platforms)
- Current loading
- Vessel offset
- Installation curvature

Even though `type: Riser` uses same f_d as Flowline (0.75), the higher `bending_strain` drives thicker walls.

### Q5: Can I add a custom type?
**A:** Current implementation supports:
- `Pipeline` (f_d = 0.90)
- `Flowline` (f_d = 0.75)
- `Riser` (f_d = 0.75)

To add custom types, edit `calcs_burst.py` → `get_design_factor()` function.

---

## Design Factor Summary (API RP 1111 Sec 4.3.1)

| Application | Design Factor (f_d) | Notes |
|-------------|---------------------|-------|
| Pipelines (buried/protected) | 0.90 | Higher factor = thinner wall |
| Flowlines (subsea/exposed) | 0.75 | Conservative for seabed exposure |
| Risers (dynamic/vertical) | 0.75 | Same as flowline, but bending often governs |
| High consequence areas | 0.60-0.70 | Reduce if required by jurisdiction |

**Note:** Tool uses standard API RP 1111 factors. Verify with project codes.

---

## Tips for Optimization

1. **Start with correct type**
   - Don't use `Pipeline` for unburied applications
   - Client/code may mandate conservative factors

2. **Review all SFs, not just pass/fail**
   - SF = 1.01 technically passes but has no margin
   - Target SF ≥ 1.5 for robust design

3. **Check controlling condition**
   - Tool reports detailed results for Operation (corroded state)
   - This is usually the critical condition

4. **Adjust bending strain if unrealistic**
   - Very high strains (>0.5%) may indicate routing issues
   - Consider span supports or route changes

5. **Use examples for validation**
   - `input_data_examples.json` shows typical configurations
   - Compare your SFs to example cases

---

## References & Standards

- **API RP 1111** (4th Edition) - Design, Construction, Operation, and Maintenance of Offshore Hydrocarbon Pipelines (Limit State Design)
- **ASME B31.4** - Pipeline Transportation Systems for Liquids and Slurries
- **ASME B31.8** - Gas Transmission and Distribution Piping Systems
- **ASME B36.10M** - Welded and Seamless Wrought Steel Pipe

---

## Support

For questions about:
- **Type selection** → Read [TYPE_SELECTION_GUIDE.md](TYPE_SELECTION_GUIDE.md)
- **Example configurations** → See `input_data_examples.json`
- **Calculation methods** → Check individual `calcs_*.py` files (well-documented)
- **Standard dimensions** → Reference `asme_b36_10.py`

---

**Version:** 1.0  
**Last Updated:** December 2025  
**Compliance:** API RP 1111 (4th Ed.), ASME B31.4/B31.8
