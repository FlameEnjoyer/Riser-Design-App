"""
API RP 1111 - Propagation Buckling Calculations (Section 4.3.2.3)
Design Against Propagating Buckle
"""

import math


def calculate_propagation_pressure(od, wt, smys):
    """
    Calculate propagation buckling pressure according to API RP 1111.
    
    Formula: P_p = 24 * S * (t/D)^2.4
    
    This is the pressure at which a buckle, once initiated, will propagate
    along the length of the pipe.
    
    Parameters:
    -----------
    od : float
        Outer diameter (inches)
    wt : float
        Wall thickness (inches)
    smys : float
        Specified Minimum Yield Strength (ksi or psi)
        
    Returns:
    --------
    dict : Dictionary containing:
        - propagation_pressure: Propagation pressure (same units as SMYS)
        - t_over_d: Wall thickness to diameter ratio
    """
    # Validate inputs to avoid invalid or complex results
    if od <= 0 or wt <= 0 or smys <= 0:
        return {
            'propagation_pressure': 0.0,
            't_over_d': 0.0,
            'd_over_t': float('inf'),
            'is_valid': False
        }

    # Calculate t/D ratio
    t_over_d = wt / od
    
    # Guard against non-positive t/D which would produce complex numbers
    if t_over_d <= 0:
        return {
            'propagation_pressure': 0.0,
            't_over_d': t_over_d,
            'd_over_t': float('inf') if wt == 0 else od / wt,
            'is_valid': False
        }
    
    # P_p = 24 * S * (t/D)^2.4
    propagation_pressure = 24 * smys * (t_over_d ** 2.4)
    
    return {
        'propagation_pressure': propagation_pressure,
        't_over_d': t_over_d,
        'd_over_t': od / wt,
        'is_valid': True
    }


def check_propagation_criteria(od, wt, smys, p_external):
    """
    Check propagation buckling design criteria according to API RP 1111.
    
    Check: P_o <= 0.80 * P_p
    
    The external pressure should not exceed 80% of the propagation pressure
    to prevent buckle propagation.
    
    Note: Propagation is only a concern when external pressure > 0.
    If p_external <= 0 (net internal pressure condition), automatically passes.
    
    Parameters:
    -----------
    od : float
        Outer diameter (inches)
    wt : float
        Wall thickness (inches)
    smys : float
        Specified Minimum Yield Strength (ksi)
    p_external : float
        External design pressure (ksi) - use net external (P_o - P_i) for proper check
        
    Returns:
    --------
    dict : Dictionary containing:
        - pass_fail: Boolean, True if passes criteria
        - propagation_pressure: Theoretical propagation pressure
        - allowable_pressure: Allowable external pressure (0.80 * P_p)
        - external_pressure: Design external pressure
        - utilization: Ratio of external to allowable (0 to 1+)
        - margin: Safety margin (%)
        - safety_factor: Applied safety factor (0.80)
    """
    # Calculate propagation pressure
    prop_result = calculate_propagation_pressure(od, wt, smys)
    propagation_pressure = prop_result['propagation_pressure']
    
    # Safety factor for propagation buckling
    safety_factor = 0.80
    
    # Calculate allowable external pressure
    allowable_pressure = safety_factor * propagation_pressure if prop_result.get('is_valid', False) else 0.0

    # Default outputs
    utilization = 0.0
    sf = float('inf')
    is_reverse_load = False
    margin = float('inf') if p_external <= 0 else 0.0

    # If propagation pressure is invalid or zero, treat as immediate failure when external > 0
    if allowable_pressure <= 0 and p_external > 0:
        return {
            'pass_fail': False,
            'propagation_pressure': propagation_pressure,
            'allowable_pressure': allowable_pressure,
            'external_pressure': p_external,
            'utilization': float('inf'),
            'margin': float('-inf'),
            'design_safety_factor': safety_factor,
            'safety_factor': 0.0,
            'is_reverse_load': False,
            't_over_d': prop_result['t_over_d'],
            'd_over_t': prop_result.get('d_over_t', float('inf'))
        }
    
    # Check criteria: P_o <= 0.80 * P_p
    # API RP 1111: Check (P_o - P_i) ≤ 0.80 × P_p (net external pressure)
    # Safety Factor = Allowable Propagation / Net External Pressure
    #
    # When internal pressure equals or exceeds external (p_external ≤ 0), propagation
    # is not a design concern. Treat as favorable loading with an infinite SF.
    # This is a net internal pressure condition - automatically passes.
    
    # Handle case where p_external <= 0 (net internal pressure - favorable)
    if p_external <= 0:
        pass_fail = True
        utilization = 0.0
        sf = float('inf')
        is_reverse_load = True
        margin = float('inf') if allowable_pressure > 0 else float('inf')
    else:
        # Normal case: positive external pressure
        pass_fail = p_external <= allowable_pressure
        utilization = p_external / allowable_pressure
        sf = allowable_pressure / p_external
        is_reverse_load = False
        margin = ((allowable_pressure - p_external) / allowable_pressure * 100)
    
    return {
        'pass_fail': pass_fail,
        'propagation_pressure': propagation_pressure,
        'allowable_pressure': allowable_pressure,
        'external_pressure': p_external,
        'utilization': utilization,
        'margin': margin,
        'design_safety_factor': safety_factor,
        'safety_factor': sf,
        'is_reverse_load': is_reverse_load,
        't_over_d': prop_result['t_over_d'],
        'd_over_t': prop_result.get('d_over_t', float('inf'))
    }


