"""
Test all calculations to verify correctness per API RP 1111 and ASME B31.4/B31.8

This script tests:
1. Hoop stress calculation (ASME B31.4 Sec 402.3)
2. Burst pressure calculation (API RP 1111 Sec 4.3.1)
3. Collapse pressure calculation (API RP 1111 Sec 4.3.2)
4. Propagation buckling calculation (API RP 1111 Sec 4.3.2.3)
"""

import math
from app import PipeProperties, LoadingCondition, LifeCycleAnalyzer

print("=" * 80)
print("CALCULATION VERIFICATION TEST")
print("API RP 1111 + ASME B31.4/B31.8 Compliance Check")
print("=" * 80)

# Create test pipe
pipe = PipeProperties(
    od_in=16.0,
    wt_in=0.750,
    grade="X-52",
    manufacturing="SMLS",
    design_category="Riser",
    fluid_type="Multiphase",
    fluid_sg=0.57,
    smys_psi=52000,
    uts_psi=66000,
    ovality_type="Other Type",
    ovality=0.005,
    E_psi=29000000,
    poisson=0.3,
)

load = LoadingCondition(
    design_pressure_psi=1400.0,
    shut_in_pressure_psi=1236.0,
    shut_in_location="Subsea Wellhead",
    water_depth_m=920.0,
    riser_length_m=920.0,
)

analyzer = LifeCycleAnalyzer(pipe, load)

# Test parameters
wt_eff = 0.750 * 0.875  # After mill tolerance
p_internal = 1400.0  # psi
p_external = 14.7  # psi (atmospheric for top position)

print(f"\nTest Parameters:")
print(f"  OD: {pipe.od_in} in")
print(f"  WT (nominal): {pipe.wt_in} in")
print(f"  WT (effective): {wt_eff:.4f} in")
print(f"  SMYS: {pipe.smys_psi:,} psi")
print(f"  UTS: {pipe.uts_psi:,} psi")
print(f"  Internal Pressure: {p_internal} psi")
print(f"  External Pressure: {p_external} psi")

# =============================================================================
# TEST 1: HOOP STRESS (ASME B31.4 Sec 402.3)
# =============================================================================
print("\n" + "=" * 80)
print("TEST 1: HOOP STRESS (ASME B31.4 Section 402.3)")
print("=" * 80)

# Manual calculation per ASME B31.4 Sec 402.3
# S_H = P_i * D / (2 * t)  -- INTERNAL PRESSURE ONLY, NOT (Pi - Po)
od = pipe.od_in
hoop_stress_manual = p_internal * od / (2 * wt_eff)
design_factor = 0.60  # For riser with multiphase
allowable_manual = design_factor * pipe.smys_psi
sf_manual = allowable_manual / hoop_stress_manual

print(f"\nManual Calculation (ASME B31.4 Sec 402.3):")
print(f"  Formula: S_H = P_i x D / (2 x t)")
print(f"  S_H = {p_internal} x {od} / (2 x {wt_eff:.4f})")
print(f"  S_H = {hoop_stress_manual:,.0f} psi")
print(f"  Design Factor F: {design_factor}")
print(f"  Allowable (F x SMYS): {allowable_manual:,.0f} psi")
print(f"  Safety Factor: {sf_manual:.2f}")

# App calculation
hoop_result = analyzer.compute_hoop(p_internal, p_external, wt_eff)

print(f"\nApp Calculation:")
print(f"  Hoop Stress: {hoop_result['hoop_stress']:,.0f} psi")
print(f"  Allowable: {hoop_result['allowable']:,.0f} psi")
print(f"  Safety Factor: {hoop_result['safety_factor']:.2f}")

# Verify
hoop_diff = abs(hoop_stress_manual - hoop_result['hoop_stress'])
print(f"\nVerification:")
print(f"  Difference: {hoop_diff:.2f} psi")
if hoop_diff < 1.0:
    print("  [OK] Hoop stress calculation CORRECT (uses P_i only, not P_i - P_o)")
else:
    print("  [ERROR] Hoop stress calculation INCORRECT")

