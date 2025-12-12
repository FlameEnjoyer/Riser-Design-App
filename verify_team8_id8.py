"""
Comprehensive verification for Team 8 (ID 8) calculations
Using exact parameters from Excel table
"""

import math

# Constants
DESIGN_LIFE_YEARS = 20
CORROSION_RATE_PER_YEAR = 0.004  # inch/year
MILL_TOLERANCE = 0.125  # 12.5%
HYDROTEST_FACTOR = 1.25

# Material properties
STEEL_DENSITY_PCF = 490.0
SEAWATER_DENSITY_PCF = 64.0
FRESHWATER_DENSITY_PCF = 62.4

# Team 8 - ID 8 Parameters from Excel table
print("="*80)
print("TEAM 8 - ID 8 VERIFICATION (Oil Riser)")
print("="*80)
print("\nInput Parameters from Excel Table:")
print(f"  Outer Diameter:           8.63 inches")
print(f"  Material:                 API 5L X-52")
print(f"  SMYS:                     52 ksi = 52,000 psi")
print(f"  Shut-in pressure:         195 psi")
print(f"  Design pressure:          230 psi")
print(f"  Fluid Content:            Oil")
print(f"  Content SG (w.r.t water): 0.82")
print(f"  Kedalam Laut:             960 m")
print()

# Convert depth to feet
water_depth_m = 960.0
water_depth_ft = water_depth_m * 3.28084
print(f"  Water Depth:              {water_depth_ft:.2f} ft")
print()

# External pressure calculation
print("="*80)
print("EXTERNAL PRESSURE CALCULATION")
print("="*80)
water_density_pcf = 64.0  # seawater
external_pressure_psi = (water_density_pcf * water_depth_ft) / 144.0
print(f"Po = (ρ_water × depth) / 144")
print(f"Po = ({water_density_pcf} × {water_depth_ft:.2f}) / 144")
print(f"Po = {external_pressure_psi:.2f} psi")
print()

# Internal pressures for different conditions
print("="*80)
print("INTERNAL PRESSURE (Pi) FOR EACH CONDITION")
print("="*80)
print(f"1. Installation:          Pi = 0 psi (empty pipe)")
print(f"2. Hydrotest:             Pi = {HYDROTEST_FACTOR} × Design = {HYDROTEST_FACTOR} × 230 = {230 * HYDROTEST_FACTOR:.2f} psi")
print(f"3. Operation:             Pi = Shut-in = 195 psi")
print()
print("NOTE: For operation, we use SHUT-IN PRESSURE (195 psi), NOT design pressure!")
print("      This is the maximum internal pressure during normal operation.")
print()

# Wall thickness calculations
print("="*80)
print("WALL THICKNESS CALCULATIONS")
print("="*80)
wt_nominal = 0.756  # From Excel weight calculation verification
print(f"Nominal WT:               {wt_nominal:.3f} inches")
print()

# Mill tolerance reduction
mill_factor = 1 - MILL_TOLERANCE
wt_mill = wt_nominal * mill_factor
print(f"Mill Tolerance:           {MILL_TOLERANCE*100:.1f}%")
print(f"Mill Factor:              {mill_factor:.3f}")
print(f"WT after mill tolerance:  {wt_mill:.3f} inches")
print()

# Corrosion allowance
corrosion_total = CORROSION_RATE_PER_YEAR * DESIGN_LIFE_YEARS
print(f"Corrosion rate:           {CORROSION_RATE_PER_YEAR} in/year")
print(f"Design life:              {DESIGN_LIFE_YEARS} years")
print(f"Total corrosion:          {corrosion_total:.3f} inches")
print()

# Effective WT for each condition
print("Effective Wall Thickness by Condition:")
print(f"  Installation:           {wt_mill:.3f} in (mill only, no corrosion)")
print(f"  Hydrotest:              {wt_mill:.3f} in (mill only, no corrosion)")
wt_operation = wt_mill - corrosion_total
print(f"  Operation:              {wt_operation:.3f} in (mill + corrosion)")
print()

# Differential pressures
print("="*80)
print("DIFFERENTIAL PRESSURES (dP = Pi - Po)")
print("="*80)
od = 8.63
pi_installation = 0.0
pi_hydrotest = 230.0 * HYDROTEST_FACTOR
pi_operation = 195.0  # SHUT-IN PRESSURE

