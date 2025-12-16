"""
Verification script to match Excel weight calculations exactly
Using data from Excel screenshot
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from calculations import calcs_weight

# From Excel screenshot - Input Data
print("="*80)
print("VERIFICATION AGAINST EXCEL DATA")
print("="*80)
print("\nInput Parameters from Excel:")
print("  PIPE O.D:                8.625 inches")
print("  PIPE W.T:                0.756 inches")
print("  PIPE SMYS:               70,000.0 PSI")
print("  PIPE ELASTIC MODULUS:    2.90E+07 PSI")
print("  PIPE SMUTS:              82,000.0 PSI")
print("  PIPE TYPE:               SMLS")
print("  AMBIENT/FLOODED WATER:   64.00 PCF")
print("  PRODUCT DENSITY:         19.20 PCF")
print()

# Calculate fluid SG from product density
# Product density = 19.20 PCF
# Freshwater density = 62.4 PCF
# SG = Product density / Freshwater density
fluid_sg = 19.20 / 62.4
print(f"  Calculated Fluid SG:     {fluid_sg:.4f} (from 19.20 PCF / 62.4 PCF)")
print()

# Run weight calculation
result = calcs_weight.calculate_pipe_weights(
    od_inches=8.625,
    wt_inches=0.756,
    fluid_sg=fluid_sg,
    use_seawater=True  # Using seawater (64 PCF)
)

print("="*80)
print("CALCULATED WEIGHTS")
print("="*80)
print(f"\nGeometric Properties:")
print(f"  OD:                      {result['od_inches']:.3f} inches")
print(f"  ID:                      {result['id_inches']:.3f} inches")
print(f"  WT:                      {result['wt_inches']:.3f} inches")
print(f"  Steel Area:              {result['steel_area_ft2']:.6f} ft²")
print(f"  Void Area:               {result['void_area_ft2']:.6f} ft²")
print()

print(f"Material Properties:")
print(f"  Steel Density:           {result['steel_density_pcf']:.2f} PCF")
print(f"  Water Density:           {result['water_density_pcf']:.2f} PCF (Seawater)")
print(f"  Fluid Density:           {result['fluid_density_pcf']:.2f} PCF")
print(f"  Fluid SG:                {result['fluid_sg']:.4f}")
print()

print("="*80)
print("WEIGHT COMPARISON - CALCULATED vs EXCEL")
print("="*80)

# Expected values from Excel (ALL FOUR SCENARIOS: Installation At Subsea/Bottom, Operation At Subsea/Bottom)
# From Excel: weights are SAME for all 4 scenarios
excel_values = {
    "void_dry_weight_plf": 63.60,
    "void_submerged_weight_plf": 37.63,
    "flooded_dry_weight_plf": 81.26,
    "flooded_submerged_weight_plf": 55.29,
    "product_filled_dry_weight_plf": 68.89,
    "product_filled_submerged_weight_plf": 42.93,
}

print("\n{:<35} {:>12} {:>12} {:>12}".format("Weight Type", "Calculated", "Excel", "Match?"))
print("-"*80)

all_match = True
for key, excel_val in excel_values.items():
    calc_val = result[key]
    match = "✓" if abs(calc_val - excel_val) < 0.01 else "✗ MISMATCH"
    if match == "✗ MISMATCH":
        all_match = False
    
    label = key.replace("_", " ").title().replace("Plf", "(PLF)")
    print(f"{label:<35} {calc_val:>12.2f} {excel_val:>12.2f} {match:>12}")

print("-"*80)

if all_match:
    print("\n✓ ALL WEIGHTS MATCH EXCEL EXACTLY!")
else:
    print("\n✗ SOME WEIGHTS DO NOT MATCH - Need to check formulas")

print()
print("="*80)
print("SPECIFIC GRAVITY COMPARISON")
print("="*80)

# Excel shows Pipe Specific Gravity = 2.45 for void pipe
excel_sg = 2.45
calc_sg = result['pipe_specific_gravity']
print(f"Void Pipe Specific Gravity:")
print(f"  Calculated: {calc_sg:.2f}")
print(f"  Excel:      {excel_sg:.2f}")
print(f"  Match:      {'✓' if abs(calc_sg - excel_sg) < 0.01 else '✗ MISMATCH'}")
print()

print("="*80)
print("NOTES FROM EXCEL:")
print("="*80)
print("1. Weights are IDENTICAL for:")
print("   - During Installation (without Corrosion Allowance)")
print("     * At Subsea Well")
print("     * At Bottom of F/L Riser")
print("   - During Operation (without Corrosion Allowance)")
print("     * At Subsea Well")
print("     * At Bottom of F/L Riser")
print()
print("2. This makes sense because:")
print("   - Weight depends on geometry (OD, WT) and densities")
print("   - Corrosion allowance NOT applied in Excel scenarios shown")
print("   - Location (subsea well vs bottom) doesn't change pipe weight")
print("   - Only pressure conditions change between scenarios, not weight")
print("="*80)
