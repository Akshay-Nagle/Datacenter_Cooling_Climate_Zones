# Climate-Adaptive Data Center Cooling Across U.S. Climate Zones

**Energy-water trade-offs and waste-heat-assisted atmospheric water harvesting**

Akshay Nagle, Jinyue Jiang, Paul Westerhoff
School of Sustainable Engineering and the Built Environment, Arizona State University, Tempe, Arizona 85287, USA

This repository contains the EnergyPlus building energy models, the atmospheric water harvesting (AWH) simulation script, and the underlying output data for the manuscript submitted to *Energy and Climate Change* (Elsevier).

## About this study

Data centers are being built fastest in regions where electricity and water are already scarce, yet a facility's cooling system, locked in for decades, sets its demand for both. This study simulates three cooling architectures for one identical 10 MW reference facility across seven U.S. cities spanning ASHRAE climate zones 1-6:

| City | ASHRAE zone | Climate character |
|---|---|---|
| Miami, FL | 1A | Hot-humid |
| Phoenix, AZ | 2B | Hot-dry |
| Atlanta, GA | 3A | Warm-humid |
| San Diego, CA | 3C | Warm-marine |
| Chicago, IL | 5A | Cool-humid |
| Denver, CO | 5B | Cool-dry |
| Minneapolis, MN | 6A | Cold |

**Cooling architectures compared:**
- **ACC** - Air-Cooled Chiller: rejects heat directly to outdoor air, no on-site water use, efficiency capped by dry-bulb temperature.
- **WCC** - Water-Cooled Chiller: rejects heat through a cooling tower governed by wet-bulb temperature; more efficient, but consumes water continuously.
- **Hybrid** - An adaptive system staging air-side economization, indirect and direct evaporative cooling, and mechanical refrigeration hour-by-hour via an EnergyPlus EMS controller, so the facility captures evaporative efficiency when weather allows and falls back on mechanical cooling only when it doesn't.

**Key findings:** the Hybrid system cuts on-site water use by 20-60% relative to WCC in every climate, but its energy performance is climate-dependent - saving energy in hot cities, roughly unchanged in one dry, cool climate, and costing 2-5% more in mild or cold climates. A waste-heat-assisted AWH model, coupled only to the Hybrid system's condenser loop, recovers the most water where the Hybrid saves the least cooling water, offsetting up to 37% of cooling-water demand in humid climates for an added electricity cost near 8%, and almost nothing in dry ones.

**Metrics used throughout:**
- **PUE** (Power Usage Effectiveness) = Total facility electricity / IT-equipment electricity
- **WUE** (Water Usage Effectiveness) = On-site cooling makeup water (L) / IT-equipment electricity (kWh)

All results come from annual, hourly whole-building EnergyPlus 25.1.0 simulations using each city's TMY3 weather file (21 simulations: 7 cities x 3 systems).

## Repository structure

```
.
├── README.md
├── LICENSE
├── CITATION.cff
├── Energyplus Models/
│   ├── Atlanta GA 3A/
│   │   ├── USA_GA_Atlanta-Hartsfield-Jackson.Intl.AP.722190_TMY3.epw   # TMY3 weather file
│   │   ├── ATL_Original Hybrid.csv                                    # MONTHLY summary output, Hybrid system only
│   │   ├── ACC/       # Air-Cooled Chiller: IDF + full EnergyPlus output set (see below)
│   │   ├── WCC/       # Water-Cooled Chiller: IDF + full EnergyPlus output set
│   │   └── Hybrid/    # Hybrid IEC+DEC+WCC: IDF + full EnergyPlus output set, incl. the HOURLY CSV used for AWH
│   ├── Miami FL 1A/            (same internal layout)
│   ├── Minneapolis MN 6A/      (same internal layout)
│   ├── San Diego CA 3C/        (same internal layout)
│   ├── Chicago IL 5A/          (same internal layout)
│   ├── Denver CO 5B/           (same internal layout)
│   └── Phoenix AZ 2B/          (same internal layout)
└── AWH Simulation/
    ├── AWH_Simulation_Final.py   # Full runnable AWH script: all city/scenario runs, both regeneration-temperature cases, plotting code
    └── AWH_Output/               # Script writes all per-city, per-scenario output CSVs and plots here
```

Each `ACC/`, `WCC/`, and `Hybrid/` folder contains the complete EnergyPlus run output for that city/system combination:

