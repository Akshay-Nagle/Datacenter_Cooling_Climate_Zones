# Climate-Adaptive Data Center Cooling: Energy-Water Trade-offs and Waste-Heat-Driven Atmospheric Water Harvesting

This repository contains the EnergyPlus building energy models, the atmospheric water harvesting (AWH) simulation script, and the output data underlying the results, tables, and figures reported in:

> Nagle, A., Jiang, J., & Westerhoff, P. (2026). Climate-adaptive data center cooling across U.S. climate zones: energy-water trade-offs and waste-heat-driven atmospheric water harvesting. *Energy and Climate Change* (in review).

## Repository contents

```
.
├── README.md
├── LICENSE
├── CITATION.cff
├── energyplus_models/
│   ├── ACC/                     # Air-Cooled Chiller IDF files, 7 cities
│   ├── WCC/                     # Water-Cooled Chiller IDF files, 7 cities
│   └── Hybrid/                  # Hybrid IEC+DEC+WCC IDF files, 7 cities
├── weather_files/
│   └── README.md                # TMY3 file identifiers and WMO station numbers (see Supplementary Table S3.5); EPW files are third-party (NREL) and linked, not redistributed
├── awh_simulation/
│   ├── AWH_Simulation_Final.py  # Full runnable script: all city/scenario runs, both regeneration-temperature cases, plotting code
│   └── requirements.txt
├── outputs/
│   ├── energyplus_results/      # Per-city, per-system hourly/annual EnergyPlus output CSVs (PUE, WUE components)
│   └── awh_results/             # Per-city, per-scenario AWH output CSVs (60C and 80C regeneration)
└── figures/
    └── scripts/                # Plotting scripts used to generate main-text and SI figures
```

Cities modeled: Atlanta, Miami, Minneapolis, San Diego, Chicago, Denver, Phoenix (ASHRAE climate zones 1A-6A). Each city/system combination uses a standardized 10 MW reference facility; only the TMY3 weather file and design-day conditions vary between cities.

## Software and versions

- EnergyPlus 25.1.0
- Python 3.x (see `awh_simulation/requirements.txt` for package versions)

## How the files map to the paper

- Table S1/S2 parameters and IDF structure: `energyplus_models/`
- Equation 3 (main text) and Equations S1-S9 (SI): implemented in `awh_simulation/AWH_Simulation_Final.py`
- Figure 5 and Figures S1-S2: generated from `outputs/awh_results/` via `figures/scripts/`
- Weather file identifiers and WMO stations: `weather_files/README.md`, matching Supplementary Information Section S3.5

## Data availability and citation

This GitHub repository hosts the actively developed version of the code and data. A versioned snapshot corresponding to the published article should be archived on Zenodo with a persistent DOI (recommended before final submission) and referenced here once minted.

Please cite both the article and, where reusing code/data directly, the archived version (see `CITATION.cff`).

## License

Code is released under the MIT License (see `LICENSE`). Data and figures are released under CC-BY 4.0 unless noted otherwise. See individual folder README files for any third-party data (e.g., TMY3 weather files) subject to their original source's license/attribution terms.

## Contact

For questions about the models or data, please open a GitHub issue or contact the corresponding author.
