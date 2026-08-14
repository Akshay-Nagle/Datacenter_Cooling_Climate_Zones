# Climate-Adaptive Data Center Cooling: Energy-Water Trade-offs and Waste-Heat-Driven Atmospheric Water Harvesting

This repository contains the EnergyPlus building energy models, the atmospheric water harvesting (AWH) simulation script, and the output data underlying the results, tables, and figures reported in:

> Nagle, A., Jiang, J., & Westerhoff, P. (2026). Climate-adaptive data center cooling across U.S. climate zones: energy-water trade-offs and waste-heat-driven atmospheric water harvesting. *Energy and Climate Change* (in review).

## Repository structure

```
.
├── README.md
├── LICENSE
├── CITATION.cff
├── Energyplus Models/
│   ├── Atlanta GA 3A/
│   │   ├── USA_GA_Atlanta-Hartsfield-Jackson.Intl.AP.722190_TMY3.epw   # TMY3 weather file
│   │   ├── ATL_Original Hybrid.csv                                    # MONTHLY summary output, Hybrid system
│   │   ├── ACC/    # Air-Cooled Chiller: IDF + all EnergyPlus run outputs (.eso, .eio, .err, .mtr, .rdd, .bnd, hourly/meter CSVs, etc.)
│   │   ├── WCC/    # Water-Cooled Chiller: IDF + all EnergyPlus run outputs
│   │   └── Hybrid/ # Hybrid IEC+DEC+WCC: IDF + all EnergyPlus run outputs, including the HOURLY CSV used for AWH calculations
│   ├── Miami FL 1A/            (same internal layout)
│   ├── Minneapolis MN 6A/      (same internal layout)
│   ├── San Diego CA 3C/        (same internal layout)
│   ├── Chicago IL 5A/          (same internal layout)
│   ├── Denver CO 5B/           (same internal layout)
│   └── Phoenix AZ 2B/          (same internal layout)
├── AWH Simulation/
│   ├── AWH_Simulation_Final.py   # Full runnable AWH script: all city/scenario runs, both regeneration-temperature cases, plotting code
│   └── AWH_Output/               # Script writes all per-city, per-scenario output CSVs and plots here (see "Running the script" below)
└── Results (Graphs+Figures)/     # Final, publication-ready graphs and figures used in the manuscript and SI
```

Cities modeled: Atlanta, Miami, Minneapolis, San Diego, Chicago, Denver, Phoenix (ASHRAE climate zones 1A-6A). Each city/system combination uses a standardized 10 MW reference facility; only the TMY3 weather file and design-day conditions vary between cities.

## A note on the two CSV files per city

Each city folder contains **two different CSV files that are easy to confuse**:

1. **`{CITY}_Original Hybrid.csv`, directly inside the city folder (next to the `.epw` file)** — this is the **monthly** summary output for the Hybrid configuration only (used for high-level PUE/WUE and monthly-resolution comparisons).
2. **`{CITY}_Original Hybrid.csv`, inside the city's `Hybrid/` subfolder** — this is the full **hourly** EnergyPlus output for the Hybrid run. This is the file the AWH script (`AWH_Simulation_Final.py`) actually reads, because the AWH heat-recovery and cycle-accumulation logic requires hour-by-hour condenser flow, condenser temperature, and heat-rejection data (see Supplementary Information Section S3.4).

Both files share the same filename, so always check which folder you're in before use.

## Software and versions

- EnergyPlus 25.1.0
- Python 3.x with `pandas`, `numpy`, `matplotlib`

## Running the AWH simulation script

`AWH_Simulation_Final.py` currently points at two hardcoded, Windows-style relative paths near the top of the file (search for "Paths -- EDIT THESE"):

```python
INPUT_TEMPLATE = r"datacenter-cooling-climate-zones\Energyplus Models\{label}\Hybrid\{city}_Original Hybrid.csv"
OUTPUT_BASE_DIR = r"datacenter-cooling-climate-zones\AWH Simulation\AWH_Output"
```

These paths are written **relative to the folder that contains your cloned repository**, not relative to the script itself. That means:

- **If you run the script from one level above the cloned repo** (e.g., your terminal's working directory contains the `datacenter-cooling-climate-zones` folder), the paths above will resolve correctly with no changes.
- **If you run the script from inside the repo** (e.g., `cd` into `AWH Simulation/` first), these paths will fail, because there is no nested `datacenter-cooling-climate-zones` folder inside the repo itself.
- **On macOS/Linux**, the backslashes in these path strings will not work as directory separators; you will need to update them (see fix below).

### Recommended fix: anchor paths to the script's own location

To make the script portable across machines, operating systems, and clone locations, replace the two lines above with:

```python
BASE_DIR = Path(__file__).resolve().parent.parent  # repo root (one level up from "AWH Simulation/")
INPUT_TEMPLATE = str(BASE_DIR / "Energyplus Models" / "{label}" / "Hybrid" / "{city}_Original Hybrid.csv")
OUTPUT_BASE_DIR = str(BASE_DIR / "AWH Simulation" / "AWH_Output")
```

This uses `pathlib`, which is already imported in the script, so no new dependency is introduced. With this change, you can run the script from any working directory and it will always find the repo's own `Energyplus Models/` and `AWH Simulation/AWH_Output/` folders relative to itself.

If you don't want to edit the script, you can instead override the paths per run when calling the function directly, e.g.:

```python
run_city_scenario("PHX", "60C", input_path="/your/path/PHX_Original Hybrid.csv", out_dir="/your/output/path")
```

## How the files map to the paper

- IDF structure and cooling-system parameters (Supplementary Tables S1-S2): `Energyplus Models/{City}/{ACC,WCC,Hybrid}/`
- Equation 3 (main text) and Equations S1-S9 (SI): implemented in `AWH Simulation/AWH_Simulation_Final.py`
- Figure 5 and Figures S1-S2: generated by the script into `AWH Simulation/AWH_Output/Combined/`; final versions used in the paper are in `Results (Graphs+Figures)/`
- Weather file identifiers and WMO stations: see Supplementary Information Section S3.5; `.epw` files are third-party (NREL TMY3), provided directly here for reproducibility

## Data availability and citation

This GitHub repository hosts the actively developed version of the code and data. A versioned snapshot corresponding to the published article should be archived on Zenodo with a persistent DOI (recommended before final submission) and referenced here once minted.

Please cite both the article and, where reusing code/data directly, the archived version (see `CITATION.cff`).

## License

Code is released under the MIT License (see `LICENSE`). Data and figures are released under CC-BY 4.0 unless noted otherwise. TMY3 weather files are NREL public-domain data; sorbent/device parameters used in the AWH model are literature-derived (cited in-script and in Supplementary Information Section S3).

## Contact

For questions about the models or data, please open a GitHub issue or contact the corresponding author.
