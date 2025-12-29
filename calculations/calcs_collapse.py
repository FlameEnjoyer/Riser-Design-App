"""
API RP 1111 - External Collapse Calculations (Section 4.3.2)
Design of Offshore Steel Pipelines Against External Collapse
"""

import math


def calculate_yield_collapse(od, wt, smys, poisson_ratio=0.3):
    """
    Calculate yield collapse pressure (P_y) - SIMPLIFIED FORMULA.

    Formula: P_y = 2 * S * (t/D)

    Note: This is the simplified yield collapse formula without Poisson correction,
    which matches industry practice and validation data.

    Parameters:
    -----------
    od : float
        Outer diameter (inches)
    wt : float
        Wall thickness (inches)
    smys : float
        Specified Minimum Yield Strength (ksi or psi)
    poisson_ratio : float
        Poisson's ratio (default 0.3 for steel) - NOT USED in simplified formula

    Returns:
    --------
    float : Yield collapse pressure (same units as SMYS)
    """
    # P_y = 2 * S * (t/D) - Simplified formula
    # This matches validation test cases and industry practice
    p_y = 2 * smys * (wt / od)

    return p_y


def calculate_elastic_collapse(od, wt, elastic_modulus, poisson_ratio=0.3, ovality=0.0):
    """
    Calculate elastic collapse pressure (P_e) - SIMPLIFIED FORMULA.

    Formula: P_e = 2E × (t/D)³ / (1 - ν²)

    Note: This is the simplified elastic collapse formula without ovality factor,
    which matches the standard formulation shown in reference materials.

    Parameters:
    -----------
    od : float
        Outer diameter (inches)
    wt : float
        Wall thickness (inches)
    elastic_modulus : float
        Young's modulus (ksi or psi)
    poisson_ratio : float
        Poisson's ratio (default 0.3 for steel)
    ovality : float
        Out-of-roundness (NOT USED in simplified formula)

    Returns:
    --------
    float : Elastic collapse pressure (same units as E)
    """
    # t/D ratio
    t_over_d = wt / od

    # P_e = 2E × (t/D)³ / (1 - ν²) - Simplified formula
    p_e = 2 * elastic_modulus * (t_over_d**3) / (1 - poisson_ratio**2)

    return p_e


def calculate_critical_collapse(p_y, p_e):
    """
    Calculate critical collapse pressure (P_c) using Murphy-Langner formula.

    Formula: P_c = (P_y × P_e) / sqrt(P_y² + P_e²)

    This formula provides a smooth transition between yield and elastic collapse
    and matches validation test cases.

    Parameters:
    -----------
    p_y : float
        Yield collapse pressure
    p_e : float
        Elastic collapse pressure

    Returns:
    --------
    dict : Dictionary containing:
        - critical_collapse: Critical collapse pressure
        - collapse_mode: Type of collapse ("Yield", "Elastic", or "Plastic")
        - py_pe_ratio: Ratio of P_y to P_e
    """
    # Calculate P_y/P_e ratio for mode classification
    if p_e > 0:
        ratio = p_y / p_e
    else:
        ratio = float('inf')

    # Determine collapse mode based on ratio
    if ratio <= 1.5:
        collapse_mode = "Elastic"
    elif ratio >= 4.0:
        collapse_mode = "Yield"
    else:
        collapse_mode = "Plastic"

    # Murphy-Langner formula: P_c = (P_y × P_e) / sqrt(P_y² + P_e²)
    # This formula matches validation test data
    if p_y > 0 and p_e > 0:
        p_c = (p_y * p_e) / math.sqrt(p_y**2 + p_e**2)
    elif ratio >= 4.0:
        # Pure yield collapse
        p_c = p_y
    else:
        p_c = 0.0

    return {
        'critical_collapse': p_c,
        'collapse_mode': collapse_mode,
        'py_pe_ratio': ratio
    }