dp_installation = pi_installation - external_pressure_psi
dp_hydrotest = pi_hydrotest - external_pressure_psi
dp_operation = pi_operation - external_pressure_psi

print(f"Installation:  dP = {pi_installation:.2f} - {external_pressure_psi:.2f} = {dp_installation:.2f} psi")
print(f"Hydrotest:     dP = {pi_hydrotest:.2f} - {external_pressure_psi:.2f} = {dp_hydrotest:.2f} psi")
print(f"Operation:     dP = {pi_operation:.2f} - {external_pressure_psi:.2f} = {dp_operation:.2f} psi")
print()

if dp_installation < 0:
    print("⚠ Installation: COLLAPSE condition (negative dP, external > internal)")
if dp_hydrotest > 0:
    print("⚠ Hydrotest: BURST condition (positive dP, internal > external)")
if dp_operation < 0:
    print("⚠ Operation: COLLAPSE condition (negative dP, external > internal)")
print()

# Weight calculations with effective WT
print("="*80)
print("WEIGHT CALCULATIONS WITH EFFECTIVE WT")
print("="*80)
print("\nFor Operation Condition (WT = {:.3f} in):".format(wt_operation))

import calcs_weight

# Calculate with operation WT
fluid_sg = 0.82
result_operation = calcs_weight.calculate_pipe_weights(
    od_inches=od,
    wt_inches=wt_operation,
    fluid_sg=fluid_sg,
    use_seawater=True
)

print(f"  OD:                      {result_operation['od_inches']:.3f} inches")
print(f"  ID:                      {result_operation['id_inches']:.3f} inches")
print(f"  WT (effective):          {result_operation['wt_inches']:.3f} inches")
print()
print(f"  Void Dry Weight:         {result_operation['void_dry_weight_plf']:.2f} PLF")
print(f"  Void Submerged Weight:   {result_operation['void_submerged_weight_plf']:.2f} PLF")
print(f"  Flooded Dry Weight:      {result_operation['flooded_dry_weight_plf']:.2f} PLF")
print(f"  Flooded Submerged Weight:{result_operation['flooded_submerged_weight_plf']:.2f} PLF")
print(f"  Product Dry Weight:      {result_operation['product_filled_dry_weight_plf']:.2f} PLF")
print(f"  Product Submerged Weight:{result_operation['product_filled_submerged_weight_plf']:.2f} PLF")
print(f"  Pipe Specific Gravity:   {result_operation['pipe_specific_gravity']:.2f}")
print()

# Compare with nominal WT (from Excel)
print("For Nominal WT (WT = {:.3f} in - matches Excel):".format(wt_nominal))
result_nominal = calcs_weight.calculate_pipe_weights(
    od_inches=od,
    wt_inches=wt_nominal,
    fluid_sg=fluid_sg,
    use_seawater=True
)
print(f"  Void Dry Weight:         {result_nominal['void_dry_weight_plf']:.2f} PLF (Excel: 63.60)")
print(f"  Void Submerged Weight:   {result_nominal['void_submerged_weight_plf']:.2f} PLF (Excel: 37.63)")
print(f"  Flooded Dry Weight:      {result_nominal['flooded_dry_weight_plf']:.2f} PLF (Excel: 81.26)")
print(f"  Flooded Submerged Weight:{result_nominal['flooded_submerged_weight_plf']:.2f} PLF (Excel: 55.29)")
print()

print("="*80)
print("SUMMARY OF KEY POINTS")
print("="*80)
print("1. Internal Pressure (Pi) for Operation = SHUT-IN PRESSURE = 195 psi")
print("   NOT design pressure (230 psi)!")
print()
print("2. Hydrotest: Pi = 1.25 × 230 = 287.5 psi")
print()
print("3. Effective WT varies by condition:")
print(f"   - Installation/Hydrotest: {wt_mill:.3f} in (mill tolerance only)")
print(f"   - Operation: {wt_operation:.3f} in (mill tolerance + corrosion)")
print()
print("4. Weights in Excel use NOMINAL WT (no mill tolerance, no corrosion)")
print("   This is for reference only. Design checks use EFFECTIVE WT.")
print()
print("="*80)