| File | Contents |
|---|---|
| `*.idf` | The EnergyPlus input file (building geometry, loads, plant, and controls) |
| `*.csv` | Hourly time-series output (the main simulation results file) |
| `*Meter.csv` | Hourly meter-level energy/water output |
| `*Ssz.csv`, `*Zsz.csv` | System- and zone-level autosizing reports |
| `*Table.html` | EnergyPlus tabular summary report (annual totals, end-use breakdowns) |
| `*.eio`, `*.eso`, `*.mtr`, `*.mtd`, `*.rdd`, `*.bnd`, `*.audit`, `*.err`, `*.rvaudit`, `*.shd`, `*.svg` | Standard EnergyPlus diagnostic/auxiliary output files (initialization echo, raw binary-equivalent output stream, meter dictionary, report-variable dictionary, surface boundary conditions, sizing/run audit logs, error log, shading illustration) |

## A note on the two "Original Hybrid.csv" files per city

Each city folder contains **two different CSV files with the same name that are easy to confuse**:

1. **`{CITY}_Original Hybrid.csv`, directly inside the city folder (next to the `.epw` file)** - this is the **monthly** summary output for the Hybrid configuration only.
2. **`{CITY}_Original Hybrid.csv`, inside the city's `Hybrid/` subfolder** - this is the full **hourly** EnergyPlus output for the Hybrid run. This is the file `AWH_Simulation_Final.py` actually reads, because the AWH heat-recovery and cycle-accumulation logic requires hour-by-hour condenser flow, condenser temperature, and heat-rejection data (see Supplementary Information Section S3.4).

Always check which folder you're in before use.

## Software and versions

- EnergyPlus 25.1.0
- Python 3.x with `pandas`, `numpy`, `matplotlib`

## Running the AWH simulation script

`AWH_Simulation_Final.py` currently points at two hardcoded, Windows-style relative paths near the top of the file (search for "Paths -- EDIT THESE"):

```python
INPUT_TEMPLATE = r"datacenter-cooling-climate-zones\Energyplus Models\{label}\Hybrid\{city}_Original Hybrid.csv"
OUTPUT_BASE_DIR = r"datacenter-cooling-climate-zones\AWH Simulation\AWH_Output"
```

These paths are written **relative to the folder that contains your cloned repository**, not relative to the script itself:

- **If you run the script from one level above the cloned repo** (your terminal's working directory contains the `datacenter-cooling-climate-zones` folder), these paths resolve correctly with no changes.
- **If you run the script from inside the repo** (e.g., after `cd`-ing into `AWH Simulation/`), these paths will fail - there's no nested `datacenter-cooling-climate-zones` folder inside the repo itself.
- **On macOS/Linux**, the backslashes in these strings won't work as path separators.

### Recommended fix: anchor paths to the script's own location

Replace the two lines above with:

```python
BASE_DIR = Path(__file__).resolve().parent.parent  # repo root (one level up from "AWH Simulation/")
INPUT_TEMPLATE = str(BASE_DIR / "Energyplus Models" / "{label}" / "Hybrid" / "{city}_Original Hybrid.csv")
OUTPUT_BASE_DIR = str(BASE_DIR / "AWH Simulation" / "AWH_Output")
```

This uses `pathlib`, already imported in the script, so no new dependency is introduced, and the script will work from any working directory, on any OS, regardless of where the repo is cloned.

Alternatively, without editing the script, override paths per call:

```python
run_city_scenario("PHX", "60C", input_path="/your/path/PHX_Original Hybrid.csv", out_dir="/your/output/path")
```

## How the files map to the paper

- IDF structure and cooling-system parameters (Supplementary Tables S1-S2): `Energyplus Models/{City}/{ACC,WCC,Hybrid}/`
- Equation 3 (main text) and Equations S1-S9 (Supplementary Information Section S3): implemented in `AWH Simulation/AWH_Simulation_Final.py`
- Figure 5 and Figures S1-S2 (RH vs. AWH production by city): generated by the script into `AWH Simulation/AWH_Output/Combined/`
- Weather file identifiers and WMO stations: Supplementary Information Section S3.5; `.epw` files are third-party NREL TMY3 data, provided directly here for reproducibility
- Sorbent (Ni2Cl2(BTDD)) isotherm, device architecture, and synthesis pathway citations: see script header comments and Supplementary Information Section S3.1-S3.2

## Data availability and citation

This GitHub repository hosts the actively developed version of the code and data. A versioned snapshot corresponding to the published article should be archived on Zenodo with a persistent DOI (recommended before final submission) and referenced here once minted.

Please cite both the article and, where reusing code/data directly, the archived version (see `CITATION.cff`).

## License

Code is released under the MIT License (see `LICENSE`). Data is released under CC-BY 4.0 unless noted otherwise. TMY3 weather files are NREL public-domain data; sorbent/device parameters used in the AWH model are literature-derived (cited in-script and in Supplementary Information Section S3).

## Contact

For questions about the models or data, please open a GitHub issue or contact the corresponding author.
