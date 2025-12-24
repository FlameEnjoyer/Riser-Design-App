"""
Test Hydrotest Pressure Calculation per API RP 1111 Appendix C

This script tests the hydrotest pressure implementation to verify:
1. Position-dependent hydrotest pressure calculation
2. Pressure loss at top of riser (like MOP)
3. Compliance with API RP 1111 Appendix C Table C.3
"""

import sys
from app import PipeProperties, LoadingCondition, LifeCycleAnalyzer

print("=" * 80)
print("Hydrotest Pressure Test - API RP 1111 Appendix C")
print("=" * 80)

# Test Case 1: Multiphase Riser (same as Team 8 Reference)
print("\n" + "=" * 80)
print("TEST CASE 1: Multiphase Riser")
print("=" * 80)

pipe1 = PipeProperties(
    od_in=16.0,
    wt_in=0.750,
    grade="X-52",
    manufacturing="SMLS",
    design_category="Riser",
    fluid_type="Multiphase",
    fluid_sg=0.57,  # Multiphase fluid
    smys_psi=52000,
    uts_psi=66000,
    ovality_type="Other Type",
    ovality=0.005,
)

load1 = LoadingCondition(
    design_pressure_psi=1400.0,
    shut_in_pressure_psi=1236.0,
    shut_in_location="Subsea Wellhead",
    water_depth_m=920.0,
    riser_length_m=920.0,
)

analyzer1 = LifeCycleAnalyzer(pipe1, load1)

# Calculate hydrotest pressures for top and bottom
ht_top = analyzer1.calculate_hydrotest_pressure("Top")
ht_bottom = analyzer1.calculate_hydrotest_pressure("Bottom")

# Calculate expected values manually
riser_length_ft = 920.0 * 3.28084
fluid_density_pcf = 0.57 * 64.0  # lb/ft³
hydrostatic_head_psi = (fluid_density_pcf * riser_length_ft) / 144.0
base_ht_pressure = 1400.0 * 1.25  # Design × 1.25
expected_ht_top = base_ht_pressure - hydrostatic_head_psi
expected_ht_bottom = base_ht_pressure

print(f"\nInput Parameters:")
print(f"  Design Pressure:     {load1.design_pressure_psi:.1f} psi")
print(f"  Hydrotest Factor:    1.25×")
print(f"  Riser Length:        {load1.riser_length_m:.1f} m ({riser_length_ft:.1f} ft)")
print(f"  Fluid SG:            {pipe1.fluid_sg:.2f}")

print(f"\nHydrotest Pressure Calculation (API RP 1111 Appendix C):")
print(f"  Base Test Pressure (Pd × 1.25):  {base_ht_pressure:.1f} psi")
print(f"  Fluid Density:                   {fluid_density_pcf:.2f} lb/ft³")
print(f"  Hydrostatic Head:                {hydrostatic_head_psi:.2f} psi")

print(f"\n  TOP Position (with pressure loss):")
print(f"    Pt_top = (Pd × 1.25) - Hydrostatic Head")
print(f"    Pt_top = {base_ht_pressure:.1f} - {hydrostatic_head_psi:.2f}")
print(f"    Pt_top = {ht_top:.2f} psi")

print(f"\n  BOTTOM Position (full test pressure):")
print(f"    Pt_bottom = Pd × 1.25")
print(f"    Pt_bottom = {ht_bottom:.2f} psi")

# Verify
ht_top_diff = abs(expected_ht_top - ht_top)
ht_bottom_diff = abs(expected_ht_bottom - ht_bottom)

print(f"\nVerification:")
print(f"  Expected Pt_top:    {expected_ht_top:.2f} psi")
print(f"  Actual Pt_top:      {ht_top:.2f} psi")
print(f"  Difference:         {ht_top_diff:.2f} psi")

print(f"\n  Expected Pt_bottom: {expected_ht_bottom:.2f} psi")
print(f"  Actual Pt_bottom:   {ht_bottom:.2f} psi")
print(f"  Difference:         {ht_bottom_diff:.2f} psi")

# Assertions
assert ht_top_diff < 1.0, f"ERROR: Top hydrotest pressure calculation incorrect"
assert ht_bottom_diff < 1.0, f"ERROR: Bottom hydrotest pressure calculation incorrect"

print(f"\n[OK] All assertions passed for Test Case 1!")

# Test Case 2: Oil Riser
print("\n" + "=" * 80)
print("TEST CASE 2: Oil Riser")
print("=" * 80)

pipe2 = PipeProperties(
    od_in=8.63,
    wt_in=0.500,
    grade="X-52",
    manufacturing="SMLS",
    design_category="Riser",
    fluid_type="Oil",
    fluid_sg=0.82,  # Oil fluid
    smys_psi=52000,
    uts_psi=66000,
    ovality_type="Other Type",
    ovality=0.005,
)

load2 = LoadingCondition(
    design_pressure_psi=230.0,
    shut_in_pressure_psi=195.0,
    shut_in_location="Subsea Wellhead",
    water_depth_m=100.0,  # Shallower water depth for low-pressure riser
    riser_length_m=100.0,
)

analyzer2 = LifeCycleAnalyzer(pipe2, load2)

# Calculate hydrotest pressures
ht_top2 = analyzer2.calculate_hydrotest_pressure("Top")
ht_bottom2 = analyzer2.calculate_hydrotest_pressure("Bottom")

# Calculate expected values
riser_length_ft2 = 100.0 * 3.28084
fluid_density_pcf2 = 0.82 * 64.0
hydrostatic_head_psi2 = (fluid_density_pcf2 * riser_length_ft2) / 144.0
base_ht_pressure2 = 230.0 * 1.25
expected_ht_top2 = base_ht_pressure2 - hydrostatic_head_psi2
expected_ht_bottom2 = base_ht_pressure2

print(f"\nInput Parameters:")
print(f"  Design Pressure:     {load2.design_pressure_psi:.1f} psi")
print(f"  Riser Length:        {load2.riser_length_m:.1f} m ({riser_length_ft2:.1f} ft)")
print(f"  Fluid SG:            {pipe2.fluid_sg:.2f}")

print(f"\nHydrotest Pressure Calculation:")
print(f"  Base Test Pressure:  {base_ht_pressure2:.1f} psi")
print(f"  Hydrostatic Head:    {hydrostatic_head_psi2:.2f} psi")
print(f"  Pt_top:              {ht_top2:.2f} psi")
print(f"  Pt_bottom:           {ht_bottom2:.2f} psi")

# Verify
ht_top_diff2 = abs(expected_ht_top2 - ht_top2)
ht_bottom_diff2 = abs(expected_ht_bottom2 - ht_bottom2)

assert ht_top_diff2 < 1.0, f"ERROR: Test Case 2 top pressure incorrect"
assert ht_bottom_diff2 < 1.0, f"ERROR: Test Case 2 bottom pressure incorrect"

print(f"\n[OK] All assertions passed for Test Case 2!")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\n[OK] Hydrotest pressure calculation implemented correctly per API RP 1111 Appendix C")
print("[OK] Position-dependent pressure logic verified")
print("[OK] Pressure loss at top of riser properly accounted for")
print("\nHydrotest Implementation Status: SUCCESS")
print("=" * 80)
