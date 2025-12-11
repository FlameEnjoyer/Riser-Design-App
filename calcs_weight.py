"""
Pipe Weight Calculations
Per API RP 1111 (3rd Edition, 1999) Appendix A

Formulas for pipe weight in air and submerged conditions,
with and without internal fluid content.
"""

import math
from typing import Dict, Any


# Material properties per API RP 1111
STEEL_DENSITY_PCF = 490.0  # lb/ft³ (carbon steel)
SEAWATER_DENSITY_PCF = 64.0  # lb/ft³
FRESHWATER_DENSITY_PCF = 62.4  # lb/ft³


def calculate_pipe_weights(
    od_inches: float,
    wt_inches: float,
    fluid_sg: float,
    use_seawater: bool = True
) -> Dict[str, Any]:
    """
    Calculate pipe weights per API RP 1111 Appendix A
    
    Parameters:
    -----------
    od_inches : float
        Outer diameter in inches
    wt_inches : float
        Wall thickness in inches
    fluid_sg : float
        Fluid specific gravity (relative to freshwater)
    use_seawater : bool
        True for seawater buoyancy, False for freshwater
        
    Returns:
    --------
    Dict containing:
    - void_dry_weight_plf: Empty pipe weight in air (lb/ft)
    - void_submerged_weight_plf: Empty pipe submerged weight (lb/ft)
    - flooded_dry_weight_plf: Flooded pipe weight in air (lb/ft)
    - flooded_submerged_weight_plf: Flooded pipe submerged weight (lb/ft)
    - product_filled_dry_weight_plf: Product-filled dry weight (lb/ft)
    - product_filled_submerged_weight_plf: Product-filled submerged weight (lb/ft)
    - pipe_specific_gravity: Pipe specific gravity (dimensionless)
    - void_pipe_specific_gravity: Void pipe specific gravity
    - flooded_pipe_specific_gravity: Flooded pipe specific gravity
    - product_filled_pipe_specific_gravity: Product-filled pipe specific gravity
    
    Formulas per API RP 1111 Appendix A:
    W_steel = ρ_steel × A_steel
    W_submerged = W_air - ρ_water × A_displaced
    W_flooded = W_steel + ρ_fluid × A_void
    SG = W / (ρ_water × A_displaced)
    """
    # Convert dimensions to feet for consistent units
    od_ft = od_inches / 12.0
    id_inches = od_inches - 2.0 * wt_inches
    id_ft = id_inches / 12.0
    
    # Select water density
    water_density = SEAWATER_DENSITY_PCF if use_seawater else FRESHWATER_DENSITY_PCF
    
    # Cross-sectional areas (ft²)
    # Steel area (annulus)
    a_steel = (math.pi / 4.0) * (od_ft**2 - id_ft**2)
    
    # Void area (inside pipe)
    a_void = (math.pi / 4.0) * (id_ft**2)
    
    # Outer area (displaced volume for buoyancy)
    a_outer = (math.pi / 4.0) * (od_ft**2)
    
    # =========================================================================
    # 1. VOID (EMPTY) PIPE WEIGHTS
    # =========================================================================
    # Dry weight (in air): W_steel = ρ_steel × A_steel
    void_dry_weight_plf = STEEL_DENSITY_PCF * a_steel
    
    # Submerged weight: W_sub = W_dry - ρ_water × A_outer (buoyancy)
    void_submerged_weight_plf = void_dry_weight_plf - (water_density * a_outer)
    
    # Void pipe specific gravity: SG = W_dry / (ρ_water × A_outer)
    void_pipe_sg = void_dry_weight_plf / (water_density * a_outer)
    
    # =========================================================================
    # 2. FLOODED PIPE WEIGHTS (completely filled with water)
    # =========================================================================
    # Dry weight: W_steel + ρ_water × A_void
    flooded_dry_weight_plf = void_dry_weight_plf + (water_density * a_void)
    
    # Submerged weight: W_flooded_dry - ρ_water × A_outer
    flooded_submerged_weight_plf = flooded_dry_weight_plf - (water_density * a_outer)
    
    # Flooded pipe specific gravity
    flooded_pipe_sg = flooded_dry_weight_plf / (water_density * a_outer)
    
    # =========================================================================
    # 3. PRODUCT-FILLED PIPE WEIGHTS (filled with hydrocarbon fluid)
    # =========================================================================
    # Fluid density: ρ_fluid = SG × ρ_freshwater
    fluid_density_pcf = fluid_sg * FRESHWATER_DENSITY_PCF
    
    # Dry weight: W_steel + ρ_fluid × A_void
    product_filled_dry_weight_plf = void_dry_weight_plf + (fluid_density_pcf * a_void)
    
    # Submerged weight: W_product_dry - ρ_water × A_outer
    product_filled_submerged_weight_plf = product_filled_dry_weight_plf - (water_density * a_outer)
    
    # Product-filled pipe specific gravity
    product_filled_pipe_sg = product_filled_dry_weight_plf / (water_density * a_outer)
    
    # =========================================================================
    # Overall pipe specific gravity (void dry weight basis)
    # =========================================================================
    pipe_specific_gravity = void_pipe_sg
    
    return {
        # Weights in lb/ft
        "void_dry_weight_plf": round(void_dry_weight_plf, 2),
        "void_submerged_weight_plf": round(void_submerged_weight_plf, 2),
        "flooded_dry_weight_plf": round(flooded_dry_weight_plf, 2),
        "flooded_submerged_weight_plf": round(flooded_submerged_weight_plf, 2),
        "product_filled_dry_weight_plf": round(product_filled_dry_weight_plf, 2),
        "product_filled_submerged_weight_plf": round(product_filled_submerged_weight_plf, 2),
        
        # Specific gravities (dimensionless)
        "pipe_specific_gravity": round(pipe_specific_gravity, 2),
        "void_pipe_specific_gravity": round(void_pipe_sg, 2),
        "flooded_pipe_specific_gravity": round(flooded_pipe_sg, 2),
        "product_filled_pipe_specific_gravity": round(product_filled_pipe_sg, 2),
        
        # Geometric properties
        "od_inches": od_inches,
        "id_inches": round(id_inches, 3),
        "wt_inches": wt_inches,
        "steel_area_ft2": round(a_steel, 6),
        "void_area_ft2": round(a_void, 6),
        "outer_area_ft2": round(a_outer, 6),
        
        # Material properties used
        "steel_density_pcf": STEEL_DENSITY_PCF,
        "water_density_pcf": water_density,
        "fluid_density_pcf": round(fluid_density_pcf, 2),
        "fluid_sg": fluid_sg,
    }