# =============================================================================
# TEST 2: BURST PRESSURE (API RP 1111 Sec 4.3.1)
# =============================================================================
print("\n" + "=" * 80)
print("TEST 2: BURST PRESSURE (API RP 1111 Section 4.3.1)")
print("=" * 80)

# Manual calculation
# P_b = 0.90 * (SMYS + UTS) * t / (D - t)
pb_manual = 0.90 * (pipe.smys_psi + pipe.uts_psi) * wt_eff / (od - wt_eff)
fd = 0.75  # Riser design factor
fe = 1.0  # Weld factor
ft = 1.0  # Temperature factor
allowable_burst_manual = fd * fe * ft * pb_manual
delta_p_burst = p_internal - p_external
sf_burst_manual = allowable_burst_manual / delta_p_burst if delta_p_burst > 0 else float('inf')

print(f"\nManual Calculation (API RP 1111 Sec 4.3.1):")
print(f"  Formula: P_b = 0.90 x (SMYS + UTS) x t / (D - t)")
print(f"  P_b = 0.90 x ({pipe.smys_psi:,} + {pipe.uts_psi:,}) x {wt_eff:.4f} / ({od} - {wt_eff:.4f})")
print(f"  P_b = {pb_manual:,.0f} psi")
print(f"  Factors: f_d={fd}, f_e={fe}, f_t={ft}")
print(f"  Allowable (f_d x f_e x f_t x P_b): {allowable_burst_manual:,.0f} psi")
print(f"  Differential (P_i - P_o): {delta_p_burst:.0f} psi")
print(f"  Safety Factor: {sf_burst_manual:.2f}")

# App calculation
burst_result = analyzer.compute_burst(p_internal, p_external, wt_eff)

print(f"\nApp Calculation:")
print(f"  Burst Pressure (P_b): {burst_result['pb']:,.0f} psi")
print(f"  Allowable: {burst_result.get('allowable_burst', 0):,.0f} psi")
print(f"  Safety Factor: {burst_result['safety_factor']:.2f}")

# Verify
pb_diff = abs(pb_manual - burst_result['pb'])
print(f"\nVerification:")
print(f"  P_b Difference: {pb_diff:.2f} psi")
if pb_diff < 1.0:
    print("  [OK] Burst pressure calculation CORRECT")
else:
    print("  [ERROR] Burst pressure calculation INCORRECT")

# =============================================================================
# TEST 3: COLLAPSE PRESSURE (API RP 1111 Sec 4.3.2)
# =============================================================================
print("\n" + "=" * 80)
print("TEST 3: COLLAPSE PRESSURE (API RP 1111 Section 4.3.2)")
print("=" * 80)

# Manual calculation
t_over_d = wt_eff / od
E = pipe.E_psi
nu = pipe.poisson
ovality = pipe.ovality

# Yield collapse: P_y = 2 x SMYS x (t/D)
py_manual = 2 * pipe.smys_psi * t_over_d

# Elastic collapse: P_e = 2 x E x (t/D)^3 / [(1 - nu^2) x (1 + ovality)]
pe_manual = (2 * E * (t_over_d ** 3)) / ((1 - nu ** 2) * (1 + ovality))

# Critical collapse: P_c = P_y x P_e / sqrt(P_y^2 + P_e^2)
pc_manual = (py_manual * pe_manual) / math.sqrt(py_manual ** 2 + pe_manual ** 2)

f_o = 0.70  # SMLS collapse factor
allowable_collapse_manual = f_o * pc_manual

print(f"\nManual Calculation (API RP 1111 Sec 4.3.2):")
print(f"  t/D Ratio: {t_over_d:.6f}")
print(f"  Yield Collapse (P_y): {py_manual:,.0f} psi")
print(f"  Elastic Collapse (P_e): {pe_manual:,.0f} psi")
print(f"  P_y/P_e Ratio: {py_manual/pe_manual:.2f}")
print(f"  Critical Collapse (P_c): {pc_manual:,.0f} psi")
print(f"  Collapse Factor (f_o): {f_o}")
print(f"  Allowable (f_o x P_c): {allowable_collapse_manual:,.0f} psi")

