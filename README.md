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
├── LICENSE-DATA.txt
├── CITATION.cff
├── Energyplus Models/
│   ├── Atlanta GA 3A/
│   │   ├── USA_GA_Atlanta-Hartsfield-Jackson.Intl.AP.722190_TMY3.epw   # TMY3 weather file
│   │   ├── ATL_Original Hybrid.csv                                    # Monthly summary output, Hybrid system only
│   │   ├── ACC/       # Air-Cooled Chiller: IDF + full EnergyPlus output set (see below)
│   │   ├── WCC/       # Water-Cooled Chiller: IDF + full EnergyPlus output set
│   │   └── Hybrid/    # Hybrid IEC+DEC+WCC: IDF + full EnergyPlus output set, incl. the hourly CSV used for AWH
│   ├── Miami FL 1A/            (same internal layout)
│   ├── Minneapolis MN 6A/      (same internal layout)
│   ├── San Diego CA 3C/        (same internal layout)
│   ├── Chicago IL 5A/          (same internal layout)
│   ├── Denver CO 5B/           (same internal layout)
│   └── Phoenix AZ 2B/          (same internal layout)
└── AWH Simulation/
    ├── AWH_Simulation_Final.py   # Full runnable AWH script: all city/scenario runs, both regeneration-temperature cases, plotting code
    └── AWH_Output/               # Per-city, per-scenario output CSVs and plots
```

Each `ACC/`, `WCC/`, and `Hybrid/` folder contains the complete EnergyPlus run output for that city/system combination:

| File | Contents |
|---|---|
| `*.idf` | The EnergyPlus input file (building geometry, loads, plant, and controls) |
| `*.csv` | Hourly time-series output (the main simulation results file) |
| `*Meter.csv` | Hourly meter-level energy/water output |
| `*Ssz.csv`, `*Zsz.csv` | System- and zone-level autosizing reports |
| `*Table.html` | EnergyPlus tabular summary report (annual totals, end-use breakdowns) |
| `*.eio`, `*.eso`, `*.mtr`, `*.mtd`, `*.rdd`, `*.bnd`, `*.audit`, `*.err`, `*.rvaudit`, `*.shd`, `*.svg` | Standard EnergyPlus diagnostic/auxiliary output files |

## A note on the two "Original Hybrid.csv" files per city

Each city folder contains two different CSV files with the same name:

1. **`{CITY}_Original Hybrid.csv`, directly inside the city folder (next to the `.epw` file)** - the monthly summary output for the Hybrid configuration only.
2. **`{CITY}_Original Hybrid.csv`, inside the city's `Hybrid/` subfolder** - the full hourly EnergyPlus output for the Hybrid run. This is the file `AWH_Simulation_Final.py` reads, because the AWH heat-recovery and cycle-accumulation logic requires hour-by-hour condenser flow, condenser temperature, and heat-rejection data (see Supplementary Information Section S3.4).

## Software and versions

- EnergyPlus 25.1.0
- Python 3.x with `pandas`, `numpy`, `matplotlib`

## Running the AWH simulation script

Run the script from anywhere; it resolves its own input and output directories relative to its location in the repository:

```bash
python "AWH Simulation/AWH_Simulation_Final.py"
```

This processes all seven cities under both regeneration-temperature scenarios (60C and 80C) and writes per-city, per-scenario CSVs and combined plots to `AWH Simulation/AWH_Output/`.

To run a single city/scenario combination:

```python
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location("awh", "AWH Simulation/AWH_Simulation_Final.py")
awh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(awh)
awh.run_city_scenario("PHX", "60C")
```

## How the files map to the paper

- IDF structure and cooling-system parameters (Supplementary Tables S1-S2): `Energyplus Models/{City}/{ACC,WCC,Hybrid}/`
- Equation 3 (main text) and Equations S1-S9 (Supplementary Information Section S3): implemented in `AWH Simulation/AWH_Simulation_Final.py`
- Figure 5 and Figures S1-S2 (RH vs. AWH production by city): generated by the script into `AWH Simulation/AWH_Output/Combined/`
- Weather file identifiers and WMO stations: Supplementary Information Section S3.5
- Sorbent (Ni2Cl2(BTDD)) isotherm, device architecture, and synthesis pathway citations: see script header comments and Supplementary Information Section S3.1-S3.2

## Data availability and citation

This GitHub repository hosts the actively developed version of the code and data. A versioned snapshot corresponding to the published article should be archived on Zenodo with a persistent DOI and referenced here once minted.

Please cite both the article and, where reusing code/data directly, the archived version (see `CITATION.cff`).

## License

- Source code (`AWH Simulation/AWH_Simulation_Final.py`): MIT License (see `LICENSE`).
- Data and model files (`Energyplus Models/`, `AWH Simulation/AWH_Output/`): CC BY 4.0 (see `LICENSE-DATA.txt`).
- TMY3 weather files (`*.epw`): U.S. government / NREL public-domain data (17 U.S.C. Section 105), not subject to copyright.
- Sorbent/device parameters used in the AWH model are literature-derived and cited in-script and in Supplementary Information Section S3.

## Contact

For questions about the models or data, please open a GitHub issue or contact the corresponding author.
