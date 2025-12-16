# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Riser Design Analysis Tool** that performs structural integrity calculations for offshore steel risers and pipelines per **API RP 1111** (3rd Edition, 1999) and **ASME B31.4/B31.8** codes.

It evaluates wall thickness requirements across **six position-dependent conditions**:
- **Installation** (Top/Bottom positions): Empty pipe during installation
- **Hydrotest** (Top/Bottom positions): Pressure testing at 1.25× design
- **Operation** (Top/Bottom positions): Normal operation with corrosion

Each condition evaluates **7 structural checks**:
1. Burst Pressure (API RP 1111 Sec 4.3.1)
2. External Collapse (API RP 1111 Sec 4.3.2)
3. Propagation Buckling (API RP 1111 Sec 4.3.2.3)
4. Hoop Stress (ASME B31.4 Sec 402.3)
5. Combined Bending + Pressure (API RP 1111 Sec 4.3.2.2)
6. Longitudinal Tension (API RP 1111 Sec 4.3.1.1) - **Position-dependent**
7. Combined Loading (API RP 1111 Sec 4.3.1.2) - **Position-dependent**

## Commands

### Run the Streamlit Web Application
```bash
streamlit run app.py
```

### Run the CLI Analysis Tool
```bash
python main.py
```
Reads configuration from `input_data.json` and outputs analysis report to console.

### Run Validation Tests
```bash
python test_all_risers.py
```
Tests all 24 riser configurations from `riser_database.json` against all calculation modules.

### Run Individual Calculation Module Tests
```bash
python calcs_burst.py
python calcs_collapse.py
python calcs_hoop.py
python calcs_propagation.py
python calcs_bending.py
python calcs_weight.py
```
Each module has `if __name__ == "__main__"` test cases.

## Architecture

### Two Entry Points
- **`app.py`**: Streamlit web UI with interactive inputs, Team 8 reference data, and tabbed results display. Uses `LifeCycleAnalyzer` class for calculations.
- **`main.py`**: CLI tool that reads from `input_data.json`, iterates standard ASME B36.10 wall thicknesses, and finds minimum passing thickness.

### Calculation Modules (Shared by Both Entry Points)
| Module | Standard | Purpose |
|--------|----------|---------|
| `calcs_burst.py` | API RP 1111 Sec 4.3.1 | Burst pressure check: `(Pi - Po) <= fd * fe * ft * Pb` |
| `calcs_collapse.py` | API RP 1111 Sec 4.3.2 | External collapse: yield/elastic/plastic modes |
| `calcs_propagation.py` | API RP 1111 Sec 4.3.2.3 | Propagation buckling: `Pp = 35 * SMYS * (t/D)^2.5` |
| `calcs_bending.py` | API RP 1111 Sec 4.3.2.2 | Combined bending + pressure interaction |
| `calcs_hoop.py` | ASME B31.4 Sec 402.3 | Hoop stress: `SH = Pi * D / (2 * t)` |
| `calcs_weight.py` | API RP 1111 Appendix A | Pipe weights: void/flooded/product-filled |

### Reference Data Modules
- **`asme_b36_10.py`**: ASME B36.10M pipe schedule database. Maps OD to available wall thicknesses and schedule names. Key function: `get_standard_thicknesses(od)`.

### Position-Dependent Life Cycle Conditions

All checks are performed for **six conditions** (3 life cycle stages × 2 riser positions):

| Condition | Position | Wall Thickness | Internal Pressure | External Pressure | Axial Tension |
|-----------|----------|----------------|-------------------|-------------------|---------------|
| **Installation** | Top | Nominal | 0 (empty) | 14.7 psi (atmospheric) | Maximum (full weight) |
| | Bottom | Nominal | 0 (empty) | 14.7 + hydrostatic | Zero (mudline support) |
| **Hydrotest** | Top | Nominal | 1.25 × Design | 14.7 psi (atmospheric) | Maximum (full weight) |
| | Bottom | Nominal | 1.25 × Design | 14.7 + hydrostatic | Zero (mudline support) |
| **Operation** | Top | Nominal - Mill Tol - Corrosion | Design/Shut-in* | 14.7 psi (atmospheric) | Maximum (full weight) |
| | Bottom | Nominal - Mill Tol - Corrosion | Design/Shut-in* | 14.7 + hydrostatic | Zero (mudline support) |

**\*Operation Internal Pressure Strategy (Check-Type Dependent):**
- **Design pressure** used for: Burst, Hoop, Longitudinal, Combined
- **Shut-in pressure** used for: Collapse, Propagation

This dual-pressure approach ensures conservative sizing for all failure modes.

### Position-Dependent Analysis

**Top Position (Sea Surface):**
- External pressure: 14.7 psi (atmospheric only)
- Longitudinal tension: Maximum (T_a = void_submerged_weight × riser_length)
- Conservative for: Burst, hoop, longitudinal checks
- Physical basis: Top of riser must support entire suspended weight

**Bottom Position (Mudline):**
- External pressure: 14.7 + hydrostatic psi (full water depth)
- Longitudinal tension: Zero (T_a = 0, supported by seabed)
- Conservative for: Collapse, propagation checks
- Physical basis: Bottom rests on mudline with no self-weight tension

**Buoyancy Consideration:**
All tension calculations use `void_submerged_weight` which already accounts for buoyancy:
```
void_submerged_weight = void_dry_weight - (water_density × displaced_volume)
```

## Key Data Structures

### Input JSON Schema (for main.py)
```json
{
  "project_info": { "hydrotest_factor": 1.25, "water_density_seawater": 64.0 },
  "scenarios": [{
    "name": "...",
    "type": "Riser|Pipeline|Flowline",
    "manufacturing": "Seamless|ERW|DSAW",
    "geometry": { "od_inches": 16.0, "ovality": 0.005, "corrosion_allowance_inches": 0.08, "mill_tolerance_percent": 12.5 },
    "material": { "grade": "X-52", "smys_ksi": 52.0, "uts_ksi": 66.0, "modulus_of_elasticity_ksi": 30000.0, "poisson_ratio": 0.3 },
    "loads": { "design_internal_pressure_psi": 1400.0, "depth_hat_m": 45.0, "depth_lat_m": 40.0, "bending_strain": 0.001 }
  }]
}
```

### Design Factors (from API RP 1111)
- Burst: `fd = 0.75` (Riser/Flowline), `0.90` (Pipeline)
- Collapse: `fo = 0.70` (Seamless/ERW), `0.60` (DSAW/Cold Expanded)
- Propagation: `fp = 0.80`
- Hoop: `F = 0.72` (offshore), `0.50-0.60` (risers by fluid type)

## Unit Conventions
- Pressures: psi (pounds per square inch) or ksi (kilo-psi = 1000 psi)
- Dimensions: inches for OD/WT, meters for water depth
- Weights: lb/ft (pounds per linear foot)
- Stress: psi or ksi (consistent with pressure)

## Dependencies
- streamlit >= 1.28.0
- pandas >= 2.0.0
- numpy >= 1.24.0
- plotly >= 5.18.0
