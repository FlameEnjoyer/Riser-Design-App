"""
Riser Design Calculation Web App
API RP 1111 + ASME B31.4/B31.8 checks

Three Life Cycle Conditions:
- Installation: No internal pressure, no corrosion, with mill tolerance
- Hydrotest: Elevated internal pressure (1.25x design), no corrosion, with mill tolerance
- Operation: Design pressures, with corrosion and mill tolerance
"""

import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Tuple

import pandas as pd
import streamlit as st

from reference_data import asme_b36_10
from calculations import calcs_weight

# -----------------------------------------------------------------------------
# Constants and reference data
# -----------------------------------------------------------------------------
COLOR_PRIMARY = "#1e3a8a"
COLOR_SECONDARY = "#3b82f6"
COLOR_SUCCESS = "#10b981"
COLOR_ALERT = "#ef4444"

GRADE_PROPERTIES = {
    # API 5L Grades (Specification for Line Pipe)
    # Format: Grade: {SMYS (ksi), UTS (ksi)}
    "A25": {"smys_psi": 25000, "uts_psi": 45000},
    "A": {"smys_psi": 30000, "uts_psi": 48000},
    "B": {"smys_psi": 35000, "uts_psi": 60000},
    "X-42": {"smys_psi": 42000, "uts_psi": 60000},
    "X-46": {"smys_psi": 46000, "uts_psi": 63000},
    "X-52": {"smys_psi": 52000, "uts_psi": 66000},
    "X-56": {"smys_psi": 56000, "uts_psi": 71000},
    "X-60": {"smys_psi": 60000, "uts_psi": 75000},
    "X-65": {"smys_psi": 65000, "uts_psi": 77000},
    "X-70": {"smys_psi": 70000, "uts_psi": 82000},
    "X-80": {"smys_psi": 80000, "uts_psi": 90000},
    "X-90": {"smys_psi": 90000, "uts_psi": 100000},
    "X-100": {"smys_psi": 100000, "uts_psi": 110000},
    "X-120": {"smys_psi": 120000, "uts_psi": 130000},
}

MANUFACTURING_COLLAPSE_FACTOR = {
    "SMLS": 0.70,
    "ERW": 0.75,
    "DSAW": 0.60,
}

DEFAULT_E_PSI = 2.9e7
DEFAULT_POISSON = 0.30
DEFAULT_WATER_DENSITY = 64.0  # lb/ft^3

# Design life and corrosion parameters (from Team 8 data)
DESIGN_LIFE_YEARS = 20
CORROSION_RATE_PER_YEAR = 0.004  # inch/year
MILL_TOLERANCE = 0.125  # 12.5% = wall thickness factor 0.875
HYDROTEST_FACTOR = 1.25

TEAM8_REFERENCE = {
    "Multiphase Riser (ID 3)": {
        "od": 16.0,
        "wt": 0.750,
        "grade": "X-52",
        "design_pressure": 1400.0,  # Design pressure for sizing
        "shut_in_pressure": 1236.0,  # Shut-in pressure = internal pressure (Pi)
        "shut_in_location": "Subsea Wellhead",
        "water_depth": 920.0,  # Kedalam Laut (m)
        "fluid_type": "Multiphase",
        "fluid_sg": 0.57,
        "manufacturing": "SMLS",
        "design_category": "Riser",
        "ovality_type": "Other Type",
        "ovality": 0.005,  # 0.5%
    },
    "Oil Riser (ID 8)": {
        "od": 8.63,
        "wt": 0.500,
        "grade": "X-52",
        "design_pressure": 230.0,  # Design pressure for sizing
        "shut_in_pressure": 195.0,  # Shut-in pressure = internal pressure (Pi)
        "shut_in_location": "Subsea Wellhead",
        "water_depth": 960.0,  # Kedalam Laut (m)
        "fluid_type": "Oil",
        "fluid_sg": 0.82,
        "manufacturing": "SMLS",
        "design_category": "Riser",
        "ovality_type": "Other Type",
        "ovality": 0.005,
    },
}


def schedule_name_for_thickness(od: float, wt: float) -> str:
    names = asme_b36_10.get_schedule_for_thickness(od, wt)
    if not names:
        return "Custom"
    return "/".join(names)


# -----------------------------------------------------------------------------
# Data classes
# -----------------------------------------------------------------------------
@dataclass
class PipeProperties:
    od_in: float
    wt_in: float
    grade: str
    manufacturing: str
    design_category: str  # "Pipeline" or "Riser"
    fluid_type: str  # Gas, Oil, Multiphase, Wet Gas
    fluid_sg: float
    smys_psi: float
    uts_psi: float
    ovality_type: str  # "Reel-lay" or "Other Type"
    ovality: float
    E_psi: float = DEFAULT_E_PSI
    poisson: float = DEFAULT_POISSON


@dataclass
class LoadingCondition:
    design_pressure_psi: float
    shut_in_pressure_psi: float
    shut_in_location: str  # "Subsea Wellhead" or "Top of Riser"
    water_depth_m: float
    riser_length_m: float  # For longitudinal tension calculation


