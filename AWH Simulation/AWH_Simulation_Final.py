# Waste-heat-assisted Atmospheric Water Harvesting (AWH) simulation
# Hybrid cooling system only -- ACC and WCC are NOT connected to AWH.
#
# SORBENT + DEVICE: Ni2Cl2(BTDD) housed in a 3-module rotating adsorption
# architecture, per the following locked citation package:
#
#   - Rieth, A. J., Wright, A. M., Skorupskii, G., Mancuso, J. L., Hendon,
#     C. H., & Dinca, M. (2019). Record-setting sorbents for reversible
#     water uptake by systematic anion exchanges in metal-organic
#     frameworks. JACS, 141(35), 13858-13866. https://doi.org/10.1021/jacs.9b06246
#     -> isotherm, heat of adsorption, cyclic stability
#
#   - Shao, Z., Wang, Z.-S., Lv, H., et al. (2023). Modular all-day
#     continuous thermal-driven atmospheric water harvester with rotating
#     adsorption strategy. Applied Physics Reviews, 10(4), 041409.
#     https://doi.org/10.1063/5.0164055
#     -> device architecture, bed-count formula, cycle times, desorption
#        completeness, natural-convection condenser (no fans)
#
#   - Bagi, S., Wright, A. M., Oppenheim, J., Dinca, M., & Roman-Leshkov,
#     Y. (2021). Accelerated synthesis of a Ni2Cl2(BTDD) metal-organic
#     framework in a continuous flow reactor for atmospheric water
#     capture. ACS Sustainable Chem. Eng., 9(11), 3996-4003.
#     https://doi.org/10.1021/acssuschemeng.0c07055
#     -> scale-up synthesis pathway
#
# HEAT SOURCE: hourly waste heat from the Hybrid system's condenser water
# loop ONLY, and ONLY during hours when the mechanical chiller is actually
# engaged (i.e., condenser mass flow rate > 0). During pure economizer /
# IEC / DEC hours, HeatRejection:EnergyTransfer is nonzero but reflects
# heat rejected through evaporative media, NOT a liquid stream a heat pump
# can draw from -- gating on mass flow rather than the heat rejection
# meter avoids silently assuming an unusable heat source is usable. This
# gating was verified empirically per-city before writing this script (see
# your own diagnostic runs): chiller-on hours range from ~3.0% of the year
# (Denver) to ~52.3% (Miami) -- see manuscript Table 4.
#
# BED-AWARE ACCUMULATION (see SI Section S3.4): a contiguity check across
# all 7 cities' hourly data found that most chiller-on hours occur in
# SHORT, often ISOLATED runs (median block length = 2 hours in all seven
# cities; 52-62% of contiguous blocks shorter than the 3-hour desorption
# cycle). An earlier design credited ZERO water production to any block
# shorter than the required cycle time, on the reasoning that no published
# kinetics curve exists for PARTIAL desorption within an incomplete cycle
# for this material. That block-contiguity approach was REPLACED by the
# bed-aware accumulator implemented below (run_bed_aware_cycles), which
# instead RETAINS partial desorption progress in the sorbent bed's thermal
# mass across chiller-off gaps and credits water only once accumulated
# on-time reaches cycle_min. This is more physically realistic than an
# instantaneous per-block reset, though it has NOT been validated against
# measured partial-cycle kinetics for Ni2Cl2(BTDD), since no such data
# exists in the cited literature -- flag accordingly if used. Only the
# accumulation still in progress and short of cycle_min when the year ends
# goes permanently uncredited; this residual stays under 0.8% of annual
# chiller-on hours in every city and scenario.
#
# HEAT PUMP: required because the actual hourly condenser return
# temperature (verified per-city, means ~27-35C depending on city) sits
# well below both regeneration targets. COP is computed FRESH for every
# completed cycle from that cycle's actual mean condenser temperature
# (not a fixed design-point value), using the Carnot limit scaled by a
# realistic efficiency factor. The realistic-efficiency range (40-50% of
# Carnot) is standard heat pump engineering practice, NOT sorbent-specific
# -- flagged accordingly.
#
# ELECTRICAL ACCOUNTING: Shao et al.'s previously-used 11,240 Wh/L figure
# is DELIBERATELY NOT USED here. That number was their resistive heater
# standing in for waste heat in a proof-of-concept -- now that heat
# pump-delivered thermal energy is modeled explicitly, reusing that figure
# would double-count the same energy as both "recovered waste heat" and
# "electricity consumed." The only electrical term retained is the heat
# pump compressor draw (Q_delivered / COP). Balance-of-plant electricity
# (fans, controls) is set to zero, which is not an assumption of
# convenience -- Shao et al.'s methods section explicitly states their
# device ran "without the use of auxiliary equipment such as fans," relying
# on natural convection for both adsorption airflow and condensation.
# ============================================================================

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------
# (A) Sorbent physics -- Ni2Cl2(BTDD), Rieth et al. (2019)
# ----------------------------------------------------------------------
WATER_MOLAR_MASS_KG_PER_MOL = 0.018015
HEAT_OF_ADSORPTION_KJ_PER_MOL = 57.0                 # Rieth et al. (2019), stated directly
THERMAL_KJ_PER_L = HEAT_OF_ADSORPTION_KJ_PER_MOL / WATER_MOLAR_MASS_KG_PER_MOL  # -> 3164 kJ/L