def calculate_axial_stress_from_weight(
    weight_plf: float,
    length_ft: float,
    od_inches: float,
    wt_inches: float
) -> float:
    """
    Calculate axial stress from pipe self-weight
    
    Parameters:
    -----------
    weight_plf : float
        Weight per linear foot (lb/ft)
    length_ft : float
        Suspended length (ft)
    od_inches : float
        Outer diameter (inches)
    wt_inches : float
        Wall thickness (inches)
        
    Returns:
    --------
    float : Axial stress in psi
    
    Formula:
    σ_axial = (W × L) / A_steel
    where A_steel = π/4 × (OD² - ID²)
    """
    # Total weight
    total_weight_lb = weight_plf * length_ft
    
    # Steel cross-sectional area
    id_inches = od_inches - 2.0 * wt_inches
    a_steel_in2 = (math.pi / 4.0) * (od_inches**2 - id_inches**2)
    
    # Axial stress
    if a_steel_in2 > 0:
        axial_stress_psi = total_weight_lb / a_steel_in2
    else:
        axial_stress_psi = 0.0
    
    return axial_stress_psi


def calculate_combined_stress_von_mises(
    axial_stress_psi: float,
    hoop_stress_psi: float,
    bending_stress_psi: float = 0.0
) -> Dict[str, float]:
    """
    Calculate von Mises equivalent stress for combined loading
    Per API RP 1111 Section 4.4
    
    Parameters:
    -----------
    axial_stress_psi : float
        Axial stress (tension positive) in psi
    hoop_stress_psi : float
        Hoop stress (circumferential) in psi
    bending_stress_psi : float
        Bending stress in psi
        
    Returns:
    --------
    Dict containing:
    - sigma_longitudinal: Combined longitudinal stress (axial + bending)
    - sigma_hoop: Hoop stress
    - sigma_von_mises: von Mises equivalent stress
    
    von Mises Formula:
    σ_vm = √(σ_L² + σ_H² - σ_L×σ_H)
    where σ_L = σ_axial + σ_bending (longitudinal)
          σ_H = σ_hoop (circumferential)
    """
    # Longitudinal stress (axial + bending)
    sigma_longitudinal = axial_stress_psi + bending_stress_psi
    
    # Hoop stress
    sigma_hoop = hoop_stress_psi
    
    # von Mises equivalent stress
    sigma_vm = math.sqrt(
        sigma_longitudinal**2 + 
        sigma_hoop**2 - 
        sigma_longitudinal * sigma_hoop
    )
    
    return {
        "sigma_longitudinal_psi": round(sigma_longitudinal, 1),
        "sigma_hoop_psi": round(sigma_hoop, 1),
        "sigma_von_mises_psi": round(sigma_vm, 1),
    }