def get_collapse_factor(manufacturing):
    """
    Get collapse safety factor (f_o) based on manufacturing method.
    
    Parameters:
    -----------
    manufacturing : str
        Manufacturing method
        
    Returns:
    --------
    float : Collapse factor f_o
    """
    # According to API RP 1111
    # Seamless and ERW: f_o = 0.7
    # Cold Expanded, DSAW: f_o = 0.6
    collapse_factors = {
        'Seamless': 0.7,
        'ERW': 0.7,
        'DSAW': 0.6,
        'SAW': 0.6,
        'Cold Expanded': 0.6,
        'EFW': 0.6
    }
    
    return collapse_factors.get(manufacturing, 0.6)


def check_collapse_criteria(od, wt, smys, elastic_modulus, p_internal, p_external,
                            manufacturing, poisson_ratio=0.3, ovality=0.005):
    """
    Check external collapse design criteria according to API RP 1111.
    
    Check: (P_o - P_i) <= f_o * P_c
    
    Parameters:
    -----------
    od : float
        Outer diameter (inches)
    wt : float
        Wall thickness (inches)
    smys : float
        Specified Minimum Yield Strength (ksi)
    elastic_modulus : float
        Young's modulus (ksi)
    p_internal : float
        Internal design pressure (ksi)
    p_external : float
        External design pressure (ksi)
    manufacturing : str
        Manufacturing method
    poisson_ratio : float
        Poisson's ratio (default 0.3)
    ovality : float
        Out-of-roundness (default 0.005)
        
    Returns:
    --------
    dict : Dictionary containing all collapse check results
    """
    # Calculate yield collapse pressure
    p_y = calculate_yield_collapse(od, wt, smys, poisson_ratio)
    
    # Calculate elastic collapse pressure
    p_e = calculate_elastic_collapse(od, wt, elastic_modulus, poisson_ratio, ovality)
    
    # Calculate critical collapse pressure
    collapse_result = calculate_critical_collapse(p_y, p_e)
    p_c = collapse_result['critical_collapse']
    
    # Get collapse factor
    f_o = get_collapse_factor(manufacturing)
    
    # Calculate allowable collapse pressure
    allowable_collapse = f_o * p_c
    
    # Calculate net external pressure
    design_pressure_diff = p_external - p_internal
    
    # Check criteria
    pass_fail = design_pressure_diff <= allowable_collapse
    
    # Calculate utilization ratio and safety factor
    # API RP 1111: Check (P_o - P_i) ≤ f_o × P_c
    # Safety Factor = Allowable Collapse Pressure / Net External Pressure
    #
    # When internal pressure equals or exceeds external (design_pressure_diff ≤ 0),
    # the collapse check is automatically satisfied. Report an infinite safety factor
    # and flag as favorable/reverse loading for reporting clarity.
    if design_pressure_diff > 0:
        utilization = design_pressure_diff / allowable_collapse
        safety_factor = allowable_collapse / design_pressure_diff if design_pressure_diff != 0 else float('inf')
        is_reverse_load = False
    else:
        utilization = 0.0
        safety_factor = float('inf')
        is_reverse_load = True
    
    # Calculate safety margin
    if allowable_collapse > 0:
        margin = ((allowable_collapse - design_pressure_diff) / allowable_collapse) * 100
    else:
        margin = 0.0
    
    return {
        'pass_fail': pass_fail,
        'yield_collapse': p_y,
        'elastic_collapse': p_e,
        'critical_collapse': p_c,
        'collapse_mode': collapse_result['collapse_mode'],
        'py_pe_ratio': collapse_result['py_pe_ratio'],
        'allowable_collapse': allowable_collapse,
        'design_pressure_diff': design_pressure_diff,
        'utilization': utilization,
        'safety_factor': safety_factor,
        'is_reverse_load': is_reverse_load,
        'f_o': f_o,
        'margin': margin,
        't_over_d': wt / od,
        'd_over_t': od / wt,
        'ovality': ovality
    }