ISOTHERM_MAX_CAPACITY_KG_PER_KG = 1.07                # Rieth et al. (2019), Table 3, at 35% RH
ISOTHERM_STEP_RH = 0.32                               # Rieth et al. (2019), Figure 3A inflection
ISOTHERM_FLOOR_RH = 0.25                              # Below this: negligible uptake per Rieth
                                                        # Fig 3A (qualitative, no exact anchor
                                                        # value below ~25% RH in the source paper).
                                                        # The 25-32% RH ramp is a LINEAR
                                                        # INTERPOLATION, not a citation -- flag
                                                        # in Limitations for dry cities
                                                        # (Phoenix, Denver) specifically.

DESORPTION_COMPLETENESS = 0.906                       # Shao et al. (2023) SI, measured at 80C.
                                                        # Applied to BOTH scenarios (60C and 80C)
                                                        # since no separately-measured completeness
                                                        # value exists for 60C -- flagged.

# ----------------------------------------------------------------------
# (B) Device -- Shao et al. (2023)
# ----------------------------------------------------------------------
BEDS_PER_UNIT = 3                                     # (x/y)+1 formula: (240/120)+1 = 3
SORBENT_MASS_PER_PLATE_KG = 0.01582                   # 15.82 g, Shao et al., directly stated
SORBENT_MASS_PER_UNIT_KG = BEDS_PER_UNIT * SORBENT_MASS_PER_PLATE_KG  # 0.04746 kg
BALANCE_OF_PLANT_ELEC_KWH = 0.0                       # Shao et al.: device ran fan-free, natural
                                                        # convection only -- citable, not assumed.

# ----------------------------------------------------------------------
# (C) Regeneration-temperature scenarios
# ----------------------------------------------------------------------
SCENARIOS = {
    "60C": {
        "T_target_C": 60.0,
        "cycle_min": 180.0,   # ESTIMATED -- interpolated from Rieth et al.'s 70C/3h
                              # reactivation data point, NOT a measured value at 60C for
                              # this material. State this explicitly in Methods/Limitations
                              # if this scenario's numbers are used in the main text.
        "report_as": "main_paper",
    },
    "80C": {
        "T_target_C": 80.0,
        "cycle_min": 120.0,  # Shao et al. (2023), directly measured device-level value.
        "report_as": "supplementary_information",
    },
}

