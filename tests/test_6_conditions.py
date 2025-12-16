"""
Test script for 6-condition position-based analysis
Tests the core calculation logic before UI updates
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any

# Add parent directory to path to import from app.py
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from app.py
from app import PipeProperties, LoadingCondition, LifeCycleAnalyzer

def test_multiphase_riser():
    """Test with Team 8 Multiphase Riser (ID 3) configuration"""

    print("="*80)
    print("TESTING: Team 8 Multiphase Riser (ID 3)")
    print("="*80)

    # Team 8 Multiphase Riser configuration
    pipe = PipeProperties(
        od_in=16.0,
        wt_in=0.750,
        grade="X-52",
        manufacturing="SMLS",
        design_category="Riser",
        fluid_type="Multiphase",
        fluid_sg=0.57,
        smys_psi=52000.0,
        uts_psi=66000.0,
        ovality_type="Other Type",
        ovality=0.005,
        E_psi=2.9e7,
        poisson=0.30
    )

    load = LoadingCondition(
        design_pressure_psi=1400.0,
        shut_in_pressure_psi=1236.0,
        shut_in_location="Subsea Wellhead",
        water_depth_m=920.0,
        riser_length_m=920.0
    )

    # Create analyzer and run
    analyzer = LifeCycleAnalyzer(pipe, load)
    result = analyzer.run_all_conditions()

    # Print summary
    print(f"\nPipe: OD={pipe.od_in}\" WT={pipe.wt_in}\" Grade={pipe.grade}")
    print(f"Loading: Design={load.design_pressure_psi} psi, Shut-in={load.shut_in_pressure_psi} psi")
    print(f"Water Depth: {load.water_depth_m} m")
    print(f"\nOverall Status: {'PASS' if result['all_conditions_pass'] else 'FAIL'}")
    print("\n" + "="*80)
    print("CONDITION RESULTS (6 Total)")
    print("="*80)

    # Print results for each condition
    for cond_key, cond in result["conditions"].items():
        print(f"\n{cond_key.upper().replace('_', ' - ')}")
        print("-" * 80)
        print(f"  Position: {cond['position']}")
        print(f"  Status: {'PASS' if cond['all_pass'] else 'FAIL'}")
        print(f"  Wall Thickness: Nominal={cond['wt_nominal']:.4f}\" Effective={cond['wt_effective']:.4f}\"")
        print(f"  External Pressure: {cond['p_external_psi']:.1f} psi")
        print(f"  Internal Pressure (Burst): {cond['p_internal_burst']:.1f} psi")
        print(f"  Internal Pressure (Collapse): {cond['p_internal_collapse']:.1f} psi")

        # Print check results
        print(f"\n  Checks (4 pressure-only):")
        for check in cond['checks']:
            sf = check['safety_factor']
            sf_str = f"{sf:.2f}" if sf != float('inf') else "INF"
            status = "PASS" if check['pass_fail'] else "FAIL"
            print(f"    {check['name']:25s}: SF={sf_str:>8s} [{status}]")

        # Longitudinal tension
        long = cond['longitudinal']
        sf = long['safety_factor']
        sf_str = f"{sf:.2f}" if sf != float('inf') else "INF"
        print(f"    {'Longitudinal Tension':25s}: SF={sf_str:>8s} [{long['status']}]")
        print(f"      T_a (applied): {long['t_a_applied_kips']:.2f} kips")
        print(f"      T_eff (effective): {long['t_eff_effective_kips']:.2f} kips")
        print(f"      Riser length used: {long['riser_length_ft']:.1f} ft")

        # Combined loading
        comb = cond['combined']
        sf = comb['safety_factor']
        sf_str = f"{sf:.2f}" if sf != float('inf') else "INF"
        print(f"    {'Combined Loading':25s}: SF={sf_str:>8s} [{comb['status']}]")
        print(f"      Combined ratio: {comb['combined_ratio']:.4f}")
        print(f"      Design factor: {comb['design_factor']}")

        # Limiting check
        limiting = cond['limiting']
        lim_sf = limiting['safety_factor']
        lim_sf_str = f"{lim_sf:.2f}" if lim_sf != float('inf') else "INF"
        print(f"\n  Limiting Check: {limiting['name']} (SF={lim_sf_str})")

    print("\n" + "="*80)
    print("VALIDATION CHECKS")
    print("="*80)

    # Validate expected behavior
    conditions = result["conditions"]

    # Check 1: Top positions should have atmospheric pressure only
    print("\n1. External Pressure Validation:")
    for pos in ["top"]:
        for stage in ["installation", "hydrotest", "operation"]:
            key = f"{stage}_{pos}"
            po = conditions[key]["p_external_psi"]
            print(f"   {key:25s}: Po = {po:.1f} psi {'[OK] (atmospheric)' if abs(po - 14.7) < 0.1 else '[ERROR]'}")

    # Check 2: Bottom positions should have atmospheric + hydrostatic
    print("\n2. Bottom Pressure Validation:")
    for stage in ["installation", "hydrotest", "operation"]:
        key = f"{stage}_bottom"
        po = conditions[key]["p_external_psi"]
        expected_hydro = 920.0 * 3.28084 * 64.0 / 144.0  # depth_m × ft/m × density / 144
        expected_total = 14.7 + expected_hydro
        print(f"   {key:25s}: Po = {po:.1f} psi (expected ~{expected_total:.1f}) {'[OK]' if abs(po - expected_total) < 1.0 else '[ERROR]'}")

    # Check 3: Operation uses different pressures for different checks
    print("\n3. Operation Internal Pressure Validation:")
    print(f"   Design pressure: {load.design_pressure_psi} psi")
    print(f"   Shut-in pressure: {load.shut_in_pressure_psi} psi")
    for pos in ["top", "bottom"]:
        key = f"operation_{pos}"
        pi_burst = conditions[key]["p_internal_burst"]
        pi_collapse = conditions[key]["p_internal_collapse"]
        print(f"   {key:25s}:")
        print(f"     Burst/Hoop/Long/Comb: {pi_burst:.0f} psi {'[OK] (design)' if abs(pi_burst - 1400) < 0.1 else '[ERROR]'}")
        print(f"     Collapse/Propagation: {pi_collapse:.0f} psi {'[OK] (shut-in)' if abs(pi_collapse - 1236) < 0.1 else '[ERROR]'}")

    # Check 4: Top has tension, bottom has zero
    print("\n4. Longitudinal Tension Validation:")
    for stage in ["installation", "hydrotest", "operation"]:
        for pos in ["top", "bottom"]:
            key = f"{stage}_{pos}"
            ta = conditions[key]["longitudinal"]["t_a_applied_kips"]
            if pos == "top":
                print(f"   {key:25s}: T_a = {ta:8.2f} kips {'[OK] (has tension)' if ta > 0 else '[ERROR]'}")
            else:
                print(f"   {key:25s}: T_a = {ta:8.2f} kips {'[OK] (zero)' if abs(ta) < 0.01 else '[ERROR]'}")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

    return result


if __name__ == "__main__":
    try:
        result = test_multiphase_riser()
        print("\n[SUCCESS] Test completed successfully!")
        print(f"Overall: {'ALL 6 CONDITIONS PASS' if result['all_conditions_pass'] else 'SOME CONDITIONS FAIL'}")
    except Exception as e:
        print(f"\n[FAILED] Test failed with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
