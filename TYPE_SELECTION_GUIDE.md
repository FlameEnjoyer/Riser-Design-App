# TYPE SELECTION GUIDE
## How to Choose Pipeline, Flowline, or Riser Type

### Overview
The `type` field in `input_data.json` determines the **design factor (f_d)** used in burst pressure calculations per **API RP 1111 Section 4.3.1**. This directly affects the required wall thickness.

---

## Type Definitions & Design Factors

### 1. **Pipeline** (f_d = 0.90)
**Use when:**
- Buried or trenched pipelines on land or seabed
- Protected by soil cover or rock dump
- Minimal dynamic loading
- Long-distance transmission lines
- Stable environment with low bending

**Characteristics:**
- Highest design factor → **Thinnest wall** for same conditions
- More economical for stable, protected routes
- Lower safety margin due to protection and redundancy

**Examples:**
- Export pipelines to shore
- Trunk lines between platforms
- Shore approach pipelines

---

### 2. **Flowline** (f_d = 0.75)
**Use when:**
- Subsea pipelines connecting wells to manifolds/platforms
- Laid on seabed without burial
- Moderate bending during installation
- Subject to some environmental loading
- Free-span sections possible

**Characteristics:**
- Moderate design factor → **Moderate wall thickness**
- Balances economy with safety for subsea exposure
- Accounts for installation stresses

**Examples:**
- Well-to-manifold connections
- Manifold-to-platform jumpers
- Intra-field pipelines

---

### 3. **Riser** (f_d = 0.75)
**Use when:**
- Vertical or near-vertical pipe sections
- Connects seabed equipment to platform/vessel
- **High dynamic loads** from waves, currents, vessel motion
- **Significant bending strains**
- Fatigue-critical applications

**Characteristics:**
- Same design factor as Flowline (0.75)
- But typically higher bending strains drive thickness
- **Riser subtype** (`riser_type` field) for documentation:
  - `TTR` - Top Tensioned Riser
  - `SCR` - Steel Catenary Riser
  - `Rigid` - Rigid vertical riser
  - `Flexible` - (not modeled in this tool)

**Examples:**
- Platform risers (fixed/floating)
- Export risers
- Drilling risers (not covered by this tool)

---

## How Type Affects Calculations

### Burst Pressure Check (API RP 1111 Sec 4.3.1)
```
P_allowable = f_d × f_e × f_t × P_b

Where:
- f_d = Design factor (0.90 for Pipeline, 0.75 for Flowline/Riser)
- f_e = Weld efficiency factor (depends on manufacturing)
- f_t = Temperature derating factor (1.0 for <250°F)
- P_b = Burst pressure capacity
```

### Impact on Wall Thickness
For the same design pressure:
- **Pipeline** (0.90) → Requires ~17% **less** wall thickness than Flowline/Riser
- **Flowline/Riser** (0.75) → More conservative, thicker wall

### Other Checks (NOT affected by type)
- **Collapse** - Uses collapse factor (f_o = 0.6-0.7) based on D/t and ovality
- **Propagation** - Fixed 0.80 factor per API RP 1111
- **Bending** - Depends on bending strain, not type
- **Hoop Stress** - ASME B31.4/B31.8 design factor (0.72) independent of type

---

## Selection Decision Tree

```
START
  │
  ├─ Is pipe buried/protected? 
  │    └─ YES → Pipeline (f_d = 0.90)
  │
  ├─ Is pipe on seabed connecting subsea equipment?
  │    └─ YES → Flowline (f_d = 0.75)
  │
  ├─ Is pipe vertical/near-vertical with dynamic loads?
  │    └─ YES → Riser (f_d = 0.75)
  │             └─ Specify riser_type: TTR, SCR, Rigid, etc.
  │
  └─ UNCERTAIN? → Use Flowline/Riser (more conservative)
```

---

## Example Configurations

### Example 1: Subsea Export Pipeline
```json
{
  "type": "Pipeline",
  "riser_type": "",
  "manufacturing": "DSAW",
  "loads": {
    "bending_strain": 0.0001  // Low bending - buried/stable
  }
}
```

### Example 2: Intra-Field Flowline
```json
{
  "type": "Flowline",
  "riser_type": "",
  "manufacturing": "Seamless",
  "loads": {
    "bending_strain": 0.0003  // Moderate bending - free spans
  }
}
```

### Example 3: Platform Riser
```json
{
  "type": "Riser",
  "riser_type": "TTR",
  "manufacturing": "Seamless",
  "loads": {
    "bending_strain": 0.0008  // High bending - wave/current
  }
}
```

---

## Key Points

1. **Type affects ONLY burst pressure calculations** via design factor f_d
2. **Bending strain** is often the driving factor for risers regardless of type
3. Use `Pipeline` only when truly buried/protected per codes
4. When in doubt, use `Flowline` or `Riser` for conservative design
5. `riser_type` is **documentation only** - does not affect calculations
6. All types use same collapse, propagation, and hoop formulas

---

## References
- API RP 1111 (4th Ed.) - Design, Construction, Operation, and Maintenance of Offshore Hydrocarbon Pipelines
- ASME B31.4 - Pipeline Transportation Systems for Liquids and Slurries
- ASME B31.8 - Gas Transmission and Distribution Piping Systems

---

**Note:** This tool implements API RP 1111 design factors. Always verify with project-specific codes and client requirements.
