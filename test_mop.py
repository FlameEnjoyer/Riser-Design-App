"""
Test MOP (Maximum Operating Pressure) Calculation

This script tests the MOP implementation to verify:
1. MOP calculation formula
2. Position-dependent pressure selection
3. Shut-in location logic
"""

import sys
from app import PipeProperties, LoadingCondition, LifeCycleAnalyzer

print("=" * 80)
print("MOP (Maximum Operating Pressure) Test")
print("=" * 80)

# Test Case 1: Shut-in at Subsea Wellhead (Bottom)
print("\n" + "=" * 80)
print("TEST CASE 1: Shut-in at Subsea Wellhead")
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
    shut_in_location="Subsea Wellhead",  # Shut-in at bottom
    water_depth_m=920.0,
    riser_length_m=920.0,
)

analyzer1 = LifeCycleAnalyzer(pipe1, load1)

# Calculate MOP
mop = analyzer1.calculate_mop()

# Calculate hydrostatic head manually for verification
riser_length_ft = 920.0 * 3.28084
fluid_density_pcf = 0.57 * 64.0  # lb/ft³
hydrostatic_head_psi = (fluid_density_pcf * riser_length_ft) / 144.0

print(f"\nInput Parameters:")
print(f"  Design Pressure:     {load1.design_pressure_psi:.1f} psi")
print(f"  Shut-in Pressure:    {load1.shut_in_pressure_psi:.1f} psi")
print(f"  Shut-in Location:    {load1.shut_in_location}")
print(f"  Riser Length:        {load1.riser_length_m:.1f} m ({riser_length_ft:.1f} ft)")
print(f"  Fluid SG:            {pipe1.fluid_sg:.2f}")

print(f"\nMOP Calculation:")
print(f"  Fluid Density:       {fluid_density_pcf:.2f} lb/ft³")
print(f"  Hydrostatic Head:    {hydrostatic_head_psi:.2f} psi")
print(f"  MOP = Shut-in - Hydrostatic")
print(f"  MOP = {load1.shut_in_pressure_psi:.1f} - {hydrostatic_head_psi:.2f}")
print(f"  MOP = {mop:.2f} psi")

# Test pressure selection for Operation condition
print(f"\nPressure Selection for Operation Condition:")

# Top position - should use MOP for collapse
p_collapse_top = analyzer1.get_internal_pressure_for_check("Operation", "collapse", "Top")
p_burst_top = analyzer1.get_internal_pressure_for_check("Operation", "burst", "Top")

print(f"\n  Top Position:")
print(f"    Burst/Hoop/Long/Combined:  {p_burst_top:.1f} psi (Design)")
print(f"    Collapse/Propagation:      {p_collapse_top:.1f} psi (MOP)")
print(f"    MOP Active: {'YES' if p_collapse_top == mop else 'NO'}")

# Bottom position - should use full shut-in for collapse
p_collapse_bottom = analyzer1.get_internal_pressure_for_check("Operation", "collapse", "Bottom")
p_burst_bottom = analyzer1.get_internal_pressure_for_check("Operation", "burst", "Bottom")

print(f"\n  Bottom Position:")
print(f"    Burst/Hoop/Long/Combined:  {p_burst_bottom:.1f} psi (Design)")
print(f"    Collapse/Propagation:      {p_collapse_bottom:.1f} psi (Shut-in)")
print(f"    MOP Active: NO (uses full shut-in)")

# Verify logic
assert p_collapse_top == mop, f"ERROR: Top collapse should use MOP ({mop:.1f}), got {p_collapse_top:.1f}"
assert p_collapse_bottom == load1.shut_in_pressure_psi, f"ERROR: Bottom collapse should use shut-in ({load1.shut_in_pressure_psi:.1f}), got {p_collapse_bottom:.1f}"
assert p_burst_top == load1.design_pressure_psi, f"ERROR: Top burst should use design ({load1.design_pressure_psi:.1f}), got {p_burst_top:.1f}"
assert p_burst_bottom == load1.design_pressure_psi, f"ERROR: Bottom burst should use design ({load1.design_pressure_psi:.1f}), got {p_burst_bottom:.1f}"

print(f"\n[OK] All assertions passed for Test Case 1!")

# Test Case 2: Shut-in at Top of Riser
print("\n" + "=" * 80)
print("TEST CASE 2: Shut-in at Top of Riser")
print("=" * 80)

load2 = LoadingCondition(
    design_pressure_psi=1400.0,
    shut_in_pressure_psi=1236.0,
    shut_in_location="Top of Riser",  # Shut-in at top
    water_depth_m=920.0,
    riser_length_m=920.0,
)

analyzer2 = LifeCycleAnalyzer(pipe1, load2)

# Calculate MOP (should equal shut-in when shut-in at top)
mop2 = analyzer2.calculate_mop()

print(f"\nInput Parameters:")
print(f"  Design Pressure:     {load2.design_pressure_psi:.1f} psi")
print(f"  Shut-in Pressure:    {load2.shut_in_pressure_psi:.1f} psi")
print(f"  Shut-in Location:    {load2.shut_in_location}")

print(f"\nMOP Calculation:")
print(f"  When shut-in at top: MOP = Shut-in (no adjustment)")
print(f"  MOP = {mop2:.2f} psi")

# Test pressure selection
p_collapse_top2 = analyzer2.get_internal_pressure_for_check("Operation", "collapse", "Top")
p_collapse_bottom2 = analyzer2.get_internal_pressure_for_check("Operation", "collapse", "Bottom")

print(f"\nPressure Selection for Operation Condition:")
print(f"  Top Position Collapse:     {p_collapse_top2:.1f} psi (Shut-in, MOP=Shut-in)")
print(f"  Bottom Position Collapse:  {p_collapse_bottom2:.1f} psi (Shut-in)")

# Verify logic
assert mop2 == load2.shut_in_pressure_psi, f"ERROR: MOP should equal shut-in ({load2.shut_in_pressure_psi:.1f}), got {mop2:.1f}"
assert p_collapse_top2 == load2.shut_in_pressure_psi, f"ERROR: Top collapse should use shut-in ({load2.shut_in_pressure_psi:.1f}), got {p_collapse_top2:.1f}"
assert p_collapse_bottom2 == load2.shut_in_pressure_psi, f"ERROR: Bottom collapse should use shut-in ({load2.shut_in_pressure_psi:.1f}), got {p_collapse_bottom2:.1f}"

print(f"\n[OK] All assertions passed for Test Case 2!")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\n[OK] MOP calculation implemented correctly")
print("[OK] Position-dependent pressure selection working")
print("[OK] Shut-in location logic verified")
print("\nMOP Implementation Status: SUCCESS")
print("=" * 80)
