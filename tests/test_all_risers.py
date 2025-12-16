"""
Test script to verify all 24 riser IDs can be analyzed without errors.
Run this to validate the calculation modules work correctly.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from reference_data import asme_b36_10
from calculations import calcs_burst, calcs_collapse, calcs_propagation, calcs_bending, calcs_hoop


def load_riser_database():
    """Load the riser database from JSON file"""
    db_path = Path(__file__).parent.parent / "reference_data" / "riser_database.json"
    with open(db_path, 'r') as f:
        data = json.load(f)
    return data.get('risers', {})


def calculate_external_pressure_from_depth(depth_m, seawater_density_pcf=64.0):
    """Convert water depth to hydrostatic pressure in psi"""
    depth_ft = depth_m * 3.28084
    pressure_psi = seawater_density_pcf * depth_ft / 144.0
    return pressure_psi


def get_effective_wt(nominal_wt, mill_tolerance, corrosion_allowance):
    """Calculate effective wall thickness"""
    return nominal_wt * (1 - mill_tolerance / 100.0) - corrosion_allowance


def test_riser(riser_id, riser_config):
    """Test a single riser configuration"""
    print(f"\n{'='*70}")
    print(f"Testing Riser ID {riser_id}: {riser_config['name']}")
    print(f"{'='*70}")
    
    # Extract parameters
    geom = riser_config['geometry']
    mat = riser_config['material']
    loads = riser_config['loads']
    
    od = geom['od_inches']
    ovality = geom['ovality']
    corrosion = geom['corrosion_allowance_inches']
    mill_tolerance = geom['mill_tolerance_percent']
    
    smys_ksi = mat['smys_ksi']
    uts_ksi = mat['uts_ksi']
    E_ksi = mat['modulus_of_elasticity_ksi']
    poisson = mat['poisson_ratio']
    
    p_i_psi = loads['design_internal_pressure_psi']
    depth_lat_m = loads['depth_lat_m']
    depth_hat_m = loads['depth_hat_m']
    bending_strain = loads['bending_strain']
    
    pipe_type = riser_config.get('type', 'Riser')
    manufacturing = riser_config.get('manufacturing', 'DSAW')
    
    # Calculate external pressures from depth
    p_o_lat_psi = calculate_external_pressure_from_depth(depth_lat_m)
    p_o_hat_psi = calculate_external_pressure_from_depth(depth_hat_m)
    
    # Use annulus pressure if specified
    if loads.get('use_annulus_pressure') and loads.get('design_external_pressure_psi'):
        p_o_hat_psi = loads['design_external_pressure_psi']
        p_o_lat_psi = loads['design_external_pressure_psi']
    
    # Convert to ksi
    p_i_ksi = p_i_psi / 1000.0
    p_o_hat_ksi = p_o_hat_psi / 1000.0
    p_o_lat_ksi = p_o_lat_psi / 1000.0
    
    # Get standard thicknesses for this OD
    thicknesses = asme_b36_10.get_standard_thicknesses(od)
    
    if thicknesses is None:
        print(f"  ERROR: No standard thicknesses found for OD {od}\"")
        return False, f"No standard thicknesses for OD {od}\""
    
    print(f"  OD: {od}\" | SMYS: {smys_ksi} ksi | Type: {pipe_type}")
    print(f"  Internal Pressure: {p_i_psi} psi ({p_i_ksi:.3f} ksi)")
    print(f"  External Pressure HAT: {p_o_hat_psi:.1f} psi ({p_o_hat_ksi:.4f} ksi)")
    print(f"  External Pressure LAT: {p_o_lat_psi:.1f} psi ({p_o_lat_ksi:.4f} ksi)")
    print(f"  Available wall thicknesses: {len(thicknesses)} options")
    print(f"  Range: {thicknesses[0]}\" to {thicknesses[-1]}\"")
    
    # Test with a mid-range wall thickness
    test_wt = thicknesses[len(thicknesses)//2]  # Middle thickness
    effective_wt = get_effective_wt(test_wt, mill_tolerance, corrosion)
    
    print(f"\n  Testing with WT = {test_wt}\" (effective: {effective_wt:.4f}\")")
    
    errors = []
    
    # Test burst calculation
    try:
        burst_result = calcs_burst.check_burst_criteria(
            od, effective_wt, smys_ksi, uts_ksi, p_i_ksi, p_o_lat_ksi,
            pipe_type, manufacturing
        )
        print(f"  ✓ Burst: {'PASS' if burst_result['pass_fail'] else 'FAIL'}")
    except Exception as e:
        errors.append(f"Burst: {str(e)}")
        print(f"  ✗ Burst: ERROR - {str(e)}")
    
    # Test collapse calculation
    try:
        collapse_result = calcs_collapse.check_collapse_criteria(
            od, effective_wt, smys_ksi, E_ksi, p_i_ksi, p_o_hat_ksi,
            manufacturing, poisson, ovality
        )
        print(f"  ✓ Collapse: {'PASS' if collapse_result['pass_fail'] else 'FAIL'}")
    except Exception as e:
        errors.append(f"Collapse: {str(e)}")
        print(f"  ✗ Collapse: ERROR - {str(e)}")
    
    # Test propagation calculation
    try:
        net_external = p_o_hat_ksi - p_i_ksi
        propagation_result = calcs_propagation.check_propagation_criteria(
            od, effective_wt, smys_ksi, net_external
        )
        print(f"  ✓ Propagation: {'PASS' if propagation_result['pass_fail'] else 'FAIL'} (net ext: {net_external:.4f} ksi)")
    except Exception as e:
        errors.append(f"Propagation: {str(e)}")
        print(f"  ✗ Propagation: ERROR - {str(e)}")
    
    # Test bending calculation
    try:
        bending_result = calcs_bending.check_combined_bending_pressure(
            od, effective_wt, smys_ksi, E_ksi, p_i_ksi, p_o_hat_ksi,
            bending_strain, collapse_result['critical_collapse'], ovality
        )
        print(f"  ✓ Bending: {'PASS' if bending_result['pass_fail'] else 'FAIL'}")
    except Exception as e:
        errors.append(f"Bending: {str(e)}")
        print(f"  ✗ Bending: ERROR - {str(e)}")
    
    # Test hoop stress calculation
    try:
        smys_psi = smys_ksi * 1000
        hoop_result = calcs_hoop.check_hoop_stress_criteria(
            od, effective_wt, p_i_psi, smys_psi, design_factor=0.72
        )
        print(f"  ✓ Hoop: {'PASS' if hoop_result['pass_fail'] else 'FAIL'}")
    except Exception as e:
        errors.append(f"Hoop: {str(e)}")
        print(f"  ✗ Hoop: ERROR - {str(e)}")
    
    # Find minimum passing thickness
    print(f"\n  Searching for minimum passing wall thickness...")
    min_pass_wt = None
    for wt in thicknesses:
        eff_wt = get_effective_wt(wt, mill_tolerance, corrosion)
        if eff_wt <= 0:
            continue
        
        try:
            # Quick pass/fail check
            burst = calcs_burst.check_burst_criteria(
                od, eff_wt, smys_ksi, uts_ksi, p_i_ksi, p_o_lat_ksi,
                pipe_type, manufacturing
            )
            
            collapse = calcs_collapse.check_collapse_criteria(
                od, eff_wt, smys_ksi, E_ksi, p_i_ksi, p_o_hat_ksi,
                manufacturing, poisson, ovality
            )
            
            net_ext = p_o_hat_ksi - p_i_ksi
            prop = calcs_propagation.check_propagation_criteria(
                od, eff_wt, smys_ksi, net_ext
            )
            
            bend = calcs_bending.check_combined_bending_pressure(
                od, eff_wt, smys_ksi, E_ksi, p_i_ksi, p_o_hat_ksi,
                bending_strain, collapse['critical_collapse'], ovality
            )
            
            hoop = calcs_hoop.check_hoop_stress_criteria(
                od, eff_wt, p_i_psi, smys_psi, design_factor=0.72
            )
            
            if all([burst['pass_fail'], collapse['pass_fail'], prop['pass_fail'], 
                    bend['pass_fail'], hoop['pass_fail']]):
                min_pass_wt = wt
                break
                
        except Exception as e:
            # Skip this thickness if error
            continue
    
    if min_pass_wt:
        print(f"  ✓ Minimum passing WT: {min_pass_wt}\"")
    else:
        print(f"  ⚠ No standard thickness passed all checks")
        print(f"    Consider: Increasing OD, upgrading material grade, or reducing design pressures")
    
    success = len(errors) == 0
    return success, errors if errors else None


def main():
    print("="*70)
    print("RISER DATABASE VALIDATION TEST")
    print("Testing all 24 riser configurations")
    print("="*70)
    
    # Load database
    riser_db = load_riser_database()
    
    if not riser_db:
        print("ERROR: Could not load riser database!")
        return
    
    print(f"Loaded {len(riser_db)} riser configurations")
    
    # Test each riser
    results = {}
    for riser_id in sorted(riser_db.keys(), key=lambda x: int(x)):
        riser_config = riser_db[riser_id]
        success, errors = test_riser(riser_id, riser_config)
        results[riser_id] = {'success': success, 'errors': errors}
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results.values() if r['success'])
    failed = len(results) - passed
    
    print(f"Total Risers: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed Risers:")
        for riser_id, result in results.items():
            if not result['success']:
                print(f"  ID {riser_id}: {result['errors']}")
    
    print("\n" + "="*70)
    if failed == 0:
        print("✓ ALL RISERS PASSED VALIDATION!")
    else:
        print(f"✗ {failed} RISERS HAVE CALCULATION ERRORS")
    print("="*70)


if __name__ == "__main__":
    main()
