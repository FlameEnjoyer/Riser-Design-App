"""
API RP 1111 - Combined Bending and External Pressure (Section 4.3.2.2)
Design Against Combined Loading
"""

import math


def calculate_bending_strain_limit(od, wt, smys, elastic_modulus):
    """
    Calculate the allowable bending strain according to API RP 1111.
    
    Formula: ε_b = 2 * t * S / (D * E)
    
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
        
    Returns:
    --------
    float : Allowable bending strain (dimensionless)
    """
    # ε_b = 2 * t * S / (D * E)
    epsilon_b = 2 * wt * smys / (od * elastic_modulus)
    
    return epsilon_b


def calculate_ovality_function(ovality):
    """
    Calculate the ovality function g(δ) for combined loading check.
    
    According to API RP 1111, the ovality function is:
    g(δ) = 1 - 3.5 * δ  (for δ <= 0.03)
    
    Parameters:
    -----------
    ovality : float
        Out-of-roundness δ = (D_max - D_min) / D_nominal
        
    Returns:
    --------
    float : Ovality function value
    """
    # For ovality <= 3%, use linear relationship
    # For larger ovality, the pipe is typically rejected
    if ovality <= 0.03:
        g_delta = 1 - 3.5 * ovality
    else:
        # Conservative approach for high ovality
        g_delta = 1 - 3.5 * ovality
    
    # Ensure g(δ) doesn't go negative
    g_delta = max(g_delta, 0.0)
    
    return g_delta


def check_combined_bending_pressure(od, wt, smys, elastic_modulus, p_internal, 
                                    p_external, bending_strain, critical_collapse,
                                    ovality=0.005):
    """
    Check combined bending and external pressure criteria according to API RP 1111.
    
    Interaction equation: ε/ε_b + (P_o - P_i)/P_c <= g(δ)
    
    Where:
    - ε is the applied bending strain
    - ε_b is the allowable bending strain
    - P_o is the external pressure
    - P_i is the internal pressure
    - P_c is the critical collapse pressure
    - g(δ) is the ovality function
    
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
        Internal pressure (ksi)
    p_external : float
        External pressure (ksi)
    bending_strain : float
        Applied bending strain (dimensionless)
    critical_collapse : float
        Critical collapse pressure P_c (ksi)
    ovality : float
        Out-of-roundness (default 0.005)
        
    Returns:
    --------
    dict : Dictionary containing all combined loading check results
    """
    # Calculate allowable bending strain
    epsilon_b = calculate_bending_strain_limit(od, wt, smys, elastic_modulus)
    
    # Calculate ovality function
    g_delta = calculate_ovality_function(ovality)
    
    # Calculate bending component
    if epsilon_b > 0:
        bending_component = bending_strain / epsilon_b
    else:
        bending_component = float('inf')
    
    # Calculate pressure component
    pressure_diff = p_external - p_internal
    if critical_collapse > 0:
        pressure_component = pressure_diff / critical_collapse
    else:
        pressure_component = float('inf')
    
    # Calculate total interaction ratio
    interaction_ratio = bending_component + pressure_component
    
    # Check criteria: interaction_ratio <= g(δ)
    pass_fail = interaction_ratio <= g_delta
    
    # Calculate utilization and safety factor
    # API RP 1111: Check (ε/ε_b) + (P_o - P_i)/P_c ≤ g(δ)
    # Safety Factor = Ovality Function / Interaction Ratio
    # SF = g(δ) / [(ε/ε_b) + (P_o - P_i)/P_c]
    # SF > 1.0 means PASS
    #
    # Note: For combined bending, "reverse loading" is not the same concept as burst/collapse.
    # The pressure term can be negative (when P_i > P_o), which HELPS the bending check.
    # This is favorable pressure contribution.
    # 
    # Cases:
    # 1. interaction > 0: Normal case, SF = g(δ)/interaction
    # 2. interaction <= 0: Pressure helps more than bending hurts - extremely favorable
    #    In this case, the check always passes (any negative value <= g(δ))
    
    if interaction_ratio > 0:
        # Normal case: positive interaction ratio
        utilization = interaction_ratio / g_delta
        safety_factor = g_delta / interaction_ratio
        is_reverse_load = False
    else:
        # Interaction is zero or negative - extremely favorable condition
        # The internal pressure completely offsets or exceeds the bending effect
        # SF concept doesn't apply here - it's automatically safe
        utilization = interaction_ratio / g_delta  # Will be <= 0
        safety_factor = float('inf')  # Infinite SF for this favorable condition
        is_reverse_load = True  # Mark as reverse/favorable
    
    # Calculate safety margin
    if g_delta > 0:
        margin = ((g_delta - interaction_ratio) / g_delta) * 100
    else:
        margin = 0.0
    
    return {
        'pass_fail': pass_fail,
        'interaction_ratio': interaction_ratio,
        'allowable_ratio': g_delta,
        'bending_component': bending_component,
        'pressure_component': pressure_component,
        'applied_bending_strain': bending_strain,
        'allowable_bending_strain': epsilon_b,
        'bending_utilization': bending_component,
        'pressure_diff': pressure_diff,
        'critical_collapse': critical_collapse,
        'pressure_utilization': pressure_component,
        'ovality': ovality,
        'g_delta': g_delta,
        'utilization': utilization,
        'safety_factor': safety_factor,
        'is_reverse_load': is_reverse_load,
        'margin': margin
    }