# ----------------------------------------------------------------------
# (D) Sensitivities -- fixed values per explicit instruction, NOT sweeps
# ----------------------------------------------------------------------
#
# RECOVERY_FRACTION represents the fraction of the Hybrid system's
# chiller-active-hour HeatRejection:EnergyTransfer that is actually
# captured by a heat exchanger and delivered to the heat pump's
# evaporator/source side, before any temperature lift takes place. This
# is NOT the same quantity as heat pump COP (which describes how
# efficiently that captured heat is then upgraded in temperature) -- the
# two are separate physical stages: (1) capturing heat from the facility
# stream into the AWH loop, then (2) upgrading its temperature. No
# published, measured value exists for this specific capture efficiency
# for THIS heat-exchanger/heat-pump pairing (no such device has been
# built). 0.85 is used here as a fixed, explicitly acknowledged modeling
# choice representing an optimistic-but-plausible capture efficiency for
# a well-designed liquid-to-liquid heat exchanger (typical real shell-
# and-tube or plate heat exchangers achieve 80-90% effectiveness in HVAC
# practice) -- NOT a value taken from any AWH-specific source. State this
# plainly in Methods: "a fixed heat-exchanger capture efficiency of 0.85
# was assumed, representing a plausible upper-range value for
# well-designed liquid heat exchangers; no AWH-specific measurement of
# this parameter exists in the literature."
RECOVERY_FRACTION = 0.85

# Realistic heat pump efficiency as a fraction of the Carnot limit.
# Standard heat pump/refrigeration engineering practice reports
# real-world vapor-compression systems achieving 40-50% of Carnot COP.
# This is GENERIC heat pump engineering knowledge, not sorbent-specific
# or AWH-specific -- flagged accordingly. Midpoint used here.
COP_EFFICIENCY_FACTOR = 0.45

AUTOSIZE_UNITS = True   # fleet sized to each city's own peak-hour demand

# ----------------------------------------------------------------------
# City configuration (elevation drives station pressure for RH calc)
# ----------------------------------------------------------------------
CITY_CONFIGS = {
    "ATL": {"elevation_m": 313.0, "label": "Atlanta GA 3A"},
    "MI":  {"elevation_m": 2.7,   "label": "Miami FL 1A"},
    "MSP": {"elevation_m": 256.0, "label": "Minneapolis MN 6A"},
    "SD":  {"elevation_m": 4.6,   "label": "San Diego CA 3C"},
    "CHI": {"elevation_m": 201.0, "label": "Chicago IL 5A"},
    "DEN": {"elevation_m": 1655.0,"label": "Denver CO 5B"},
    "PHX": {"elevation_m": 337.0, "label": "Phoenix AZ 2B"},
}

# ----------------------------------------------------------------------
# Paths -- EDIT THESE to match your local directory structure.
# ----------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent  
INPUT_TEMPLATE = str(BASE_DIR / "Energyplus Models" / "{label}" / "Hybrid" / "{city}_Original Hybrid.csv")
OUTPUT_BASE_DIR = str(BASE_DIR / "AWH Simulation" / "AWH_Output")

EPW_YEAR = 2024

COL_TIME  = "Date/Time"
COL_TDB   = "Environment:Site Outdoor Air Drybulb Temperature [C](Hourly)"
COL_TWB   = "Environment:Site Outdoor Air Wetbulb Temperature [C](Hourly)"
COL_REJ_J = "HeatRejection:EnergyTransfer [J](Hourly)"
COL_COND_FLOW = "CONDENSER TOWER INLET NODE:System Node Mass Flow Rate [kg/s](Hourly)"
COL_COND_TIN  = "CONDENSER TOWER INLET NODE:System Node Temperature [C](Hourly)"

# ----------------------------------------------------------------------
# Elevation -> station pressure (standard barometric formula)
# ----------------------------------------------------------------------
def station_pressure_kpa(elevation_m: float, p0_kpa: float = 101.325) -> float:
    return p0_kpa * (1.0 - 2.25577e-5 * elevation_m) ** 5.25588

# ----------------------------------------------------------------------
# Parsing and psychrometrics
# ----------------------------------------------------------------------
def parse_energyplus_datetime(series, year=2024):
    s = series.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    parts = s.str.split(" ", n=1, expand=True)
    md = parts[0].str.split("/", expand=True)
    tm = parts[1].str.split(":", expand=True)
    mm = md[0].astype(int); dd = md[1].astype(int)
    HH = tm[0].astype(int); MI = tm[1].astype(int); SS = tm[2].astype(int)
    is_24 = HH == 24
    HH = np.where(is_24, 0, HH)
    dt = pd.to_datetime({"year": year, "month": mm, "day": dd,
                         "hour": HH, "minute": MI, "second": SS}, errors="coerce")
    dt = dt + pd.to_timedelta(is_24.astype(int), unit="D")
    return dt

