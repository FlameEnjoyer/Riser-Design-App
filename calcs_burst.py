"""
API RP 1111 - Burst Pressure Calculations (Section 4.3.1)
Design of Offshore Steel Pipelines Against Bursting
"""

import math


def calculate_burst_pressure(od, wt, smys, uts):
    """
    Calculate burst pressure according to API RP 1111 Section 4.3.1.
    
    Formula: P_b = 0.45 * (S + U) * ln(D / D_i)
    
    Parameters:
    -----------
    od : float
        Outer diameter (inches)
    wt : float
        Wall thickness (inches)
    smys : float
        Specified Minimum Yield Strength (ksi or psi)
    uts : float
        Ultimate Tensile Strength (ksi or psi)
        
    Returns:
    --------
    dict : Dictionary containing:
        - burst_pressure: Theoretical burst pressure (same units as SMYS/UTS)
        - inner_diameter: Inner diameter (inches)
        - d_to_di_ratio: D/D_i ratio
    """
    # Calculate inner diameter
    inner_diameter = od - 2 * wt
    
    # D/D_i ratio
    d_to_di = od / inner_diameter
    
    # Burst pressure formula
    # P_b = 0.45 * (S + U) * ln(D/D_i)
    burst_pressure = 0.45 * (smys + uts) * math.log(d_to_di)
    
    return {
        'burst_pressure': burst_pressure,
        'inner_diameter': inner_diameter,
        'd_to_di_ratio': d_to_di
    }


def get_design_factor(scenario_type):
    """
    Get design factor (f_d) based on scenario type.
    
    Parameters:
    -----------
    scenario_type : str
        Type of scenario: "Riser", "Flowline", or "Pipeline"
        
    Returns:
    --------
    float : Design factor f_d
    """
    design_factors = {
        'Riser': 0.75,
        'Flowline': 0.75,
        'Pipeline': 0.90
    }
    
    return design_factors.get(scenario_type, 0.75)


def get_weld_factor(manufacturing):
    """
    Get weld factor (f_e) based on manufacturing method.
    
    Parameters:
    -----------
    manufacturing : str
        Manufacturing method: "Seamless", "ERW", "DSAW", etc.
        
    Returns:
    --------
    float : Weld factor f_e
    """
    # According to API RP 1111
    # Seamless and ERW typically use 1.0
    # DSAW and other welded pipes may use reduced factors
    weld_factors = {
        'Seamless': 1.0,
        'ERW': 1.0,
        'DSAW': 0.85,  # Double Submerged Arc Welded
        'SAW': 0.85,   # Submerged Arc Welded
        'EFW': 0.85,   # Electric Fusion Welded
    }
    
    return weld_factors.get(manufacturing, 1.0)


def get_temperature_factor():
    """
    Get temperature derating factor (f_t).
    For ambient/normal offshore temperatures, this is typically 1.0.
    
    Returns:
    --------
    float : Temperature factor f_t
    """
    # For standard offshore applications at ambient temperature
    return 1.0


def check_burst_criteria(od, wt, smys, uts, p_internal, p_external, 
                         scenario_type, manufacturing):
    """
    Check burst pressure design criteria according to API RP 1111.
    
    Check: (P_i - P_o) <= f_d * f_e * f_t * P_b
    
    Parameters:
    -----------
    od : float
        Outer diameter (inches)
    wt : float
        Wall thickness (inches)
    smys : float
        Specified Minimum Yield Strength (ksi)
    uts : float
        Ultimate Tensile Strength (ksi)
    p_internal : float
        Internal design pressure (psi or ksi)
    p_external : float
        External design pressure (psi or ksi)
    scenario_type : str
        Type: "Riser", "Flowline", or "Pipeline"
    manufacturing : str
        Manufacturing method
        
    Returns:
    --------
    dict : Dictionary containing:
        - pass_fail: Boolean, True if passes criteria
        - burst_pressure: Theoretical burst pressure
        - allowable_burst: Allowable burst pressure (f_d * f_e * f_t * P_b)
        - design_pressure_diff: Net internal pressure (P_i - P_o)
        - utilization: Ratio of design to allowable (0 to 1+)
        - f_d: Design factor
        - f_e: Weld factor
        - f_t: Temperature factor
        - margin: Safety margin (%)
    """
    # Calculate burst pressure
    burst_result = calculate_burst_pressure(od, wt, smys, uts)
    burst_pressure = burst_result['burst_pressure']
    
    # Get factors
    f_d = get_design_factor(scenario_type)
    f_e = get_weld_factor(manufacturing)
    f_t = get_temperature_factor()
    
    # Calculate allowable burst pressure
    allowable_burst = f_d * f_e * f_t * burst_pressure
    
    # Calculate net internal pressure
    design_pressure_diff = p_internal - p_external
    
    # Check criteria
    pass_fail = design_pressure_diff <= allowable_burst
    
    # Calculate utilization ratio and safety factor
    # API RP 1111: Check (P_i - P_o) ≤ f_d × f_e × f_t × P_b
    # Safety Factor = Allowable Burst Pressure / Design Differential
    # SF = (f_d × f_e × f_t × P_b) / (P_i - P_o)
    #
    # When external pressure exceeds internal (design_pressure_diff ≤ 0), the burst
    # criterion is inherently satisfied. Treat this as a favorable (reverse) direction
    # and report an infinite safety factor for clarity.
    if design_pressure_diff > 0:
        utilization = design_pressure_diff / allowable_burst
        safety_factor = allowable_burst / design_pressure_diff if design_pressure_diff != 0 else float('inf')
        is_reverse_load = False
    else:
        utilization = 0.0
        safety_factor = float('inf')
        is_reverse_load = True
    
    # Calculate safety margin
    if allowable_burst > 0:
        margin = ((allowable_burst - design_pressure_diff) / allowable_burst) * 100
    else:
        margin = 0.0
    
    return {
        'pass_fail': pass_fail,
        'burst_pressure': burst_pressure,
        'allowable_burst': allowable_burst,
        'design_pressure_diff': design_pressure_diff,
        'utilization': utilization,
        'safety_factor': safety_factor,
        'is_reverse_load': is_reverse_load,
        'f_d': f_d,
        'f_e': f_e,
        'f_t': f_t,
        'margin': margin,
        'inner_diameter': burst_result['inner_diameter'],
        'd_to_di_ratio': burst_result['d_to_di_ratio']
    }