# -----------------------------------------------------------------------------
# Life Cycle Analyzer
# -----------------------------------------------------------------------------
class LifeCycleAnalyzer:
    """Analyzes all three life cycle conditions: Installation, Hydrotest, Operation"""
    
    def __init__(self, pipe: PipeProperties, load: LoadingCondition):
        self.pipe = pipe
        self.load = load

    @staticmethod
    def _ft_from_m(depth_m: float) -> float:
        return depth_m * 3.28084

    def external_pressure_psi(self) -> float:
        """Calculate hydrostatic external pressure"""
        depth_ft = self._ft_from_m(self.load.water_depth_m)
        return DEFAULT_WATER_DENSITY * depth_ft / 144.0

    def external_pressure_psi_for_position(self, position: str) -> float:
        """
        Calculate external pressure based on riser position

        Parameters:
        -----------
        position : str
            "Top" or "Bottom"

        Returns:
        --------
        float : External pressure in psi

        Top Position: Atmospheric only (14.7 psi)
        Bottom Position: Atmospheric + Hydrostatic

        Physical Basis:
        - Top of riser is at sea surface → atmospheric pressure
        - Bottom of riser is at water depth → atmospheric + hydrostatic
        """
        ATMOSPHERIC_PSI = 14.7

        if position.lower() == "top":
            return ATMOSPHERIC_PSI
        else:  # bottom
            depth_ft = self._ft_from_m(self.load.water_depth_m)
            hydrostatic_psi = DEFAULT_WATER_DENSITY * depth_ft / 144.0
            return ATMOSPHERIC_PSI + hydrostatic_psi

    def calculate_mop(self) -> float:
        """
        Calculate MOP (Maximum Operating Pressure) per API RP 1111

        MOP = Shut-in Pressure - Hydrostatic Head of Riser Contents

        The hydrostatic head is the pressure exerted by the fluid column
        inside the riser from bottom to top.

        Formula:
        Hydrostatic Head (psi) = (fluid_sg × water_density_pcf) × riser_length_ft / 144

        Where:
        - fluid_sg: Fluid specific gravity (dimensionless)
        - water_density_pcf: 64 lb/ft³ (seawater)
        - riser_length_ft: Riser vertical length in feet
        - 144: Conversion factor from lb/ft² to psi

        Returns:
        --------
        float : MOP in psi

        Notes:
        - MOP is only different from shut-in when shut-in location is at Subsea Wellhead
        - When shut-in is at Top of Riser, MOP = shut-in pressure (no adjustment)
        - MOP represents the pressure at top of riser when shut-in valve closes at bottom
        """
        # If shut-in location is at top, MOP = shut-in (no adjustment needed)
        if self.load.shut_in_location == "Top of Riser":
            return self.load.shut_in_pressure_psi

        # Calculate hydrostatic head of riser contents
        riser_length_ft = self._ft_from_m(self.load.riser_length_m)
        fluid_density_pcf = self.pipe.fluid_sg * DEFAULT_WATER_DENSITY  # lb/ft³
        hydrostatic_head_psi = (fluid_density_pcf * riser_length_ft) / 144.0

        # MOP = Shut-in pressure at bottom - hydrostatic head
        mop = self.load.shut_in_pressure_psi - hydrostatic_head_psi

        return max(mop, 0.0)  # Ensure non-negative

    def get_internal_pressure_for_check(self, condition_name: str, check_type: str, position: str = "Top") -> float:
        """
        Determine internal pressure based on condition, check type, and position

        Parameters:
        -----------
        condition_name : str
            "Installation", "Hydrotest", or "Operation"
        check_type : str
            "burst", "collapse", "propagation", "hoop", "longitudinal", "combined"
        position : str
            "Top" or "Bottom" - riser position being analyzed

        Returns:
        --------
        float : Internal pressure in psi

        CRITICAL LOGIC FOR OPERATION CONDITION WITH MOP:

        Pressure Selection Strategy:
        1. Burst, Hoop, Longitudinal, Combined → Always use DESIGN PRESSURE
        2. Collapse, Propagation → Use shut-in or MOP based on position and shut-in location

        MOP (Maximum Operating Pressure) Logic:
        - MOP = Shut-in Pressure - Hydrostatic Head of Riser Contents
        - Only applies when shut-in location is "Subsea Wellhead"
        - When analyzing TOP position with shut-in at BOTTOM → Use MOP
        - When analyzing BOTTOM position → Use full shut-in pressure
        - When shut-in at TOP → MOP = shut-in (no adjustment needed)

        Rationale:
        - Design pressure ensures adequate burst/hoop resistance for sizing
        - MOP/shut-in pressure used for collapse (actual operating pressures)
        - Position-dependent pressure accounts for fluid column weight
        """
        if condition_name == "Installation":
            # Empty pipe during installation
            return 0.0

        elif condition_name == "Hydrotest":
            # Elevated test pressure (1.25x design)
            return self.load.design_pressure_psi * HYDROTEST_FACTOR

        elif condition_name == "Operation":
            # CRITICAL: Different pressures per check type

            # Design pressure checks (burst, hoop, longitudinal, combined)
            if check_type in ["burst", "hoop", "longitudinal", "combined"]:
                # Always use design pressure for these checks
                return self.load.design_pressure_psi

            # Collapse and propagation checks - use shut-in/MOP
            elif check_type in ["collapse", "propagation"]:
                # Check shut-in location
                if self.load.shut_in_location == "Subsea Wellhead":
                    # Shut-in valve at bottom of riser
                    if position.lower() == "top":
                        # At top: Use MOP (shut-in minus hydrostatic head)
                        return self.calculate_mop()
                    else:
                        # At bottom: Use full shut-in pressure
                        return self.load.shut_in_pressure_psi
                else:
                    # Shut-in location at "Top of Riser"
                    # MOP = shut-in (no adjustment), use for all positions
                    return self.load.shut_in_pressure_psi

        return 0.0

    def calculate_longitudinal_load(self, wt_eff: float, p_internal: float,
                                     p_external: float, condition_name: str,
                                     position: str) -> Dict[str, Any]:
        """
        Calculate longitudinal tension per API RP 1111 Section 4.3.1.1

        CRITICAL CHANGE: Position-dependent applied tension

        Longitudinal Load Design:
        T_eff = T_a - P_i × A_i + P_o × A_o

        Acceptance Criterion:
        T_eff ≤ 0.60 × T_y

        Position Effects:
        - Top: T_a = void_submerged_weight × riser_length (maximum tension)
        - Bottom: T_a = 0 (supported by mudline/seabed)

        Where:
        - T_a: Applied axial tension from self-weight (lb)
        - T_eff: Effective tension accounting for pressure end-cap forces
        - T_y: Yield tension = SMYS × A_steel
        - P_i: Internal pressure (position-specific)
        - P_o: External pressure (position-specific)
        - A_i: Internal cross-sectional area
        - A_o: External cross-sectional area

        BUOYANCY NOTE: void_submerged_weight already accounts for buoyancy
        void_submerged = dry_weight - (water_density × displaced_volume)
        """
        # Calculate cross-sectional areas (in²)
        od = self.pipe.od_in
        id_val = od - 2 * wt_eff

        a_outer = math.pi / 4 * od**2  # External area
        a_inner = math.pi / 4 * id_val**2  # Internal area
        a_steel = a_outer - a_inner  # Steel cross-section

        # Calculate pipe weights using effective WT
        weights = calcs_weight.calculate_pipe_weights(
            od_inches=od,
            wt_inches=wt_eff,
            fluid_sg=self.pipe.fluid_sg,
            use_seawater=True
        )

        # Applied tension T_a from self-weight - POSITION DEPENDENT
        # BUOYANCY is accounted for in void_submerged_weight_plf
        void_submerged_plf = weights['void_submerged_weight_plf']

        if position.lower() == "top":
            # Top of riser: Full tension from entire suspended weight
            riser_length_ft = self._ft_from_m(self.load.riser_length_m)
            t_a_lb = void_submerged_plf * riser_length_ft
            riser_length_ft_display = riser_length_ft
        else:  # bottom
            # Bottom of riser: Supported by mudline/seabed
            t_a_lb = 0.0
            riser_length_ft_display = 0.0
        
        # Pressure end-cap forces
        # Internal pressure creates upward force (reduces tension)
        # External pressure creates downward force (increases tension)
        force_internal_lb = p_internal * a_inner  # lb (reduces tension)
        force_external_lb = p_external * a_outer  # lb (increases tension)
        
        # Effective tension (lb)
        t_eff_lb = t_a_lb - force_internal_lb + force_external_lb
        
        # Yield tension (lb)
        t_y_lb = self.pipe.smys_psi * a_steel
        
        # Allowable tension per API RP 1111: 0.60 × T_y
        allowable_tension_lb = 0.60 * t_y_lb
        
        # Safety factor
        if t_eff_lb <= 0:
            # Compression case (not covered by this check)
            safety_factor = float('inf')
            passes = True
            status = "Compression (N/A)"
        else:
            safety_factor = allowable_tension_lb / t_eff_lb
            passes = safety_factor >= 1.0
            status = "PASS" if passes else "FAIL"
        
        # Axial stress in pipe wall (psi)
        axial_stress_psi = t_eff_lb / a_steel if a_steel > 0 else 0
        
        return {
            "condition": condition_name,
            "position": position,
            "t_a_applied_lb": t_a_lb,
            "t_a_applied_kips": t_a_lb / 1000,
            "force_internal_lb": force_internal_lb,
            "force_external_lb": force_external_lb,
            "t_eff_effective_lb": t_eff_lb,
            "t_eff_effective_kips": t_eff_lb / 1000,
            "t_y_yield_lb": t_y_lb,
            "t_y_yield_kips": t_y_lb / 1000,
            "allowable_tension_lb": allowable_tension_lb,
            "allowable_tension_kips": allowable_tension_lb / 1000,
            "axial_stress_psi": axial_stress_psi,
            "axial_stress_ksi": axial_stress_psi / 1000,
            "safety_factor": safety_factor,
            "passes": passes,
            "status": status,
            "criterion": "T_eff ≤ 0.60 × T_y (API RP 1111 Section 4.3.1.1)",
            "a_outer_in2": a_outer,
            "a_inner_in2": a_inner,
            "a_steel_in2": a_steel,
            "void_submerged_plf": void_submerged_plf,
            "riser_length_ft": riser_length_ft_display,
        }
    
    def calculate_combined_load(self, wt_eff: float, p_internal: float,
                                 p_external: float, condition_name: str,
                                 position: str) -> Dict[str, Any]:
        """
        Calculate combined loading per API RP 1111 Section 4.3.1.2

        Combined Load Design:
        √[(P_i - P_o)² / P_b²] + (T_eff / T_y)² ≤ Design Factor

        Design Factors:
        - 0.90 for operational loads
        - 0.96 for extreme loads (storm, earthquake)
        - 0.96 for hydrotest loads

        Position affects longitudinal component through T_eff calculation.

        This is the most comprehensive check that combines:
        1. Pressure loading (burst/collapse)
        2. Longitudinal tension (from weight and pressure end-caps, position-dependent)
        """
        # Get longitudinal load results with position
        longitudinal = self.calculate_longitudinal_load(
            wt_eff, p_internal, p_external, condition_name, position
        )
        
        # Get burst pressure using class method
        burst_result = self.compute_burst(p_internal, p_external, wt_eff)
        p_b = burst_result["pb"]  # Burst pressure capacity
        
        # Differential pressure (positive = burst, negative = collapse)
        p_diff = p_internal - p_external
        
        # Pressure component: (P_i - P_o) / P_b
        # For collapse cases (negative p_diff), we still use absolute value
        # per API RP 1111 interpretation
        pressure_component = (p_diff / p_b) if p_b > 0 else 0
        
        # Tension component: T_eff / T_y
        t_eff = longitudinal["t_eff_effective_lb"]
        t_y = longitudinal["t_y_yield_lb"]
        tension_component = (t_eff / t_y) if t_y > 0 else 0
        
        # Combined load ratio
        combined_ratio = math.sqrt(pressure_component**2 + tension_component**2)
        
        # Determine design factor based on condition
        if condition_name == "Operation":
            design_factor = 0.90  # Operational loads
            factor_description = "0.90 (Operational)"
        elif condition_name == "Hydrotest":
            design_factor = 0.96  # Hydrotest loads
            factor_description = "0.96 (Hydrotest)"
        else:  # Installation
            design_factor = 0.96  # Extreme loads (conservative)
            factor_description = "0.96 (Extreme)"
        
        # Safety factor (design_factor / combined_ratio)
        if combined_ratio > 0:
            safety_factor = design_factor / combined_ratio
        else:
            safety_factor = float('inf')
        
        passes = combined_ratio <= design_factor
        status = "PASS" if passes else "FAIL"
        
        return {
            "condition": condition_name,
            "position": position,
            "p_internal_psi": p_internal,
            "p_external_psi": p_external,
            "p_diff_psi": p_diff,
            "p_b_burst_psi": p_b,
            "pressure_component": pressure_component,
            "t_eff_lb": t_eff,
            "t_y_lb": t_y,
            "tension_component": tension_component,
            "combined_ratio": combined_ratio,
            "design_factor": design_factor,
            "factor_description": factor_description,
            "safety_factor": safety_factor,
            "passes": passes,
            "status": status,
            "criterion": f"√[(P/Pb)² + (T/Ty)²] ≤ {design_factor} (API RP 1111 Section 4.3.1.2)",
        }

    def effective_wall_thickness(self, use_mill_tolerance: bool, use_corrosion: bool) -> float:
        """
        Calculate effective wall thickness per life cycle condition
        - Installation/Hydrotest: WT × 0.875 (mill tolerance only)
        - Operation: (WT × 0.875) - (corrosion_rate × design_life)
        """
        wt = self.pipe.wt_in
        
        # Apply mill tolerance (12.5% reduction = 0.875 factor)
        if use_mill_tolerance:
            wt = wt * (1.0 - MILL_TOLERANCE)
        
        # Apply corrosion (only for operation: rate × design life)
        if use_corrosion:
            corrosion_total = CORROSION_RATE_PER_YEAR * DESIGN_LIFE_YEARS
            wt = wt - corrosion_total
        
        return max(wt, 0.001)  # Ensure positive

    def _hoop_design_factor(self) -> float:
        """Design factor per ASME B31.4/B31.8 based on category and fluid type"""
        if self.pipe.design_category.lower() == "pipeline":
            return 0.72
        # Riser design factors
        if self.pipe.fluid_type.lower() in ["gas", "wet gas"]:
            return 0.50
        if self.pipe.fluid_type.lower() in ["oil", "multiphase"]:
            return 0.60
        return 0.72

    @staticmethod
    def _burst_design_factor(design_category: str) -> float:
        """Burst design factor per API RP 1111 Section 4.3.1"""
        return 0.90 if design_category.lower() == "pipeline" else 0.75

    def compute_burst(self, p_internal: float, p_external: float, wt_eff: float) -> Dict[str, Any]:
        """Burst pressure check per API RP 1111 Section 4.3.1"""
        fd = self._burst_design_factor(self.pipe.design_category)
        fe = 1.0  # Weld joint factor
        ft = 1.0  # Temperature factor
        od = self.pipe.od_in
        smys = self.pipe.smys_psi
        uts = self.pipe.uts_psi

        pb = 0.90 * (smys + uts) * wt_eff / (od - wt_eff) if od > wt_eff else 0.0
        delta_p = p_internal - p_external
        
        if delta_p <= 0:
            sf = float("inf")
        else:
            sf = (fd * fe * ft * pb) / delta_p

        return {
            "name": "Burst",
            "pb": pb,
            "safety_factor": sf,
            "utilization": 0 if sf == float("inf") else 1 / sf,
            "pass_fail": sf >= 1.0,
            "details": {
                "design_factor": fd,
                "joint_factor": fe,
                "temperature_factor": ft,
                "delta_p": delta_p,
            },
        }

    def compute_collapse(self, p_internal: float, p_external: float, wt_eff: float) -> Dict[str, Any]:
        """External collapse check per API RP 1111 Section 4.3.2"""
        od = self.pipe.od_in
        smys = self.pipe.smys_psi
        E = self.pipe.E_psi
        nu = self.pipe.poisson
        ovality = self.pipe.ovality
        f_o = MANUFACTURING_COLLAPSE_FACTOR.get(self.pipe.manufacturing.upper(), 0.70)

        t_over_d = wt_eff / od
        py = 2 * smys * t_over_d
        # Pe adjusted for ovality per API RP 1111 Section 4.3.2
        pe = (2 * E * (t_over_d ** 3)) / ((1 - nu ** 2) * (1 + ovality))
        pc = (py * pe) / math.sqrt(py ** 2 + pe ** 2) if (py > 0 and pe > 0) else 0.0

        delta_p = p_external - p_internal
        if delta_p <= 0:
            sf = float("inf")
        else:
            sf = (f_o * pc) / delta_p

        return {
            "name": "Collapse",
            "py": py,
            "pe": pe,
            "pc": pc,
            "collapse_factor": f_o,
            "ovality": ovality,
            "safety_factor": sf,
            "utilization": 0 if sf == float("inf") else 1 / sf,
            "pass_fail": sf >= 1.0,
            "details": {"delta_p": delta_p},
        }

    def compute_propagation(self, p_internal: float, p_external: float, wt_eff: float) -> Dict[str, Any]:
        """Propagation buckling check per API RP 1111 Section 4.3.2.3"""
        od = self.pipe.od_in
        smys = self.pipe.smys_psi
        fp = 0.80
        t_over_d = wt_eff / od
        pp = 35 * smys * (t_over_d ** 2.5)
        delta_p = p_external - p_internal

        if delta_p <= 0:
            sf = float("inf")
        else:
            sf = (fp * pp) / delta_p

        return {
            "name": "Propagation",
            "pp": pp,
            "design_factor": fp,
            "safety_factor": sf,
            "utilization": 0 if sf == float("inf") else 1 / sf,
            "pass_fail": sf >= 1.0,
            "details": {"delta_p": delta_p},
        }

    def compute_hoop(self, p_internal: float, p_external: float, wt_eff: float) -> Dict[str, Any]:
        """Hoop stress check per ASME B31.4 Section 402.3"""
        od = self.pipe.od_in
        smys = self.pipe.smys_psi
        design_factor = self._hoop_design_factor()
        delta_p = p_internal - p_external

        if wt_eff <= 0 or od <= wt_eff:
            hoop_stress = float("inf")
        else:
            hoop_stress = delta_p * od / (2 * wt_eff)

        allowable = design_factor * smys
        sf = allowable / hoop_stress if hoop_stress > 0 else float("inf")

        return {
            "name": "Hoop Stress",
            "hoop_stress": hoop_stress,
            "design_factor": design_factor,
            "allowable": allowable,
            "safety_factor": sf,
            "utilization": 0 if sf == float("inf") else 1 / sf,
            "pass_fail": sf >= 1.0,
            "details": {"delta_p": delta_p},
        }

    def analyze_condition(self, condition_name: str, p_internal: float, 
                          use_mill_tolerance: bool, use_corrosion: bool) -> Dict[str, Any]:
        """Analyze one life cycle condition"""
        p_external = self.external_pressure_psi()
        wt_eff = self.effective_wall_thickness(use_mill_tolerance, use_corrosion)
        
        # Calculate pipe weights for this condition
        weights = calcs_weight.calculate_pipe_weights(
            od_inches=self.pipe.od_in,
            wt_inches=wt_eff,  # Use effective WT for this condition
            fluid_sg=self.pipe.fluid_sg,
            use_seawater=True
        )

        burst = self.compute_burst(p_internal, p_external, wt_eff)
        collapse = self.compute_collapse(p_internal, p_external, wt_eff)
        propagation = self.compute_propagation(p_internal, p_external, wt_eff)
        hoop = self.compute_hoop(p_internal, p_external, wt_eff)
        
        # NEW: Calculate longitudinal tension (Section 4.3.1.1)
        longitudinal = self.calculate_longitudinal_load(wt_eff, p_internal, condition_name)
        
        # NEW: Calculate combined loading (Section 4.3.1.2)
        combined = self.calculate_combined_load(wt_eff, p_internal, condition_name)

        checks = [burst, collapse, propagation, hoop]
        limiting = min(
            checks,
            key=lambda c: c["safety_factor"] if c["safety_factor"] != float("inf") else float("inf"),
        )
        # Update all_pass to include longitudinal and combined checks
        all_pass = all(c["pass_fail"] for c in checks) and longitudinal["passes"] and combined["passes"]

        return {
            "condition_name": condition_name,
            "p_internal_psi": p_internal,
            "p_external_psi": p_external,
            "wt_nominal": self.pipe.wt_in,
            "wt_effective": wt_eff,
            "mill_tolerance_applied": use_mill_tolerance,
            "corrosion_applied": use_corrosion,
            "weights": weights,
            "checks": checks,
            "longitudinal": longitudinal,
            "combined": combined,
            "all_pass": all_pass,
            "limiting": limiting,
        }

    def analyze_condition_at_position(
        self,
        condition_name: str,  # "Installation", "Hydrotest", "Operation"
        position: str,        # "Top" or "Bottom"
        use_mill_tolerance: bool,
        use_corrosion: bool
    ) -> Dict[str, Any]:
        """
        Analyze one life cycle condition at a specific riser position

        This is the NEW core analysis method that replaces analyze_condition()
        for the 6-condition analysis (3 stages × 2 positions).

        Key Differences from Old Method:
        1. Position-dependent external pressure (Po)
        2. Check-type-dependent internal pressure (Pi) for Operation
        3. Position-dependent axial loading (T_a)

        Parameters:
        -----------
        condition_name : str
            "Installation", "Hydrotest", or "Operation"
        position : str
            "Top" or "Bottom"
        use_mill_tolerance : bool
            Apply 12.5% mill tolerance to WT
        use_corrosion : bool
            Apply corrosion allowance to WT

        Returns:
        --------
        Dict containing:
        - Position-specific pressures for each check
        - All 7 check results
        - Overall pass/fail status
        """
        # Calculate position-specific external pressure
        p_external = self.external_pressure_psi_for_position(position)

        # Calculate effective wall thickness (unchanged logic)
        wt_eff = self.effective_wall_thickness(use_mill_tolerance, use_corrosion)

        # Calculate pipe weights for this condition
        weights = calcs_weight.calculate_pipe_weights(
            od_inches=self.pipe.od_in,
            wt_inches=wt_eff,
            fluid_sg=self.pipe.fluid_sg,
            use_seawater=True
        )

        # Run pressure-only checks with check-type-specific internal pressure
        # NOW WITH MOP SUPPORT: position affects collapse/propagation pressures

        # 1. Burst check - uses design pressure (no MOP)
        p_i_burst = self.get_internal_pressure_for_check(condition_name, "burst", position)
        burst = self.compute_burst(p_i_burst, p_external, wt_eff)

        # 2. Collapse check - uses shut-in/MOP depending on position
        p_i_collapse = self.get_internal_pressure_for_check(condition_name, "collapse", position)
        collapse = self.compute_collapse(p_i_collapse, p_external, wt_eff)

        # 3. Propagation check - uses shut-in/MOP depending on position
        p_i_propagation = self.get_internal_pressure_for_check(condition_name, "propagation", position)
        propagation = self.compute_propagation(p_i_propagation, p_external, wt_eff)

        # 4. Hoop check - uses design pressure (no MOP)
        p_i_hoop = self.get_internal_pressure_for_check(condition_name, "hoop", position)
        hoop = self.compute_hoop(p_i_hoop, p_external, wt_eff)

        # 5. Longitudinal tension - uses design pressure, POSITION-AWARE
        p_i_longitudinal = self.get_internal_pressure_for_check(condition_name, "longitudinal", position)
        longitudinal = self.calculate_longitudinal_load(
            wt_eff, p_i_longitudinal, p_external, condition_name, position
        )

        # 6. Combined loading - uses design pressure, POSITION-AWARE
        p_i_combined = self.get_internal_pressure_for_check(condition_name, "combined", position)
        combined = self.calculate_combined_load(
            wt_eff, p_i_combined, p_external, condition_name, position
        )

        # Collect pressure-only checks
        checks = [burst, collapse, propagation, hoop]

        # Find limiting check among pressure-only checks
        limiting = min(
            checks,
            key=lambda c: c["safety_factor"] if c["safety_factor"] != float("inf") else float("inf"),
        )

        # Overall pass/fail includes all 6 checks (4 pressure + longitudinal + combined)
        all_pass = (
            all(c["pass_fail"] for c in checks) and
            longitudinal["passes"] and
            combined["passes"]
        )

        # Calculate MOP for information display
        mop_psi = self.calculate_mop()
        mop_active = (
            condition_name == "Operation" and
            self.load.shut_in_location == "Subsea Wellhead" and
            position.lower() == "top"
        )

        return {
            "condition_name": condition_name,
            "position": position,
            # Store pressures used for each check type (for UI display)
            "p_internal_burst": p_i_burst,      # Used by: burst, hoop, longitudinal, combined
            "p_internal_collapse": p_i_collapse,  # Used by: collapse, propagation
            "p_external_psi": p_external,
            "wt_nominal": self.pipe.wt_in,
            "wt_effective": wt_eff,
            "mill_tolerance_applied": use_mill_tolerance,
            "corrosion_applied": use_corrosion,
            "weights": weights,
            "checks": checks,
            "longitudinal": longitudinal,
            "combined": combined,
            "all_pass": all_pass,
            "limiting": limiting,
            # MOP information
            "mop_psi": mop_psi,
            "mop_active": mop_active,
            "shut_in_location": self.load.shut_in_location,
        }

    def run_all_conditions(self) -> Dict[str, Any]:
        """
        Analyze all six life cycle conditions (3 stages × 2 positions):

        1. Installation Top: Empty pipe, atmospheric Po, max tension
        2. Installation Bottom: Empty pipe, full hydrostatic Po, zero tension
        3. Hydrotest Top: 1.25× design Pi, atmospheric Po, max tension
        4. Hydrotest Bottom: 1.25× design Pi, full hydrostatic Po, zero tension
        5. Operation Top: Design/shut-in Pi, atmospheric Po, max tension
        6. Operation Bottom: Design/shut-in Pi, full hydrostatic Po, zero tension

        Critical Changes from Previous Implementation:
        - External pressure varies by position (14.7 vs 14.7+hydrostatic)
        - Internal pressure varies by check type in Operation condition
        - Axial tension varies by position (full vs zero)

        Returns:
        --------
        Dict with keys:
        - pipe: Pipe properties
        - loading: Loading conditions
        - conditions: Dict with 6 condition results (keys: "installation_top", etc.)
        - all_conditions_pass: Boolean (True if all 6 pass)
        """
        # Define all 6 conditions to analyze
        # Format: (condition_name, position, use_mill_tolerance, use_corrosion)
        conditions_to_analyze = [
            # Installation: Empty pipe, mill tolerance only
            ("Installation", "Top", True, False),
            ("Installation", "Bottom", True, False),

            # Hydrotest: Elevated pressure, mill tolerance only
            ("Hydrotest", "Top", True, False),
            ("Hydrotest", "Bottom", True, False),

            # Operation: Design/shut-in pressure, mill tolerance + corrosion
            ("Operation", "Top", True, True),
            ("Operation", "Bottom", True, True),
        ]

        results = {}

        for condition_name, position, use_mill, use_corr in conditions_to_analyze:
            # Create condition key: "installation_top", "hydrotest_bottom", etc.
            condition_key = f"{condition_name.lower()}_{position.lower()}"

            # Analyze this condition at this position
            result = self.analyze_condition_at_position(
                condition_name=condition_name,
                position=position,
                use_mill_tolerance=use_mill,
                use_corrosion=use_corr
            )

            results[condition_key] = result

        # Check if ALL 6 conditions pass
        all_conditions_pass = all(r["all_pass"] for r in results.values())

        return {
            "pipe": asdict(self.pipe),
            "loading": asdict(self.load),
            "conditions": results,  # Now has 6 entries instead of 3
            "all_conditions_pass": all_conditions_pass,
        }