def p_ws_tetens_kpa_vec(T_C: np.ndarray) -> np.ndarray:
    return 0.61078 * np.exp((17.27 * T_C) / (T_C + 237.3))

def rh_from_tdb_twb_vec(Tdb_C: np.ndarray, Twb_C: np.ndarray, p_kpa: float) -> np.ndarray:
    gamma = 0.00066 * (1.0 + 0.00115 * Twb_C)
    pws_wb = p_ws_tetens_kpa_vec(Twb_C)
    diff = np.maximum(0.0, Tdb_C - Twb_C)
    pv = pws_wb - gamma * p_kpa * diff
    pws_db = p_ws_tetens_kpa_vec(Tdb_C)
    pv = np.clip(pv, 0.0, pws_db)
    RH = pv / np.maximum(1e-9, pws_db)
    return np.clip(RH, 0.0, 1.0)

# ----------------------------------------------------------------------
# Isotherm: linear ramp 25-32% RH (interpolated, not measured), flat
# above the 35%-RH-anchored max capacity above the step.
# ----------------------------------------------------------------------
def working_capacity_kgkg(RH_frac: float) -> float:
    if RH_frac < ISOTHERM_FLOOR_RH:
        uptake = 0.0
    elif RH_frac < ISOTHERM_STEP_RH:
        frac = (RH_frac - ISOTHERM_FLOOR_RH) / (ISOTHERM_STEP_RH - ISOTHERM_FLOOR_RH)
        uptake = frac * ISOTHERM_MAX_CAPACITY_KG_PER_KG
    else:
        uptake = ISOTHERM_MAX_CAPACITY_KG_PER_KG
    return uptake * DESORPTION_COMPLETENESS

# ----------------------------------------------------------------------
# BED-AWARE ACCUMULATOR: replaces block-contiguity gating.
#
# MODELING ASSUMPTION (flag in Methods/Limitations if used): partial
# desorption progress accumulates in the sorbent bed's thermal mass and
# is RETAINED across chiller-off gaps, rather than being lost when a
# contiguous block ends. This is more physically realistic than assuming
# the bed instantaneously resets to zero on every chiller-off transition,
# but it has NOT been validated against measured partial-cycle kinetics
# for Ni2Cl2(BTDD) -- no such data exists in the cited literature. Only
# fully-accumulated cycles (>= cycle_min total on-time) produce water;
# any leftover accumulation at year-end that never reaches cycle_min is
# still credited as zero (this residual is now small, not the dominant
# loss term it was under block-contiguity gating).
# ----------------------------------------------------------------------
def run_bed_aware_cycles(df, scen, sorbent_mass_kg_fleet=None):
    cycle_min = scen["cycle_min"]
    is_on = (df["cond_flow"] > 1e-6).to_numpy()
    T_source_arr = df["cond_Tin"].to_numpy()
    RH_arr = df["RH_frac"].to_numpy()
    heat_arr = df["waste_heat_kWh"].to_numpy()
    month_arr = df["datetime"].dt.month.to_numpy()

    cycle_records = []
    acc_minutes = 0.0
    acc_heat_kWh = 0.0
    acc_T_weighted = 0.0
    acc_RH_weighted = 0.0
    acc_month = None
    n_hours_in_progress = 0

    for i in range(len(df)):
        if not is_on[i]:
            continue

        acc_minutes += 60.0
        acc_heat_kWh += heat_arr[i]
        acc_T_weighted += T_source_arr[i]
        acc_RH_weighted += RH_arr[i]
        n_hours_in_progress += 1
        if acc_month is None:
            acc_month = month_arr[i]

        if acc_minutes >= cycle_min:
            T_source = acc_T_weighted / n_hours_in_progress
            RH_avg = acc_RH_weighted / n_hours_in_progress
            cop = cop_for_cycle(scen["T_target_C"], T_source)

            if np.isinf(cop):
                Q_hot_max_kWh = acc_heat_kWh
            else:
                Q_hot_max_kWh = acc_heat_kWh * cop / (cop - 1.0)

            if sorbent_mass_kg_fleet is None:
                # PASS 1: sizing mode -- uncapped, no bed-capacity limit
                Q_delivered_kWh = Q_hot_max_kWh
            else:
                # PASS 2: production mode -- capped by actual fleet bed capacity
                wc = working_capacity_kgkg(RH_avg)
                water_L_capacity = sorbent_mass_kg_fleet * wc
                Q_bed_capacity_kWh = water_L_capacity * THERMAL_KJ_PER_L / 3600.0
                Q_delivered_kWh = min(Q_hot_max_kWh, Q_bed_capacity_kWh)

            elec_kWh = Q_delivered_kWh / cop if (cop > 0 and not np.isinf(cop)) else 0.0
            water_L = Q_delivered_kWh * 3600.0 / THERMAL_KJ_PER_L

            cycle_records.append({
                "month": acc_month, "T_source_C": T_source, "RH_frac": RH_avg,
                "cop": cop if not np.isinf(cop) else np.nan,
                "water_L": water_L, "heat_pump_elec_kWh": elec_kWh,
                "Q_hot_max_kWh": Q_hot_max_kWh,
            })

            acc_minutes = 0.0
            acc_heat_kWh = 0.0
            acc_T_weighted = 0.0
            acc_RH_weighted = 0.0
            acc_month = None
            n_hours_in_progress = 0

    residual_wasted_hours = n_hours_in_progress
    return pd.DataFrame(cycle_records), residual_wasted_hours

