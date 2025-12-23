# MOP (Maximum Operating Pressure) Implementation

## Overview

This document describes the MOP (Maximum Operating Pressure) implementation added to the Riser Design Analysis Tool per API RP 1111 requirements.

## What is MOP?

**MOP (Maximum Operating Pressure)** is the maximum pressure at the top of the riser when the shut-in valve is closed at the subsea wellhead (bottom position).

### Formula

```
MOP = Shut-in Pressure - Hydrostatic Head of Riser Contents
```

Where:
- **Shut-in Pressure**: Pressure at the shut-in valve location (psi)
- **Hydrostatic Head**: Pressure exerted by fluid column inside riser
  - `Hydrostatic Head (psi) = (Fluid SG × 64 lb/ft³) × Riser Length (ft) / 144`

## Implementation Details

### 1. New User Input: Shut-in Location

A new dropdown input has been added to the UI under **Pressures & Loading** tab:

**Shut-in Location:**
- `Subsea Wellhead` - Shut-in valve at bottom of riser (default)
- `Top of Riser` - Shut-in valve at top of riser

### 2. Pressure Selection Logic

The tool now uses **three independent pressures** for different checks:

#### Design Pressure
- **Used for**: Burst, Hoop, Longitudinal, Combined Loading
- **All positions**: Always uses input design pressure
- **No MOP adjustment**

#### Shut-in Pressure / MOP
- **Used for**: Collapse, Propagation
- **Position-dependent**:

| Shut-in Location | Top Position | Bottom Position |
|------------------|--------------|-----------------|
| **Subsea Wellhead** | Uses **MOP** (Shut-in - Hydrostatic) | Uses **Full Shut-in** |
| **Top of Riser** | Uses **Shut-in** (MOP = Shut-in) | Uses **Shut-in** |

### 3. Calculation Method

New method added to `LifeCycleAnalyzer` class:

```python
def calculate_mop(self) -> float:
    """
    Calculate MOP per API RP 1111

    Returns MOP in psi:
    - If shut-in at top: MOP = shut-in (no adjustment)
    - If shut-in at bottom: MOP = shut-in - hydrostatic head
    """
```

### 4. Updated Analysis Methods

The `get_internal_pressure_for_check()` method now includes:
- Position parameter: `"Top"` or `"Bottom"`
- Shut-in location awareness
- MOP calculation integration

## Example Calculation

### Test Case: Multiphase Riser (ID 3)

**Input Parameters:**
- Design Pressure: 1400 psi
- Shut-in Pressure: 1236 psi
- Shut-in Location: Subsea Wellhead
- Riser Length: 920 m (3018.4 ft)
- Fluid SG: 0.57 (multiphase)

**MOP Calculation:**
```
Fluid Density = 0.57 × 64 lb/ft³ = 36.48 lb/ft³
Hydrostatic Head = (36.48 × 3018.4) / 144 = 764.65 psi
MOP = 1236.0 - 764.65 = 471.35 psi
```

**Pressure Selection for Operation Condition:**

| Position | Check Type | Pressure Used | Value |
|----------|-----------|---------------|-------|
| **Top** | Burst, Hoop, Long, Combined | Design | 1400 psi |
| **Top** | Collapse, Propagation | **MOP** | **471 psi** |
| **Bottom** | Burst, Hoop, Long, Combined | Design | 1400 psi |
| **Bottom** | Collapse, Propagation | Shut-in | 1236 psi |

## UI Changes

### 1. Input Section

**Pressures & Loading Tab:**
- New dropdown: "Shut-in Location"
- Help text explaining MOP calculation

### 2. Results Display

**Operation Condition Tab:**
- Information box showing MOP value when applicable
- Explanation of pressure strategy
- MOP calculation formula

**Position Results:**
- 4-column pressure display for Operation:
  1. External Pressure (Po)
  2. Design Pressure
  3. Shut-in/MOP
  4. **MOP Active indicator** (new)

- MOP Active indicator shows:
  - ✓ Yes - when MOP is being used (top position, shut-in at bottom)
  - ✗ No - when using shut-in or not applicable

### 3. Summary Tab

Enhanced to show:
- Shut-in location for each analysis
- MOP values in condition summaries
- Clear indication when MOP is active

## Testing

Run the test script to verify MOP calculations:

```bash
python test_mop.py
```

**Expected Results:**
- Test Case 1: Shut-in at Subsea Wellhead
  - MOP calculated correctly
  - Top position uses MOP for collapse/propagation
  - Bottom position uses full shut-in

- Test Case 2: Shut-in at Top of Riser
  - MOP equals shut-in (no adjustment)
  - Both positions use shut-in for collapse

## Code Files Modified

1. **app.py**
   - Line 182-221: Added `calculate_mop()` method
   - Line 223-290: Updated `get_internal_pressure_for_check()` with position and MOP logic
   - Line 741-770: Updated pressure retrieval in `analyze_condition_at_position()`
   - Line 788-817: Added MOP information to result dictionary
   - Line 1088-1100: Added shut-in location dropdown input
   - Line 1284-1328: Updated pressure display in results
   - Line 1636-1670: Added MOP information to Operation tab

2. **test_mop.py** (new file)
   - Comprehensive MOP testing
   - Verification of pressure selection logic
   - Test cases for both shut-in locations

## API RP 1111 Compliance

This implementation follows API RP 1111 guidance for operating pressure calculations:

- MOP accounts for hydrostatic head of riser contents
- Position-dependent pressure selection ensures conservative design
- Design pressure used for strength-based checks (burst, hoop)
- Actual operating pressure (MOP/shut-in) used for stability checks (collapse, propagation)

## Benefits

1. **More Accurate Analysis**: Position-dependent pressures reflect actual operating conditions
2. **Conservative Design**: Different pressures for different failure modes
3. **API Compliance**: Follows industry standard practices
4. **User Flexibility**: Supports different shut-in valve configurations
5. **Clear Documentation**: UI clearly shows when and why MOP is used

## References

- API RP 1111 (3rd Edition, 1999) - Design of Offshore Pipelines and Risers
- ASME B31.4 - Pipeline Transportation Systems for Liquid Hydrocarbons
- ASME B31.8 - Gas Transmission and Distribution Piping Systems