if __name__ == "__main__":
    # Example test case
    print("API RP 1111 - External Collapse Check")
    print("=" * 70)
    
    # Test Case 1: TTR PIP Inner Tube
    print("\nTest Case 1: TTR PIP Inner Tube (4.5\" OD, X-80)")
    od = 4.5
    wt = 0.337  # Example wall thickness
    smys = 80.0  # ksi
    E = 30000.0  # ksi
    p_i = 5.0    # 5 ksi internal
    p_o = 4.0    # 4 ksi external (annulus)
    
    result = check_collapse_criteria(od, wt, smys, E, p_i, p_o, 
                                     "Seamless", poisson_ratio=0.3, ovality=0.005)
    
    print(f"  OD: {od}\" | WT: {wt}\" | D/t: {result['d_over_t']:.2f}")
    print(f"  SMYS: {smys} ksi | E: {E} ksi")
    print(f"  P_internal: {p_i} ksi | P_external: {p_o} ksi")
    print(f"  Net External Pressure (P_o - P_i): {result['design_pressure_diff']:.2f} ksi")
    print(f"  Yield Collapse (P_y): {result['yield_collapse']:.2f} ksi")
    print(f"  Elastic Collapse (P_e): {result['elastic_collapse']:.2f} ksi")
    print(f"  Critical Collapse (P_c): {result['critical_collapse']:.2f} ksi")
    print(f"  Collapse Mode: {result['collapse_mode']} (P_y/P_e = {result['py_pe_ratio']:.2f})")
    print(f"  Factor f_o: {result['f_o']}")
    print(f"  Allowable Collapse: {result['allowable_collapse']:.2f} ksi")
    print(f"  Utilization: {result['utilization']:.3f} ({result['utilization']*100:.1f}%)")
    print(f"  Safety Margin: {result['margin']:.1f}%")
    print(f"  Status: {'PASS' if result['pass_fail'] else 'FAIL'}")
    
    # Test Case 2: Rigid Riser
    print("\n\nTest Case 2: Rigid Riser (16\" OD, X-52)")
    od = 16.0
    wt = 0.5     # Example wall thickness
    smys = 52.0  # ksi
    E = 30000.0  # ksi
    p_i = 1.4    # 1.4 ksi internal
    # External pressure at 41m depth with seawater (64 lb/ft³)
    # p = ρ * g * h = 64 * 41 * 3.28084 / 144 = ~58.4 psi = 0.0584 ksi
    p_o = 0.0584
    
    result = check_collapse_criteria(od, wt, smys, E, p_i, p_o, 
                                     "DSAW", poisson_ratio=0.3, ovality=0.005)
    
    print(f"  OD: {od}\" | WT: {wt}\" | D/t: {result['d_over_t']:.2f}")
    print(f"  SMYS: {smys} ksi | E: {E} ksi")
    print(f"  P_internal: {p_i} ksi | P_external: {p_o:.4f} ksi")
    print(f"  Net External Pressure (P_o - P_i): {result['design_pressure_diff']:.4f} ksi")
    print(f"  Yield Collapse (P_y): {result['yield_collapse']:.2f} ksi")
    print(f"  Elastic Collapse (P_e): {result['elastic_collapse']:.2f} ksi")
    print(f"  Critical Collapse (P_c): {result['critical_collapse']:.2f} ksi")
    print(f"  Collapse Mode: {result['collapse_mode']} (P_y/P_e = {result['py_pe_ratio']:.2f})")
    print(f"  Factor f_o: {result['f_o']}")
    print(f"  Allowable Collapse: {result['allowable_collapse']:.2f} ksi")
    print(f"  Utilization: {result['utilization']:.3f} ({result['utilization']*100:.1f}%)")
    print(f"  Safety Margin: {result['margin']:.1f}%")
    print(f"  Status: {'PASS' if result['pass_fail'] else 'FAIL'}")