if __name__ == "__main__":
    # Example test case
    print("API RP 1111 - Burst Pressure Check")
    print("=" * 70)
    
    # Test Case 1: TTR PIP Inner Tube
    print("\nTest Case 1: TTR PIP Inner Tube (4.5\" OD, X-80)")
    od = 4.5
    wt = 0.337  # Example wall thickness
    smys = 80.0  # ksi
    uts = 90.0   # ksi
    p_i = 5.0    # 5000 psi = 5 ksi (converting for consistency)
    p_o = 4.0    # 4000 psi = 4 ksi
    
    result = check_burst_criteria(od, wt, smys, uts, p_i, p_o, 
                                   "Riser", "Seamless")
    
    print(f"  OD: {od}\" | WT: {wt}\" | ID: {result['inner_diameter']:.3f}\"")
    print(f"  SMYS: {smys} ksi | UTS: {uts} ksi")
    print(f"  P_internal: {p_i} ksi | P_external: {p_o} ksi")
    print(f"  Design Pressure Diff (P_i - P_o): {result['design_pressure_diff']:.2f} ksi")
    print(f"  Burst Pressure (P_b): {result['burst_pressure']:.2f} ksi")
    print(f"  Factors: f_d={result['f_d']}, f_e={result['f_e']}, f_t={result['f_t']}")
    print(f"  Allowable Burst: {result['allowable_burst']:.2f} ksi")
    print(f"  Utilization: {result['utilization']:.3f} ({result['utilization']*100:.1f}%)")
    print(f"  Safety Margin: {result['margin']:.1f}%")
    print(f"  Status: {'PASS' if result['pass_fail'] else 'FAIL'}")
    
    # Test Case 2: Rigid Riser
    print("\n\nTest Case 2: Rigid Riser (16\" OD, X-52)")
    od = 16.0
    wt = 0.5     # Example wall thickness
    smys = 52.0  # ksi
    uts = 66.0   # ksi
    p_i = 1.4    # 1400 psi = 1.4 ksi
    p_o = 0.0584 # ~18 psi hydrostatic at 41m depth = 0.0584 ksi
    
    result = check_burst_criteria(od, wt, smys, uts, p_i, p_o, 
                                   "Riser", "DSAW")
    
    print(f"  OD: {od}\" | WT: {wt}\" | ID: {result['inner_diameter']:.3f}\"")
    print(f"  SMYS: {smys} ksi | UTS: {uts} ksi")
    print(f"  P_internal: {p_i} ksi | P_external: {p_o:.4f} ksi")
    print(f"  Design Pressure Diff (P_i - P_o): {result['design_pressure_diff']:.2f} ksi")
    print(f"  Burst Pressure (P_b): {result['burst_pressure']:.2f} ksi")
    print(f"  Factors: f_d={result['f_d']}, f_e={result['f_e']}, f_t={result['f_t']}")
    print(f"  Allowable Burst: {result['allowable_burst']:.2f} ksi")
    print(f"  Utilization: {result['utilization']:.3f} ({result['utilization']*100:.1f}%)")
    print(f"  Safety Margin: {result['margin']:.1f}%")
    print(f"  Status: {'PASS' if result['pass_fail'] else 'FAIL'}")