def evaluate_standard_thicknesses(base_pipe: PipeProperties, load: LoadingCondition) -> pd.DataFrame:
    """Evaluate all standard thicknesses per ASME B36.10"""
    thicknesses = asme_b36_10.get_standard_thicknesses(base_pipe.od_in)
    if not thicknesses:
        return pd.DataFrame()

    records: List[Dict[str, Any]] = []
    for wt in thicknesses:
        pipe_variant = PipeProperties(**{**asdict(base_pipe), "wt_in": wt})
        analyzer = LifeCycleAnalyzer(pipe_variant, load)
        result = analyzer.run_all_conditions()
        
        # Find worst safety factor across ALL 6 conditions and checks
        min_sf = float("inf")
        limiting_condition = ""
        limiting_check = ""

        for cond_key, cond_result in result["conditions"].items():
            # cond_key is now: "installation_top", "hydrotest_bottom", etc.
            if cond_result["limiting"]["safety_factor"] < min_sf:
                min_sf = cond_result["limiting"]["safety_factor"]

                # Create display name: "Installation - Top"
                stage = cond_result["condition_name"]
                position = cond_result["position"]
                limiting_condition = f"{stage} - {position}"
                limiting_check = cond_result["limiting"]["name"]

        records.append({
            "WT (in)": wt,
            "Schedule": schedule_name_for_thickness(base_pipe.od_in, wt),
            "Limiting Condition": limiting_condition,
            "Limiting Check": limiting_check,
            "Safety Factor": format_safety_factor(min_sf),
            "Utilization (%)": 0 if min_sf == float("inf") else round(100 / min_sf, 1),
            "Status": "PASS" if result["all_conditions_pass"] else "FAIL",
        })

    return pd.DataFrame(records)