def verify_weight_calculation():
    """
    Verification test against expected values from Excel reference
    
    Test Case 1 (ID 8): OD=8.625", WT=0.756", SG=0.57
    Expected: Void Dry=63.60, Void Sub=37.63, Flooded Dry=81.26, 
              Flooded Sub=55.29, Pipe SG=2.45
    
    Test Case 2 (ID 3): OD=16.0", WT varies, SG=0.57 (Multiphase)
    """
    # Test case from Excel (ID 8)
    print("="*80)
    print("TEST CASE 1: ID 8 (8.625\" OD)")
    print("="*80)
    test_params = {
        "od_inches": 8.625,
        "wt_inches": 0.756,
        "fluid_sg": 0.57,
    }
    
    result = calculate_pipe_weights(**test_params)
    
    print("="*80)
    print("PIPE WEIGHT CALCULATION VERIFICATION")
    print("="*80)
    print(f"Input Parameters:")
    print(f"  OD: {test_params['od_inches']:.3f} inches")
    print(f"  WT: {test_params['wt_inches']:.3f} inches")
    print(f"  ID: {result['id_inches']:.3f} inches")
    print(f"  Fluid SG: {test_params['fluid_sg']}")
    print()
    print(f"Calculated Weights (lb/ft):")
    print(f"  Void Dry Weight:              {result['void_dry_weight_plf']:.2f} PLF")
    print(f"  Void Submerged Weight:        {result['void_submerged_weight_plf']:.2f} PLF")
    print(f"  Flooded Dry Weight:           {result['flooded_dry_weight_plf']:.2f} PLF")
    print(f"  Flooded Submerged Weight:     {result['flooded_submerged_weight_plf']:.2f} PLF")
    print(f"  Product-Filled Dry Weight:    {result['product_filled_dry_weight_plf']:.2f} PLF")
    print(f"  Product-Filled Submerged:     {result['product_filled_submerged_weight_plf']:.2f} PLF")
    print()
    print(f"Specific Gravities:")
    print(f"  Pipe (Void) Specific Gravity: {result['pipe_specific_gravity']:.2f}")
    print(f"  Flooded Pipe SG:              {result['flooded_pipe_specific_gravity']:.2f}")
    print(f"  Product-Filled Pipe SG:       {result['product_filled_pipe_specific_gravity']:.2f}")
    print("="*80)
    print()
    
    # Test case 2: ID 3 from your dataset
    print("="*80)
    print("TEST CASE 2: ID 3 (16.0\" OD, Multiphase)")
    print("="*80)
    test_params2 = {
        "od_inches": 16.0,
        "wt_inches": 0.750,  # Nominal from your data
        "fluid_sg": 0.57,
    }
    
    result2 = calculate_pipe_weights(**test_params2)
    
    print(f"Input Parameters:")
    print(f"  OD: {test_params2['od_inches']:.3f} inches")
    print(f"  WT: {test_params2['wt_inches']:.3f} inches")
    print(f"  ID: {result2['id_inches']:.3f} inches")
    print(f"  Fluid SG: {test_params2['fluid_sg']}")
    print()
    print(f"Calculated Weights (lb/ft):")
    print(f"  Void Dry Weight:              {result2['void_dry_weight_plf']:.2f} PLF")
    print(f"  Void Submerged Weight:        {result2['void_submerged_weight_plf']:.2f} PLF")
    print(f"  Flooded Dry Weight:           {result2['flooded_dry_weight_plf']:.2f} PLF")
    print(f"  Flooded Submerged Weight:     {result2['flooded_submerged_weight_plf']:.2f} PLF")
    print(f"  Product-Filled Dry Weight:    {result2['product_filled_dry_weight_plf']:.2f} PLF")
    print(f"  Product-Filled Submerged:     {result2['product_filled_submerged_weight_plf']:.2f} PLF")
    print()
    print(f"Specific Gravities:")
    print(f"  Pipe (Void) Specific Gravity: {result2['pipe_specific_gravity']:.2f}")
    print(f"  Flooded Pipe SG:              {result2['flooded_pipe_specific_gravity']:.2f}")
    print(f"  Product-Filled Pipe SG:       {result2['product_filled_pipe_specific_gravity']:.2f}")
    print("="*80)
    
    return result, result2


if __name__ == "__main__":
    # Run verification
    verify_weight_calculation()