# ----------------------------------------------------------------------
# Heat pump COP for one completed cycle
# ----------------------------------------------------------------------
def cop_for_cycle(T_target_C: float, T_source_C: float) -> float:
    if T_source_C >= T_target_C:
        return float("inf")   # source already hot enough -- no lift needed
    T_target_K = T_target_C + 273.15
    T_source_K = T_source_C + 273.15
    cop_carnot = T_target_K / (T_target_K - T_source_K)
    return cop_carnot * COP_EFFICIENCY_FACTOR

# ----------------------------------------------------------------------
# Fleet sizing: peak-hour autosizing against the theoretical max bed duty
# ----------------------------------------------------------------------
def max_bed_thermal_kw(cycle_min: float) -> float:
    max_wc = ISOTHERM_MAX_CAPACITY_KG_PER_KG * DESORPTION_COMPLETENESS
    water_L = SORBENT_MASS_PER_PLATE_KG * max_wc  # 1 kg/kg = 1 L/kg
    E_kWh = water_L * THERMAL_KJ_PER_L / 3600.0
    t_h = cycle_min / 60.0
    return E_kWh / t_h

# ----------------------------------------------------------------------
# Main per-city, per-scenario pipeline
# ----------------------------------------------------------------------
def run_city_scenario(city_key: str, scenario_key: str, input_path: str = None,
                       out_dir: str = None):
    cfg = CITY_CONFIGS[city_key]
    label = cfg["label"]
    scen = SCENARIOS[scenario_key]
    p_kpa = station_pressure_kpa(cfg["elevation_m"])

    in_path = input_path or INPUT_TEMPLATE.format(label=label, city=city_key)
    out_root = Path(out_dir or OUTPUT_BASE_DIR) / city_key
    out_root.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(in_path, engine="python")
    df.columns = [c.strip() for c in df.columns]

    df["datetime"] = parse_energyplus_datetime(df[COL_TIME], year=EPW_YEAR)
    df["Tdb_C"] = pd.to_numeric(df[COL_TDB], errors="coerce")
    df["Twb_C"] = pd.to_numeric(df[COL_TWB], errors="coerce")
    df["Qrej_J"] = pd.to_numeric(df[COL_REJ_J], errors="coerce").fillna(0.0)
    df["cond_flow"] = pd.to_numeric(df[COL_COND_FLOW], errors="coerce").fillna(0.0)
    df["cond_Tin"] = pd.to_numeric(df[COL_COND_TIN], errors="coerce")
    df = df.dropna(subset=["datetime", "Tdb_C", "Twb_C"]).sort_values("datetime").reset_index(drop=True)

    df["RH_frac"] = rh_from_tdb_twb_vec(df["Tdb_C"].to_numpy(), df["Twb_C"].to_numpy(), p_kpa)
    df["RH_percent"] = df["RH_frac"] * 100.0
    df["waste_heat_kWh"] = (df["Qrej_J"] / 3.6e6) * RECOVERY_FRACTION

    is_on = (df["cond_flow"] > 1e-6).to_numpy()  # kept only for chiller-on hour reporting

    # ------------------------------------------------------------------
    # PASS 1 (bed-aware, uncapped): find the richest completed cycle's
    # heat demand to size the fleet.
    # ------------------------------------------------------------------
    cyc_uncapped, _ = run_bed_aware_cycles(df, scen, sorbent_mass_kg_fleet=None)

    if not cyc_uncapped.empty:
        max_wc_possible = ISOTHERM_MAX_CAPACITY_KG_PER_KG * DESORPTION_COMPLETENESS
        single_unit_water_L_capacity = SORBENT_MASS_PER_UNIT_KG * max_wc_possible
        single_unit_kWh_capacity = single_unit_water_L_capacity * THERMAL_KJ_PER_L / 3600.0
        peak_Q_hot_kWh = cyc_uncapped["Q_hot_max_kWh"].max()
        fleet_units = max(1, int(np.ceil(peak_Q_hot_kWh / max(single_unit_kWh_capacity, 1e-9))))
    else:
        fleet_units = 1

    sorbent_mass_kg_fleet = SORBENT_MASS_PER_UNIT_KG * fleet_units

    # ------------------------------------------------------------------
    # PASS 2 (bed-aware, capped): actual delivered water/electricity,
    # now that fleet size is fixed.
    # ------------------------------------------------------------------
    cyc_df, residual_wasted_hours = run_bed_aware_cycles(
        df, scen, sorbent_mass_kg_fleet=sorbent_mass_kg_fleet
    )
    wasted_block_hours = float(residual_wasted_hours)
 

    # ---- Hourly RH/temp series for the RH-vs-production plot & full record ----
    hourly_out = df[["datetime", "Tdb_C", "Twb_C", "RH_frac", "RH_percent",
                      "cond_flow", "cond_Tin", "waste_heat_kWh"]].copy()
    hourly_out.to_csv(out_root / f"{city_key}_{scenario_key}_hourly.csv", index=False)

    # ---- Monthly summary, WITH monthly mean RH column as requested ----
    df["month"] = df["datetime"].dt.month
    monthly_rh = df.groupby("month").agg(
        Monthly_Mean_RH_percent=("RH_percent", "mean"),
        Monthly_Mean_Tdb_C=("Tdb_C", "mean"),
        Chiller_On_Hours=("cond_flow", lambda x: (x > 1e-6).sum()),
    ).reset_index()

    if not cyc_df.empty:
        monthly_prod = cyc_df.groupby("month").agg(
            Total_Water_L=("water_L", "sum"),
            Total_HeatPump_Elec_kWh=("heat_pump_elec_kWh", "sum"),
            Completed_Cycles=("water_L", "count"),
            Mean_COP=("cop", "mean"),
        ).reset_index()
        monthly = monthly_rh.merge(monthly_prod, on="month", how="left")
    else:
        monthly = monthly_rh.copy()
        monthly["Total_Water_L"] = 0.0
        monthly["Total_HeatPump_Elec_kWh"] = 0.0
        monthly["Completed_Cycles"] = 0
        monthly["Mean_COP"] = np.nan

    monthly[["Total_Water_L", "Total_HeatPump_Elec_kWh", "Completed_Cycles"]] = \
        monthly[["Total_Water_L", "Total_HeatPump_Elec_kWh", "Completed_Cycles"]].fillna(0.0)

    monthly["city"] = city_key
    monthly["scenario"] = scenario_key
    monthly["T_target_C"] = scen["T_target_C"]
    monthly.to_csv(out_root / f"{city_key}_{scenario_key}_monthly.csv", index=False)

    # ---- Annual summary ----
    total_water_L = cyc_df["water_L"].sum() if not cyc_df.empty else 0.0
    total_elec_kWh = cyc_df["heat_pump_elec_kWh"].sum() if not cyc_df.empty else 0.0
    total_chiller_on_hours = int(is_on.sum())

    annual = pd.DataFrame({
        "city": [city_key], "scenario": [scenario_key],
        "T_target_C": [scen["T_target_C"]], "cycle_min": [scen["cycle_min"]],
        "recovery_fraction": [RECOVERY_FRACTION],
        "cop_efficiency_factor": [COP_EFFICIENCY_FACTOR],
        "fleet_units_autosized": [fleet_units],
        "total_chiller_on_hours": [total_chiller_on_hours],
        "pct_year_chiller_on": [100.0 * total_chiller_on_hours / len(df)],
        "wasted_block_hours": [wasted_block_hours],
        "pct_chiller_on_hours_wasted": [100.0 * wasted_block_hours / max(total_chiller_on_hours, 1)],
        "completed_cycles": [len(cyc_df)],
        "total_water_L": [total_water_L],
        "total_water_L_per_day": [total_water_L / 365.0],
        "total_heat_pump_elec_kWh": [total_elec_kWh],
    })
    annual.to_csv(out_root / f"{city_key}_{scenario_key}_annual_summary.csv", index=False)

    print(f"[{city_key}/{scenario_key}] chiller-on={total_chiller_on_hours}h "
          f"({100*total_chiller_on_hours/len(df):.1f}%), wasted={wasted_block_hours:.0f}h, "
          f"cycles={len(cyc_df)}, water={total_water_L:.1f}L/yr")

    return monthly