def find_closest_passing_standard_wt(base_pipe: PipeProperties, load: LoadingCondition, 
                                      input_wt: float) -> Tuple[float, str]:
    """
    Find closest standard thickness >= input_wt that passes all conditions.
    Uses floor-to-up approach (round up from input).
    """
    thicknesses = asme_b36_10.get_standard_thicknesses(base_pipe.od_in)
    if not thicknesses:
        return None, "No standard thicknesses available"
    
    # Filter thicknesses >= input_wt
    candidates = [wt for wt in thicknesses if wt >= input_wt]
    if not candidates:
        return None, "No standard thickness >= input thickness"
    
    # Test each candidate starting from smallest
    for wt in sorted(candidates):
        pipe_variant = PipeProperties(**{**asdict(base_pipe), "wt_in": wt})
        analyzer = LifeCycleAnalyzer(pipe_variant, load)
        result = analyzer.run_all_conditions()
        
        if result["all_conditions_pass"]:
            schedule = schedule_name_for_thickness(base_pipe.od_in, wt)
            return wt, schedule
    
    return None, "No passing standard thickness found"


# -----------------------------------------------------------------------------
# UI helpers
# -----------------------------------------------------------------------------

def badge(label: str, color: str) -> str:
    return f"<span style='background:{color}; color:#ffffff; padding:4px 10px; border-radius:999px; font-weight:700;'>{label}</span>"