def calculate_allowable_bending_with_pressure(epsilon_b, p_internal, p_external, 
                                               critical_collapse, ovality=0.005):
    """
    Calculate the allowable bending strain when external pressure is present.
    
    From interaction equation: ε/ε_b <= g(δ) - (P_o - P_i)/P_c
    Therefore: ε_allowed = ε_b * [g(δ) - (P_o - P_i)/P_c]
    
    Parameters:
    -----------
    epsilon_b : float
        Allowable bending strain without pressure
    p_internal : float
        Internal pressure (ksi)
    p_external : float
        External pressure (ksi)
    critical_collapse : float
        Critical collapse pressure (ksi)
    ovality : float
        Out-of-roundness
        
    Returns:
    --------
    float : Allowable bending strain with pressure effects (dimensionless)
    """
    g_delta = calculate_ovality_function(ovality)
    
    if critical_collapse > 0:
        pressure_component = (p_external - p_internal) / critical_collapse
    else:
        pressure_component = 0.0
    
    remaining_capacity = g_delta - pressure_component
    remaining_capacity = max(remaining_capacity, 0.0)
    
    epsilon_allowed = epsilon_b * remaining_capacity
    
    return epsilon_allowed


if __name__ == "__main__":
    # Example test cases
    print("API RP 1111 - Combined Bending and External Pressure Check")
    print("=" * 70)
    
    # Test Case 1: TTR PIP Inner Tube
    print("\nTest Case 1: TTR PIP Inner Tube (4.5\" OD, X-80)")
    od = 4.5
    wt = 0.337  # Example wall thickness
    smys = 80.0  # ksi
    E = 30000.0  # ksi
    p_i = 5.0    # 5 ksi internal
    p_o = 4.0    # 4 ksi external
    bending_strain = 0.002  # 0.2% strain
    p_c = 10.0   # Example critical collapse (would be calculated from collapse module)
    ovality = 0.005
    
    result = check_combined_bending_pressure(od, wt, smys, E, p_i, p_o, 
                                             bending_strain, p_c, ovality)
    
    print(f"  OD: {od}\" | WT: {wt}\"")
    print(f"  SMYS: {smys} ksi | E: {E} ksi")
    print(f"  P_internal: {p_i} ksi | P_external: {p_o} ksi")
    print(f"  Applied Bending Strain (ε): {result['applied_bending_strain']:.6f} ({result['applied_bending_strain']*100:.2f}%)")
    print(f"  Allowable Bending Strain (ε_b): {result['allowable_bending_strain']:.6f} ({result['allowable_bending_strain']*100:.2f}%)")
    print(f"  Bending Component (ε/ε_b): {result['bending_component']:.3f}")
    print(f"  Pressure Difference (P_o - P_i): {result['pressure_diff']:.2f} ksi")
    print(f"  Critical Collapse (P_c): {result['critical_collapse']:.2f} ksi")
    print(f"  Pressure Component: {result['pressure_component']:.3f}")
    print(f"  Ovality (δ): {result['ovality']:.4f} ({result['ovality']*100:.2f}%)")
    print(f"  Ovality Function g(δ): {result['g_delta']:.3f}")
    print(f"  Interaction Ratio: {result['interaction_ratio']:.3f}")
    print(f"  Allowable Ratio: {result['allowable_ratio']:.3f}")
    print(f"  Utilization: {result['utilization']:.3f} ({result['utilization']*100:.1f}%)")
    print(f"  Safety Margin: {result['margin']:.1f}%")
    print(f"  Status: {'PASS' if result['pass_fail'] else 'FAIL'}")
    
    # Calculate allowable bending with pressure
    eps_allowed = calculate_allowable_bending_with_pressure(
        result['allowable_bending_strain'], p_i, p_o, p_c, ovality)
    print(f"  Allowable Bending with Pressure: {eps_allowed:.6f} ({eps_allowed*100:.2f}%)")
    
    # Test Case 2: Rigid Riser with different loading
    print("\n\nTest Case 2: Rigid Riser (16\" OD, X-52)")
    od = 16.0
    wt = 0.5     # Example wall thickness
    smys = 52.0  # ksi
    E = 30000.0  # ksi
    p_i = 1.4    # 1.4 ksi internal
    p_o = 0.0584 # 0.0584 ksi external (hydrostatic at 41m)
    bending_strain = 0.002  # 0.2% strain
    p_c = 5.0    # Example critical collapse
    ovality = 0.005
    
    result = check_combined_bending_pressure(od, wt, smys, E, p_i, p_o, 
                                             bending_strain, p_c, ovality)
    
    print(f"  OD: {od}\" | WT: {wt}\"")
    print(f"  SMYS: {smys} ksi | E: {E} ksi")
    print(f"  P_internal: {p_i} ksi | P_external: {p_o:.4f} ksi")
    print(f"  Applied Bending Strain (ε): {result['applied_bending_strain']:.6f} ({result['applied_bending_strain']*100:.2f}%)")
    print(f"  Allowable Bending Strain (ε_b): {result['allowable_bending_strain']:.6f} ({result['allowable_bending_strain']*100:.2f}%)")
    print(f"  Bending Component (ε/ε_b): {result['bending_component']:.3f}")
    print(f"  Pressure Difference (P_o - P_i): {result['pressure_diff']:.4f} ksi")
    print(f"  Critical Collapse (P_c): {result['critical_collapse']:.2f} ksi")
    print(f"  Pressure Component: {result['pressure_component']:.3f}")
    print(f"  Ovality (δ): {result['ovality']:.4f}")
    print(f"  Ovality Function g(δ): {result['g_delta']:.3f}")
    print(f"  Interaction Ratio: {result['interaction_ratio']:.3f}")
    print(f"  Allowable Ratio: {result['allowable_ratio']:.3f}")
    print(f"  Utilization: {result['utilization']:.3f} ({result['utilization']*100:.1f}%)")
    print(f"  Safety Margin: {result['margin']:.1f}%")
    print(f"  Status: {'PASS' if result['pass_fail'] else 'FAIL'}")
    
    # Calculate allowable bending with pressure
    eps_allowed = calculate_allowable_bending_with_pressure(
        result['allowable_bending_strain'], p_i, p_o, p_c, ovality)
    print(f"  Allowable Bending with Pressure: {eps_allowed:.6f} ({eps_allowed*100:.2f}%)")