def calculate_minimum_thickness_for_propagation(od, smys, p_external):
    """
    Calculate the minimum wall thickness required to prevent propagation buckling.
    
    Derived from: P_o = 0.80 * 24 * S * (t/D)^2.4
    Solving for t: t = D * [P_o / (0.80 * 24 * S)]^(1/2.4)
    
    Parameters:
    -----------
    od : float
        Outer diameter (inches)
    smys : float
        Specified Minimum Yield Strength (ksi)
    p_external : float
        External design pressure (ksi)
        
    Returns:
    --------
    float : Minimum wall thickness (inches)
            Returns 0.0 if p_external <= 0 (no propagation concern)
    """
    safety_factor = 0.80
    
    # If external pressure is zero or negative (net internal pressure),
    # propagation is not a concern - return 0 (any thickness OK)
    if p_external <= 0:
        return 0.0
    
    if smys > 0:
        # t/D = [P_o / (safety_factor * 24 * S)]^(1/2.4)
        ratio = p_external / (safety_factor * 24 * smys)
        # Ensure ratio is positive before taking fractional power
        if ratio > 0:
            t_over_d = ratio ** (1 / 2.4)
            min_thickness = od * t_over_d
        else:
            min_thickness = 0.0
    else:
        min_thickness = 0.0
    
    return min_thickness


if __name__ == "__main__":
    # Example test cases
    print("API RP 1111 - Propagation Buckling Check")
    print("=" * 70)
    
    # Test Case 1: TTR PIP Inner Tube
    print("\nTest Case 1: TTR PIP Inner Tube (4.5\" OD, X-80)")
    od = 4.5
    wt = 0.337  # Example wall thickness
    smys = 80.0  # ksi
    p_o = 4.0    # 4 ksi external (annulus pressure)
    
    result = check_propagation_criteria(od, wt, smys, p_o)
    
    print(f"  OD: {od}\" | WT: {wt}\" | D/t: {result['d_over_t']:.2f}")
    print(f"  SMYS: {smys} ksi")
    print(f"  External Pressure (P_o): {p_o} ksi")
    print(f"  t/D Ratio: {result['t_over_d']:.6f}")
    print(f"  Propagation Pressure (P_p): {result['propagation_pressure']:.2f} ksi")
    print(f"  Safety Factor: {result['safety_factor']}")
    print(f"  Allowable Pressure (0.80*P_p): {result['allowable_pressure']:.2f} ksi")
    print(f"  Utilization: {result['utilization']:.3f} ({result['utilization']*100:.1f}%)")
    print(f"  Safety Margin: {result['margin']:.1f}%")
    print(f"  Status: {'PASS' if result['pass_fail'] else 'FAIL'}")
    
    # Calculate minimum required thickness
    min_t = calculate_minimum_thickness_for_propagation(od, smys, p_o)
    print(f"  Minimum Required Thickness: {min_t:.4f}\"")
    
    # Test Case 2: Rigid Riser
    print("\n\nTest Case 2: Rigid Riser (16\" OD, X-52)")
    od = 16.0
    wt = 0.5     # Example wall thickness
    smys = 52.0  # ksi
    # External pressure at 41m depth with seawater (64 lb/ft³)
    # p = ρ * g * h = 64 * 41 * 3.28084 / 144 = ~58.4 psi = 0.0584 ksi
    p_o = 0.0584
    
    result = check_propagation_criteria(od, wt, smys, p_o)
    
    print(f"  OD: {od}\" | WT: {wt}\" | D/t: {result['d_over_t']:.2f}")
    print(f"  SMYS: {smys} ksi")
    print(f"  External Pressure (P_o): {p_o:.4f} ksi")
    print(f"  t/D Ratio: {result['t_over_d']:.6f}")
    print(f"  Propagation Pressure (P_p): {result['propagation_pressure']:.2f} ksi")
    print(f"  Safety Factor: {result['safety_factor']}")
    print(f"  Allowable Pressure (0.80*P_p): {result['allowable_pressure']:.2f} ksi")
    print(f"  Utilization: {result['utilization']:.3f} ({result['utilization']*100:.1f}%)")
    print(f"  Safety Margin: {result['margin']:.1f}%")
    print(f"  Status: {'PASS' if result['pass_fail'] else 'FAIL'}")
    
    # Calculate minimum required thickness
    min_t = calculate_minimum_thickness_for_propagation(od, smys, p_o)
    print(f"  Minimum Required Thickness: {min_t:.4f}\"")
    
    # Test Case 3: Deep water example
    print("\n\nTest Case 3: Deep Water Example (16\" OD, X-65, 1000m depth)")
    od = 16.0
    wt = 0.75
    smys = 65.0  # ksi
    # At 1000m depth: ~1450 psi = 1.45 ksi
    p_o = 1.45
    
    result = check_propagation_criteria(od, wt, smys, p_o)
    
    print(f"  OD: {od}\" | WT: {wt}\" | D/t: {result['d_over_t']:.2f}")
    print(f"  SMYS: {smys} ksi")
    print(f"  External Pressure (P_o): {p_o} ksi")
    print(f"  Propagation Pressure (P_p): {result['propagation_pressure']:.2f} ksi")
    print(f"  Allowable Pressure (0.80*P_p): {result['allowable_pressure']:.2f} ksi")
    print(f"  Utilization: {result['utilization']:.3f} ({result['utilization']*100:.1f}%)")
    print(f"  Safety Margin: {result['margin']:.1f}%")
    print(f"  Status: {'PASS' if result['pass_fail'] else 'FAIL'}")
    
    # Calculate minimum required thickness
    min_t = calculate_minimum_thickness_for_propagation(od, smys, p_o)
    print(f"  Minimum Required Thickness: {min_t:.4f}\"")