def render_styles():
    style = f"""
<style>
:root {{
    --primary: {COLOR_PRIMARY};
    --secondary: {COLOR_SECONDARY};
    --success: {COLOR_SUCCESS};
    --alert: {COLOR_ALERT};
}}
[data-testid="stAppViewContainer"] {{
    background: radial-gradient(circle at 10% 20%, rgba(30,58,138,0.15), rgba(59,130,246,0)) ,
                linear-gradient(135deg, {COLOR_PRIMARY} 0%, {COLOR_SECONDARY} 35%, #0f172a 100%);
}}
.main-header {{
    font-size: 2.4rem;
    font-weight: 800;
    color: #ffffff;
    text-align: left;
    padding: 0.4rem 0 0.4rem 0;
}}
.headline-card {{
    background: #0b1224cc;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 1.2rem;
    box-shadow: 0 20px 45px rgba(0,0,0,0.35);
    color: #e2e8f0;
}}
.section-card {{
    background: #ffffff;
    border-radius: 14px;
    padding: 1rem 1rem 0.5rem 1rem;
    box-shadow: 0 15px 35px rgba(0,0,0,0.08);
    border: 1px solid rgba(15,23,42,0.06);
}}
.metric-chip {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 12px;
    font-weight: 700;
    color: #0f172a;
    background: linear-gradient(120deg, rgba(59,130,246,0.12), rgba(30,58,138,0.1));
}}
.status-pass {{ color: {COLOR_SUCCESS}; font-weight: 700; }}
.status-fail {{ color: {COLOR_ALERT}; font-weight: 700; }}
.badge-pill {{
    padding: 6px 12px;
    border-radius: 999px;
    font-weight: 700;
    color: #fff;
    display: inline-block;
}}
.subdued {{ color: #cbd5e1; font-size: 0.9rem; }}
.stTabs [data-baseweb="tab-list"] button {{
    gap: 8px;
    padding: 10px 16px;
    border-radius: 10px 10px 0 0;
    font-weight: 700;
}}
.stTabs [data-baseweb="tab"]:hover {{
    background: rgba(59,130,246,0.08);
}}
@media (max-width: 768px) {{
    .main-header {{
        font-size: 1.6rem;
        text-align: center;
    }}
    .headline-card {{
        padding: 1rem;
    }}
    .metric-chip {{
        width: 100%;
        justify-content: center;
    }}
}}
</style>
"""
    st.markdown(style, unsafe_allow_html=True)


def status_pill(text: str, positive: bool) -> str:
    color = COLOR_SUCCESS if positive else COLOR_ALERT
    return f"<span class='badge-pill' style='background:{color};'>{text}</span>"


def info_chip(label: str, value: str) -> str:
    return f"<span class='metric-chip'>{label}: {value}</span>"