# App calculation
collapse_result = analyzer.compute_collapse(p_internal, p_external, wt_eff)

print(f"\nApp Calculation:")
print(f"  Yield Collapse (P_y): {collapse_result['py']:,.0f} psi")
print(f"  Elastic Collapse (P_e): {collapse_result['pe']:,.0f} psi")
print(f"  Critical Collapse (P_c): {collapse_result['pc']:,.0f} psi")
print(f"  Collapse Mode: {collapse_result.get('collapse_mode', 'N/A')}")
print(f"  Allowable: {collapse_result.get('allowable_collapse', 0):,.0f} psi")

# Verify
py_diff = abs(py_manual - collapse_result['py'])
pe_diff = abs(pe_manual - collapse_result['pe'])
pc_diff = abs(pc_manual - collapse_result['pc'])

print(f"\nVerification:")
print(f"  P_y Difference: {py_diff:.2f} psi")
print(f"  P_e Difference: {pe_diff:.2f} psi")
print(f"  P_c Difference: {pc_diff:.2f} psi")
if py_diff < 1.0 and pe_diff < 1.0 and pc_diff < 1.0:
    print("  [OK] Collapse pressure calculation CORRECT")
else:
    print("  [ERROR] Collapse pressure calculation INCORRECT")

# =============================================================================
# TEST 4: PROPAGATION BUCKLING (API RP 1111 Sec 4.3.2.3)
# =============================================================================
print("\n" + "=" * 80)
print("TEST 4: PROPAGATION BUCKLING (API RP 1111 Section 4.3.2.3)")
print("=" * 80)

# Manual calculation
# P_p = 35 x SMYS x (t/D)^2.5
pp_manual = 35 * pipe.smys_psi * (t_over_d ** 2.5)
fp = 0.80
allowable_prop_manual = fp * pp_manual

print(f"\nManual Calculation (API RP 1111 Sec 4.3.2.3):")
print(f"  Formula: P_p = 35 x SMYS x (t/D)^2.5")
print(f"  P_p = 35 x {pipe.smys_psi:,} x ({t_over_d:.6f})^2.5")
print(f"  P_p = {pp_manual:,.0f} psi")
print(f"  Design Factor (f_p): {fp}")
print(f"  Allowable (f_p x P_p): {allowable_prop_manual:,.0f} psi")

# App calculation
prop_result = analyzer.compute_propagation(p_internal, p_external, wt_eff)

print(f"\nApp Calculation:")
print(f"  Propagation Pressure (P_p): {prop_result['pp']:,.0f} psi")
print(f"  Allowable: {prop_result.get('allowable_prop', 0):,.0f} psi")

# Verify
pp_diff = abs(pp_manual - prop_result['pp'])
print(f"\nVerification:")
print(f"  P_p Difference: {pp_diff:.2f} psi")
if pp_diff < 1.0:
    print("  [OK] Propagation pressure calculation CORRECT")
else:
    print("  [ERROR] Propagation pressure calculation INCORRECT")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

all_pass = (hoop_diff < 1.0 and pb_diff < 1.0 and
            py_diff < 1.0 and pe_diff < 1.0 and pc_diff < 1.0 and
            pp_diff < 1.0)

if all_pass:
    print("\n[OK] All calculations verified CORRECT per API RP 1111 and ASME B31.4")
    print("\nKey Corrections Applied:")
    print("  - Hoop Stress: Uses P_i only (NOT P_i - P_o) per ASME B31.4 Sec 402.3")
    print("  - Burst: Uses Barlow thin-wall formula per API RP 1111 Sec 4.3.1")
    print("  - Collapse: Includes ovality in elastic collapse per API RP 1111 Sec 4.3.2")
    print("  - Propagation: Uses 35 x (t/D)^2.5 formula per API RP 1111 Sec 4.3.2.3")
else:
    print("\n[ERROR] Some calculations need review")

print("=" * 80)