# ----------------------------------------------------------------------
# RH vs. water production plot -- one figure per scenario, all 7 cities
# ----------------------------------------------------------------------
def plot_rh_vs_production(all_monthly: pd.DataFrame, scenario_key: str, out_dir: str):
    sub = all_monthly[all_monthly["scenario"] == scenario_key]
    fig, ax = plt.subplots(figsize=(8, 6))
    for city_key, grp in sub.groupby("city"):
        ax.scatter(grp["Monthly_Mean_RH_percent"], grp["Total_Water_L"],
                   label=CITY_CONFIGS[city_key]["label"], alpha=0.75)
    ax.set_xlabel("Monthly mean relative humidity (%)")
    ax.set_ylabel("Monthly water production (L)")
    ax.set_title(f"RH vs. AWH water production -- {scenario_key} scenario")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out_path = Path(out_dir) / f"RH_vs_Production_{scenario_key}.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved plot: {out_path}")

# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------
def run_all():
    all_monthly = []
    for city_key in CITY_CONFIGS:
        for scenario_key in SCENARIOS:
            try:
                m = run_city_scenario(city_key, scenario_key)
                all_monthly.append(m)
            except FileNotFoundError as e:
                print(f"[{city_key}/{scenario_key}] SKIPPED -- {e}")

    if all_monthly:
        combined = pd.concat(all_monthly, ignore_index=True)
        combined_dir = Path(OUTPUT_BASE_DIR) / "Combined"
        combined_dir.mkdir(parents=True, exist_ok=True)
        combined.to_csv(combined_dir / "All_Cities_Monthly_Summary.csv", index=False)
        for scenario_key in SCENARIOS:
            plot_rh_vs_production(combined, scenario_key, combined_dir)

if __name__ == "__main__":
    # Example single-city, single-scenario run for testing:
    # run_city_scenario("PHX", "60C", input_path=r"C:\path\to\PHX_Original_Hybrid.csv", out_dir=r"C:\path\to\output")
    run_all()