def render_hero():
    st.markdown(
        """
        <div class='headline-card'>
            <div class='main-header'>Riser Design Analysis Tool</div>
            <div class='subdued'>API RP 1111 burst/collapse/propagation + ASME B31.4/B31.8 hoop checks</div>
            <div class='subdued' style='margin-top:8px;'>Three life cycle conditions: Installation, Hydrotest, Operation</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def initialize_state():
    """Initialize session state with Multiphase Riser defaults"""
    defaults = TEAM8_REFERENCE["Multiphase Riser (ID 3)"]
    for key, value in {
        "od_in": defaults["od"],
        "wt_in": defaults["wt"],
        "design_pressure": defaults["design_pressure"],
        "shut_in_pressure": defaults["shut_in_pressure"],
        "shut_in_location": defaults["shut_in_location"],
        "water_depth": defaults["water_depth"],
        "riser_length": defaults["water_depth"],  # Initialize with water depth
        "fluid_sg": defaults["fluid_sg"],
        "grade": defaults["grade"],
        "manufacturing": defaults["manufacturing"],
        "fluid_type": defaults["fluid_type"],
        "design_category": defaults["design_category"],
        "ovality_type": defaults["ovality_type"],
        "ovality": defaults["ovality"],
    }.items():
        st.session_state.setdefault(key, value)


def apply_reference(name: str):
    """Load Team 8 reference data into form"""
    ref = TEAM8_REFERENCE[name]
    st.session_state.od_in = ref["od"]
    st.session_state.wt_in = ref["wt"]
    st.session_state.design_pressure = ref["design_pressure"]
    st.session_state.shut_in_pressure = ref["shut_in_pressure"]
    st.session_state.shut_in_location = ref["shut_in_location"]
    st.session_state.water_depth = ref["water_depth"]
    st.session_state.riser_length = ref["water_depth"]  # Default to water depth
    st.session_state.fluid_sg = ref["fluid_sg"]
    st.session_state.grade = ref["grade"]
    st.session_state.manufacturing = ref["manufacturing"]
    st.session_state.fluid_type = ref["fluid_type"]
    st.session_state.design_category = ref["design_category"]
    st.session_state.ovality_type = ref["ovality_type"]
    st.session_state.ovality = ref["ovality"]
    st.success(f"Loaded {name} data. You can modify any values.")


def build_pipe_and_load() -> Tuple[PipeProperties, LoadingCondition]:
    """Build pipe and loading objects from session state"""
    grade_props = GRADE_PROPERTIES.get(st.session_state.grade, GRADE_PROPERTIES["X-52"])
    
    # Get ovality based on type
    if st.session_state.ovality_type == "Reel-lay":
        ovality_value = 0.01  # 1%
    else:  # Other Type
        ovality_value = 0.005  # 0.5%
    
    pipe = PipeProperties(
        od_in=st.session_state.od_in,
        wt_in=st.session_state.wt_in,
        grade=st.session_state.grade,
        manufacturing=st.session_state.manufacturing,
        design_category=st.session_state.design_category,
        fluid_type=st.session_state.fluid_type,
        fluid_sg=st.session_state.fluid_sg,
        smys_psi=grade_props["smys_psi"],
        uts_psi=grade_props["uts_psi"],
        ovality_type=st.session_state.ovality_type,
        ovality=ovality_value,
    )
    load = LoadingCondition(
        design_pressure_psi=st.session_state.design_pressure,
        shut_in_pressure_psi=st.session_state.shut_in_pressure,
        shut_in_location=st.session_state.get("shut_in_location", "Subsea Wellhead"),
        water_depth_m=st.session_state.water_depth,
        riser_length_m=st.session_state.get("riser_length", st.session_state.water_depth),
    )
    return pipe, load


def render_input_sections():
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.subheader("Design Inputs")
    st.caption("Enter all values manually. Team 8 reference buttons pre-fill the form for convenience.")

    tabs = st.tabs(["Pipe Properties", "Pressures & Loading", "Environment"])

    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.od_in = st.number_input("Outer Diameter (in)", min_value=2.0, max_value=48.0, value=st.session_state.od_in, step=0.01, format="%.3f")
            st.session_state.wt_in = st.number_input("Wall Thickness (in)", min_value=0.1, max_value=3.0, value=st.session_state.wt_in, step=0.01, format="%.4f")
            st.caption(f"Mill tolerance: {MILL_TOLERANCE*100}% | Corrosion: {CORROSION_RATE_PER_YEAR*DESIGN_LIFE_YEARS:.3f}\" over {DESIGN_LIFE_YEARS} years")
        with col2:
            st.session_state.grade = st.selectbox("Pipe Grade", list(GRADE_PROPERTIES.keys()), index=list(GRADE_PROPERTIES.keys()).index(st.session_state.grade))
            st.session_state.manufacturing = st.selectbox("Manufacturing Type", ["SMLS", "ERW", "DSAW"], index=["SMLS", "ERW", "DSAW"].index(st.session_state.manufacturing))
            st.session_state.design_category = st.selectbox("Design Category", ["Riser", "Pipeline"], index=["Riser", "Pipeline"].index(st.session_state.design_category))
        with col3:
            st.session_state.fluid_type = st.selectbox("Fluid Type", ["Gas", "Oil", "Multiphase", "Wet Gas"], index=["Gas", "Oil", "Multiphase", "Wet Gas"].index(st.session_state.fluid_type))
            st.session_state.fluid_sg = st.number_input("Fluid Specific Gravity", min_value=0.02, max_value=1.50, value=st.session_state.fluid_sg, step=0.01)
            st.session_state.ovality_type = st.selectbox("Ovality Type", ["Other Type", "Reel-lay"], index=["Other Type", "Reel-lay"].index(st.session_state.ovality_type))
            st.caption("Ovality: 0.5% (Other Type) or 1.0% (Reel-lay) per API RP 1111")

    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.design_pressure = st.number_input("Design Pressure (psi)", min_value=0.0, max_value=20000.0, value=st.session_state.design_pressure, step=10.0)
            st.session_state.shut_in_pressure = st.number_input("Shut-in Pressure (psi)", min_value=0.0, max_value=20000.0, value=st.session_state.shut_in_pressure, step=10.0)
        with col2:
            st.session_state.shut_in_location = st.selectbox(
                "Shut-in Location",
                ["Subsea Wellhead", "Top of Riser"],
                index=["Subsea Wellhead", "Top of Riser"].index(st.session_state.get("shut_in_location", "Subsea Wellhead")),
                help="Location where shut-in pressure is measured. Affects MOP calculation."
            )
            st.caption("**MOP (Maximum Operating Pressure)** is calculated when shut-in is at Subsea Wellhead:\nMOP = Shut-in Pressure - Hydrostatic Head of Riser Contents")

    with tabs[2]:
        st.session_state.water_depth = st.number_input("💧 Water Depth (m)", min_value=0.0, max_value=4000.0, value=st.session_state.water_depth, step=10.0, help="Kedalam Laut / Depth for external pressure calculation")
        st.session_state.riser_length = st.number_input("📏 Riser Length (m)", min_value=0.0, max_value=4000.0, value=st.session_state.get("riser_length", st.session_state.water_depth), step=10.0, help="Vertical riser length for longitudinal tension calculation (typically equals water depth)")
        st.caption(f"External pressure: {DEFAULT_WATER_DENSITY} lb/ft³ seawater density × depth × 3.28084 ft/m / 144")
        st.caption("Note: Riser length affects applied tension T_a = void_submerged_weight × length")

    st.markdown("</div>", unsafe_allow_html=True)


def render_reference_section():
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    with st.expander("Team 8 Reference Data (Auto-Load)", expanded=False):
        st.write("Click a button to automatically load Team 8 data into the form. Modify values after loading if needed.")
        cols = st.columns(2)
        if cols[0].button("🔄 Load Multiphase Riser (ID 3)", use_container_width=True):
            apply_reference("Multiphase Riser (ID 3)")
            st.rerun()
        if cols[1].button("🔄 Load Oil Riser (ID 8)", use_container_width=True):
            apply_reference("Oil Riser (ID 8)")
            st.rerun()
        
        st.markdown("**Reference Values:**")
        df_ref = pd.DataFrame({
            "Parameter": ["OD (in)", "WT (in)", "Grade", "Design P (psi)", "Shut-in P (psi)", "Depth (m)", "Fluid Type", "SG"],
            "Gas Riser (ID 3)": [16.0, 0.750, "X-52", 1400, 1236, 920, "Multiphase", 0.57],
            "Oil Riser (ID 8)": [8.63, 0.500, "X-52", 230, 195, 960, "Oil", 0.82],
        })
        st.dataframe(df_ref, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def build_verification_notes(pipe: PipeProperties, load: LoadingCondition, result: Dict[str, Any]) -> List[str]:
    """Build automated verification warnings"""
    notes: List[str] = []
    d_over_t = pipe.od_in / max(pipe.wt_in, 1e-6)

    # Check operation condition WT (use operation_top as representative)
    op_wt = result["conditions"]["operation_top"]["wt_effective"]
    if op_wt < 0.1:
        notes.append(f"⚠️ Operation WT very thin ({op_wt:.4f} in) after corrosion and mill tolerance")

    if d_over_t > 120:
        notes.append(f"⚠️ High D/t ratio ({d_over_t:.1f}); check fabrication tolerances")

    if load.shut_in_pressure_psi > load.design_pressure_psi * 1.5:
        notes.append("⚠️ Shut-in pressure > 1.5× design; confirm well control assumptions")

    if pipe.fluid_sg < 0.02 or pipe.fluid_sg > 1.2:
        notes.append(f"⚠️ Fluid SG ({pipe.fluid_sg}) outside typical range")

    # Check if any condition fails
    for cond_name, cond in result["conditions"].items():
        if not cond["all_pass"]:
            # Format condition name nicely (e.g., "operation_top" -> "Operation Top")
            formatted_name = cond_name.replace("_", " ").title()
            notes.append(f"❌ {formatted_name} condition fails")

    return notes


def format_safety_factor(sf: float, check_name: str = "", p_internal: float = 0.0) -> str:
    """
    Format safety factor for display with descriptive text for infinite values

    Parameters:
    -----------
    sf : float
        Safety factor value
    check_name : str
        Name of check (for context)
    p_internal : float
        Internal pressure (for determining N/A reason)

    Returns:
    --------
    str : Formatted safety factor text

    Replaces float('inf') with user-friendly descriptions:
    - "N/A (No internal pressure)" for burst/hoop during installation
    - "N/A (Favorable loading)" for reverse loading cases
    - ">999" for extremely high safety factors
    """
    if sf == float('inf'):
        # Determine reason for infinite safety factor
        if p_internal <= 0 and check_name in ["Burst", "Hoop Stress"]:
            return "N/A (No internal pressure)"
        else:
            return "N/A (Favorable loading)"
    elif sf > 999:
        return ">999"
    else:
        return f"{sf:.2f}"


def render_position_results(position_name: str, cond_result: Dict[str, Any]):
    """
    Render results for one position (Top or Bottom) within a lifecycle condition

    Displays:
    - Position-specific external pressure
    - Check-specific internal pressures (Operation shows both design and shut-in)
    - All 7 checks with formatted safety factors
    - Detailed expandable sections

    Parameters:
    -----------
    position_name : str
        "Top" or "Bottom"
    cond_result : Dict
        Result dictionary from analyze_condition_at_position()
    """
    st.markdown(f"#### {position_name} Position")

    # Status badge
    status_html = status_pill("PASS" if cond_result["all_pass"] else "FAIL", cond_result["all_pass"])
    st.markdown(f"**Status:** {status_html}", unsafe_allow_html=True)

    # Pressure summary card
    st.markdown("**Pressures:**")

    condition_name = cond_result['condition_name']

    if condition_name == "Operation":
        # Operation uses different Pi for different checks - show design, shut-in, and MOP
        # Check if MOP is being used (collapse pressure differs from shut-in)
        shut_in_used = cond_result.get('p_internal_collapse', 0)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("External (Po)", f"{cond_result['p_external_psi']:.0f} psi")
        with col2:
            st.metric("Design Pressure", f"{cond_result['p_internal_burst']:.0f} psi")
            st.caption("For: Burst, Hoop, Longitudinal, Combined")
        with col3:
            st.metric("Shut-in/MOP", f"{shut_in_used:.0f} psi")
            st.caption("For: Collapse, Propagation")
        with col4:
            # Show MOP indicator if applicable
            if cond_result.get('mop_active', False):
                st.metric("MOP Active", "✓ Yes")
                st.caption(f"MOP = {cond_result['mop_psi']:.0f} psi")
                st.caption("(Shut-in at Subsea Wellhead)")
            else:
                st.metric("MOP Active", "✗ No")
                if cond_result.get('shut_in_location') == "Top of Riser":
                    st.caption("Shut-in at Top")
                elif position_name == "Bottom":
                    st.caption("Bottom position uses full shut-in")
                else:
                    st.caption("Using shut-in pressure")
    else:
        # Installation and Hydrotest use same Pi for all checks
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Internal (Pi)", f"{cond_result['p_internal_burst']:.0f} psi")
        with col2:
            st.metric("External (Po)", f"{cond_result['p_external_psi']:.0f} psi")
        with col3:
            p_diff = cond_result['p_internal_burst'] - cond_result['p_external_psi']
            st.metric("Differential (Pi-Po)", f"{p_diff:+.0f} psi")

    # Wall thickness
    col1, col2 = st.columns(2)
    col1.metric("Nominal WT", f"{cond_result['wt_nominal']:.4f} in")
    col2.metric("Effective WT", f"{cond_result['wt_effective']:.4f} in")

    # Pipe weights
    st.markdown("**Pipe Weights:**")
    weights = cond_result["weights"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Empty Pipe:**")
        st.write(f"Dry: {weights['void_dry_weight_plf']:.2f} lb/ft")
        st.write(f"Submerged: {weights['void_submerged_weight_plf']:.2f} lb/ft")
    with col2:
        st.markdown("**Flooded (Water):**")
        st.write(f"Dry: {weights['flooded_dry_weight_plf']:.2f} lb/ft")
        st.write(f"Submerged: {weights['flooded_submerged_weight_plf']:.2f} lb/ft")
    with col3:
        st.markdown("**Product-Filled:**")
        st.write(f"Dry: {weights['product_filled_dry_weight_plf']:.2f} lb/ft")
        st.write(f"Submerged: {weights['product_filled_submerged_weight_plf']:.2f} lb/ft")

    # Checks table with formatted safety factors
    st.markdown("**Analysis Results:**")
    table_records = []
    for chk in cond_result["checks"]:
        sf_formatted = format_safety_factor(
            chk["safety_factor"],
            chk["name"],
            cond_result.get('p_internal_burst', 0)
        )
        util_pct = 0 if chk["safety_factor"] == float("inf") else round(100 / chk["safety_factor"], 1)
        table_records.append({
            "Check": chk["name"],
            "Safety Factor": sf_formatted,
            "Utilization (%)": util_pct,
            "Status": "PASS" if chk["pass_fail"] else "FAIL",
        })

    # Add longitudinal tension
    long_check = cond_result["longitudinal"]
    sf_formatted = format_safety_factor(long_check["safety_factor"], "Longitudinal")
    long_util = 0 if long_check["safety_factor"] == float("inf") else round(100 / long_check["safety_factor"], 1)
    table_records.append({
        "Check": "Longitudinal Tension",
        "Safety Factor": sf_formatted,
        "Utilization (%)": long_util,
        "Status": long_check["status"],
    })

    # Add combined loading
    comb_check = cond_result["combined"]
    sf_formatted = format_safety_factor(comb_check["safety_factor"], "Combined")
    comb_util = 0 if comb_check["safety_factor"] == float("inf") else round(100 / comb_check["safety_factor"], 1)
    table_records.append({
        "Check": "Combined Loading",
        "Safety Factor": sf_formatted,
        "Utilization (%)": comb_util,
        "Status": comb_check["status"],
    })

    df = pd.DataFrame(table_records)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Limiting check
    limiting_sf_text = format_safety_factor(cond_result['limiting']['safety_factor'])
    st.info(f"**Limiting Check:** {cond_result['limiting']['name']} with SF = {limiting_sf_text}")

    # Detailed expandable sections
    with st.expander("📊 Longitudinal Tension Details"):
        long = long_check
        st.markdown(f"""
        **Position:** {cond_result['position']}
        **Applied Tension (T_a):** {long['t_a_applied_kips']:.2f} kips
        *{"Full riser weight (submerged)" if position_name == "Top" else "Zero (supported by mudline)"}*

        **Effective Tension (T_eff):** {long['t_eff_effective_kips']:.2f} kips
        **Allowable (0.60 × T_y):** {long['allowable_tension_kips']:.2f} kips

        **Safety Factor:** {format_safety_factor(long['safety_factor'])}
        **Status:** {long['status']}

        **Note:** Buoyancy is accounted for in submerged weight calculation.
        """)

    with st.expander("🔄 Combined Loading Details"):
        comb = comb_check
        st.markdown(f"""
        **Position:** {cond_result['position']}
        **Combined Ratio:** {comb['combined_ratio']:.4f}
        **Design Factor:** {comb['design_factor']} ({comb['factor_description']})

        **Pressure Component:** {comb['pressure_component']:.4f}
        **Tension Component:** {comb['tension_component']:.4f}

        **Safety Factor:** {format_safety_factor(comb['safety_factor'])}
        **Status:** {"PASS" if comb['passes'] else "FAIL"}
        """)


def render_condition_results(cond_name: str, cond_result: Dict[str, Any]):
    """Render one life cycle condition results"""
    st.markdown(f"### {cond_name.capitalize()} Condition")
    
    status_html = status_pill("PASS" if cond_result["all_pass"] else "FAIL", cond_result["all_pass"])
    st.markdown(f"Status: {status_html}", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Nominal WT", f"{cond_result['wt_nominal']:.4f} in")
    col2.metric("Effective WT", f"{cond_result['wt_effective']:.4f} in")
    col3.metric("Pi", f"{cond_result['p_internal_psi']:.0f} psi")
    col4.metric("Po", f"{cond_result['p_external_psi']:.0f} psi")
    
    # Display pipe weights
    st.markdown("#### Pipe Weights")
    weights = cond_result["weights"]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Empty Pipe:**")
        st.write(f"Dry: {weights['void_dry_weight_plf']:.2f} lb/ft")
        st.write(f"Submerged: {weights['void_submerged_weight_plf']:.2f} lb/ft")
    with col2:
        st.markdown("**Flooded (Water):**")
        st.write(f"Dry: {weights['flooded_dry_weight_plf']:.2f} lb/ft")
        st.write(f"Submerged: {weights['flooded_submerged_weight_plf']:.2f} lb/ft")
    with col3:
        st.markdown("**Product-Filled:**")
        st.write(f"Dry: {weights['product_filled_dry_weight_plf']:.2f} lb/ft")
        st.write(f"Submerged: {weights['product_filled_submerged_weight_plf']:.2f} lb/ft")
    
    st.caption(f"Pipe Specific Gravity: {weights['pipe_specific_gravity']:.2f} | Steel: {weights['steel_density_pcf']:.0f} pcf | Water: {weights['water_density_pcf']:.0f} pcf")
    
    # Adjustments applied
    adjustments = []
    if cond_result["mill_tolerance_applied"]:
        adjustments.append("Mill Tolerance (×0.875)")
    if cond_result["corrosion_applied"]:
        adjustments.append(f"Corrosion ({CORROSION_RATE_PER_YEAR*DESIGN_LIFE_YEARS:.3f} in)")
    st.caption("Applied: " + ", ".join(adjustments) if adjustments else "Applied: None (nominal WT)")
    
    # Checks table
    table_records = []
    for chk in cond_result["checks"]:
        util_pct = 0 if chk["safety_factor"] == float("inf") else round(100 / chk["safety_factor"], 1)
        table_records.append({
            "Check": chk["name"],
            "Safety Factor": f"{chk['safety_factor']:.2f}" if chk["safety_factor"] != float("inf") else "∞",
            "Utilization (%)": util_pct,
            "Status": "PASS" if chk["pass_fail"] else "FAIL",
        })
    
    # Add longitudinal tension check
    long_check = cond_result["longitudinal"]
    long_util = 0 if long_check["safety_factor"] == float("inf") else round(100 / long_check["safety_factor"], 1)
    table_records.append({
        "Check": "Longitudinal Tension",
        "Safety Factor": f"{long_check['safety_factor']:.2f}" if long_check["safety_factor"] != float("inf") else "∞",
        "Utilization (%)": long_util,
        "Status": long_check["status"],
    })
    
    # Add combined loading check
    comb_check = cond_result["combined"]
    comb_util = 0 if comb_check["safety_factor"] == float("inf") else round(100 / comb_check["safety_factor"], 1)
    table_records.append({
        "Check": "Combined Loading",
        "Safety Factor": f"{comb_check['safety_factor']:.2f}" if comb_check["safety_factor"] != float("inf") else "∞",
        "Utilization (%)": comb_util,
        "Status": comb_check["status"],
    })
    
    df = pd.DataFrame(table_records)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Detailed information for new checks
    with st.expander("📊 Longitudinal Tension Details (API RP 1111 Section 4.3.1.1)"):
        st.markdown(f"""
        **Applied Tension (T_a):** {long_check['t_a_applied_kips']:.2f} kips ({long_check['t_a_applied_lb']:.0f} lb)  
        *From self-weight: {long_check['void_submerged_plf']:.2f} lb/ft × {long_check['riser_length_ft']:.0f} ft*
        
        **Pressure End-Cap Forces:**
        - Internal (P_i × A_i): {long_check['force_internal_lb']/1000:.2f} kips (reduces tension)
        - External (P_o × A_o): {long_check['force_external_lb']/1000:.2f} kips (increases tension)
        
        **Effective Tension (T_eff):** {long_check['t_eff_effective_kips']:.2f} kips  
        *T_eff = T_a - P_i×A_i + P_o×A_o*
        
        **Yield Tension (T_y):** {long_check['t_y_yield_kips']:.2f} kips  
        *T_y = SMYS × A_steel = {cond_result["checks"][0].get("smys", "N/A")} psi × {long_check['a_steel_in2']:.2f} in²*
        
        **Allowable (0.60 × T_y):** {long_check['allowable_tension_kips']:.2f} kips
        
        **Axial Stress:** {long_check['axial_stress_ksi']:.2f} ksi  
        **Criterion:** T_eff ≤ 0.60 × T_y (per API RP 1111 Section 4.3.1.1)
        """)
    
    with st.expander("🔄 Combined Loading Details (API RP 1111 Section 4.3.1.2)"):
        st.markdown(f"""
        **Formula:** √[(P/P_b)² + (T/T_y)²] ≤ Design Factor
        
        **Pressure Component (P/P_b):** {comb_check['pressure_component']:.4f}  
        *P_i - P_o = {comb_check['p_diff_psi']:.0f} psi, P_b = {comb_check['p_b_burst_psi']:.0f} psi*
        
        **Tension Component (T/T_y):** {comb_check['tension_component']:.4f}  
        *T_eff = {comb_check['t_eff_lb']/1000:.2f} kips, T_y = {comb_check['t_y_lb']/1000:.2f} kips*
        
        **Combined Ratio:** {comb_check['combined_ratio']:.4f}  
        **Design Factor:** {comb_check['design_factor']} ({comb_check['factor_description']})
        
        **Status:** Combined Ratio {'≤' if comb_check['passes'] else '>'} Design Factor
        """)
    
    # Limiting check
    st.info(f"Limiting: **{cond_result['limiting']['name']}** with SF = {cond_result['limiting']['safety_factor']:.2f}")


def render_results(result: Dict[str, Any], pipe: PipeProperties, load: LoadingCondition):
    """Render complete results with all six life cycle conditions (3 stages × 2 positions)"""
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)

    tabs = st.tabs(["Summary", "Installation", "Hydrotest", "Operation", "Standard Thicknesses", "Verification"])

    with tabs[0]:
        st.subheader("Life Cycle Analysis Summary")

        all_pass = result["all_conditions_pass"]
        status_html = status_pill("ALL 6 CONDITIONS PASS" if all_pass else "SOME CONDITIONS FAIL", all_pass)
        st.markdown(f"Overall: {status_html}", unsafe_allow_html=True)

        st.markdown("---")

        # Summary table - now with 6 rows
        summary_records = []
        condition_order = [
            "installation_top", "installation_bottom",
            "hydrotest_top", "hydrotest_bottom",
            "operation_top", "operation_bottom"
        ]

        for cond_key in condition_order:
            cond = result["conditions"][cond_key]

            # Create display name: "Installation - Top"
            stage = cond["condition_name"]
            position = cond["position"]
            display_name = f"{stage} - {position}"

            summary_records.append({
                "Condition": display_name,
                "Effective WT (in)": f"{cond['wt_effective']:.4f}",
                "Po (psi)": f"{cond['p_external_psi']:.0f}",
                "Pi Burst (psi)": f"{cond['p_internal_burst']:.0f}",
                "Pi Collapse (psi)": f"{cond['p_internal_collapse']:.0f}",
                "Limiting Check": cond["limiting"]["name"],
                "Min SF": format_safety_factor(cond["limiting"]["safety_factor"]),
                "Status": "PASS" if cond["all_pass"] else "FAIL",
            })

        df_summary = pd.DataFrame(summary_records)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

        if all_pass:
            st.success("✅ The selected wall thickness satisfies all design criteria for all 6 conditions (3 stages × 2 positions).")
        else:
            st.error("❌ Wall thickness does NOT meet all criteria. Review failed conditions and consider increasing thickness.")

    with tabs[1]:
        st.markdown("### Installation Condition")
        st.info("Installation: Empty pipe (Pi=0), external pressure + bending during lay. Uses mill tolerance only.")

        position_tabs = st.tabs(["Top Position", "Bottom Position"])

        with position_tabs[0]:
            render_position_results("Top", result["conditions"]["installation_top"])
            st.caption("Top of riser: Atmospheric pressure only (14.7 psi), maximum longitudinal tension from full riser weight.")

        with position_tabs[1]:
            render_position_results("Bottom", result["conditions"]["installation_bottom"])
            st.caption("Bottom of riser: Full hydrostatic external pressure, zero longitudinal tension (supported by mudline).")

    with tabs[2]:
        st.markdown("### Hydrotest Condition")
        st.info(f"Hydrotest: Internal pressure = {HYDROTEST_FACTOR}× design pressure. Uses mill tolerance only.")

        position_tabs = st.tabs(["Top Position", "Bottom Position"])

        with position_tabs[0]:
            render_position_results("Top", result["conditions"]["hydrotest_top"])
            st.caption("Top: High internal pressure with atmospheric external, maximum tension.")

        with position_tabs[1]:
            render_position_results("Bottom", result["conditions"]["hydrotest_bottom"])
            st.caption("Bottom: High internal pressure with full hydrostatic external, zero tension.")

    with tabs[3]:
        st.markdown("### Operation Condition")

        # Get MOP info from operation_top result
        op_top = result["conditions"]["operation_top"]
        shut_in_loc = op_top.get("shut_in_location", "Subsea Wellhead")
        mop_value = op_top.get("mop_psi", 0)

        # Display MOP information box
        if shut_in_loc == "Subsea Wellhead":
            st.info(f"""
            **Operation Pressure Strategy with MOP:**
            - **Design pressure** used for: Burst, Hoop, Longitudinal, Combined
            - **Shut-in/MOP** used for: Collapse, Propagation
            - **MOP (Maximum Operating Pressure)** = {mop_value:.0f} psi
            - MOP applies at **Top** position when shut-in location is at **Subsea Wellhead**
            - Includes {DESIGN_LIFE_YEARS}-year corrosion ({CORROSION_RATE_PER_YEAR*DESIGN_LIFE_YEARS:.3f} in)

            **MOP Calculation:** Shut-in Pressure - Hydrostatic Head of Riser Contents
            """)
        else:
            st.info(f"Operation: Uses design pressure for burst/hoop/longitudinal/combined, shut-in for collapse. Includes {DESIGN_LIFE_YEARS}-year corrosion ({CORROSION_RATE_PER_YEAR*DESIGN_LIFE_YEARS:.3f} in).")

        position_tabs = st.tabs(["Top Position", "Bottom Position"])

        with position_tabs[0]:
            render_position_results("Top", result["conditions"]["operation_top"])
            if shut_in_loc == "Subsea Wellhead":
                st.caption("Top: Design pressure for burst/hoop/longitudinal/combined, **MOP** for collapse/propagation. Atmospheric external, full weight tension.")
            else:
                st.caption("Top: Design/shut-in pressures with atmospheric external, full weight tension. Design pressure for burst/hoop, shut-in for collapse.")

        with position_tabs[1]:
            render_position_results("Bottom", result["conditions"]["operation_bottom"])
            st.caption("Bottom: Design pressure for burst/hoop/longitudinal/combined, **full shut-in** for collapse/propagation. Full hydrostatic external, zero tension.")

    with tabs[4]:
        st.subheader("Standard Thickness Evaluation (ASME B36.10)")
        df_std = evaluate_standard_thicknesses(pipe, load)
        if df_std.empty:
            st.warning("No standard thicknesses found for this OD.")
        else:
            st.dataframe(df_std, use_container_width=True, hide_index=True)
            passing = df_std[df_std["Status"] == "PASS"]
            if not passing.empty:
                first_pass = passing.iloc[0]
                st.success(
                    f"✅ Least passing thickness: **{first_pass['WT (in)']:.4f} in** (Schedule: {first_pass['Schedule']})"
                )
                st.info(
                    f"Limiting: {first_pass['Limiting Condition']} - {first_pass['Limiting Check']} with SF {first_pass['Safety Factor']}"
                )
                
                # Find closest standard >= input WT
                closest_wt, closest_sch = find_closest_passing_standard_wt(pipe, load, pipe.wt_in)
                if closest_wt:
                    if closest_wt == pipe.wt_in:
                        st.success(f"✅ Input WT ({pipe.wt_in:.4f} in) matches standard thickness (Sch. {closest_sch}) and passes all conditions.")
                    else:
                        st.info(f"📊 Closest standard thickness ≥ input ({pipe.wt_in:.4f} in): **{closest_wt:.4f} in** (Sch. {closest_sch})")
                else:
                    st.warning(f"⚠️ {closest_sch}")
            else:
                st.error("❌ No standard thickness meets all criteria. Consider:")
                st.markdown("- Increasing pipe grade (X-60, X-65)")
                st.markdown("- Reducing design/shut-in pressures")
                st.markdown("- Decreasing water depth")
                st.markdown("- Using custom (non-standard) wall thickness")

    with tabs[5]:
        st.subheader("Input Verification")
        notes = build_verification_notes(pipe, load, result)
        if notes:
            for note in notes:
                st.warning(note)
        else:
            st.success("✅ All inputs within typical design ranges. No flags detected.")
        
        with st.expander("Detailed Input Summary", expanded=False):
            st.json({"pipe": result["pipe"], "loading": result["loading"]}, expanded=False)

    st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Streamlit app
# -----------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Riser Design Analysis", layout="wide")
    render_styles()
    render_hero()
    initialize_state()

    render_input_sections()
    render_reference_section()

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    if st.button("🔍 Calculate All Life Cycle Conditions", type="primary", use_container_width=True):
        pipe, load = build_pipe_and_load()
        analyzer = LifeCycleAnalyzer(pipe, load)
        result = analyzer.run_all_conditions()

        render_results(result, pipe, load)
    else:
        st.info("📝 Enter all design parameters manually, then click Calculate. Use Team 8 auto-load buttons for quick reference data entry.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.caption(
        f"API RP 1111 (3rd Ed 1999) + ASME B31.4/B31.8 | "
        f"Mill Tolerance: {MILL_TOLERANCE*100}% | "
        f"Corrosion: {CORROSION_RATE_PER_YEAR} in/year × {DESIGN_LIFE_YEARS} years | "
        f"Hydrotest Factor: {HYDROTEST_FACTOR}×"
    )


if __name__ == "__main__":
    main()
