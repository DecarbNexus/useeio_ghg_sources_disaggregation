# USEEIO GHG Sources Disaggregation

Reproducible workflow to disaggregate USEEIO sector direct emissions into their underlying greenhouse gas (GHG) sources. Enriches the [flowsa](https://github.com/cornerstone-data/flowsa) output — which allocates the US EPA national GHG inventory to NAICS sectors — with detailed metadata, enabling breakdowns by:

- **Activities**: Emitting activities organized by category, subcategory, type, and activities
- **Greenhouse Gases**: CO₂, CH₄, N₂O, and fluorinated gases
- **Fuel Types**: Natural gas, coal, petroleum products, etc. (where applicable)
- **IPCC Categories**: Energy, Industrial Processes, Agriculture, Waste
- **Emissions Intensity**: kgCO₂e and MTCO₂e per USD of sector output

Main outputs are industry-form and commodity-form CSVs and Excel workbooks with absolute emissions (kg, kgCO₂e, MTCO₂e), intensity values, and percentage contributions to sector totals.

Supports **EPA Supply Chain Emission Factors v1.3.0** (2022 model year) and **v1.4.0** (2023 model year). Switch versions by setting `SEF_VERSION` in `config.py`.

---

## Just here for the data? (no coding required)

### Interactive visualization
Explore sector emissions interactively: https://open.decarbnexus.com/useeio_ghg_sources_disaggregation/

### Download data files
All data files are published in the [**Releases**](https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation/releases) section.

**Industry form** (emissions allocated to economic sectors):
| File | Format | Description |
|---|---|---|
| `GHG_national_2022_m2_industry.xlsx` | Excel | Comprehensive workbook with all reference tabs |
| `GHG_national_2022_m2_industry.csv` | CSV | Main enriched emissions table |
| `GHG_national_2022_m2_industry.parquet` | Parquet | Columnar format for data science |

**Commodity form** (emissions reallocated to commodities via market-share matrix):
| File | Format | Description |
|---|---|---|
| `GHG_national_2022_m2_commodity.xlsx` | Excel | Includes B_Matrix and B_Matrix_Long tabs |
| `GHG_national_2022_m2_commodity.csv` | CSV | Flat commodity-form table |
| `GHG_national_2022_m2_commodity.parquet` | Parquet | Columnar format for data science |

**GHG Source Classification** (standalone lookup table):
| File | Format | Description |
|---|---|---|
| `GHG_national_2022_m2_ghg_source_classification.csv` | CSV | Unique emission source combinations with `GHG Source ID` |
| `GHG_national_2022_m2_ghg_source_classification.jsonld` | JSON-LD | Linked data version |

**Attribution**: `LICENSE.txt`, `THIRD_PARTY_LICENSES.txt`, `CITATION.md`

#### Linking the tables
Each row in the industry and commodity CSVs carries a `GHG Source ID` — a stable 8-character hash of the 9 classification columns (Activity Category → Gas). This is the foreign key into `ghg_source_classification.csv`. Use it to JOIN or VLOOKUP the full emission source metadata without duplicating those columns in your analysis.

#### Excel workbook tabs
- **Author_Info** — Attribution, license, citations
- **Model_Specs** — Configuration and EPA GHGI source links
- **Enriched** — Main emission data with full metadata
- **Baseline** — Original FlowBySector for QC (F01000 excluded) (industry form only)
- **GHG_Classification** — Unique activity/gas combinations
- **Sector_Classification** — USEEIO sector definitions
- **NAICS_to_USEEIO** — Sector crosswalk
- **V_n_Matrix** — Market share matrix (industry form only)
- **B_Matrix / B_Matrix_Long** — useeior B matrix in wide and long form (commodity form only)

---

## Quick start (reproduce the data)

**Prerequisites:** Python 3.9–3.11 (not 3.12+), R ≥ 4.1, pip

```bash
# 1. Clone and enter the repository
git clone https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation.git
cd useeio_ghg_sources_disaggregation

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 3. Install dependencies (includes FlowSA)
python scripts/tools/install_flowsa.py
pip install -r requirements.txt

# 4. One-time R export of useeior reference matrices
Rscript scripts/setup/export_reference_data.R

# 5. Run the pipeline
python scripts/generate_ghg_dataset.py
```

Outputs are written to `outputs/SEF_v1.3.0/` (or `SEF_v1.4.0/` depending on `SEF_VERSION` in `config.py`).

---

## Configuration (`config.py`)

The single value you need to change to switch between SEF releases:

```python
SEF_VERSION = "v1.3.0"   # or "v1.4.0"
```

Everything else (model year, FlowSA version, file paths) is derived automatically from the version spec.

> **When upgrading to a new SEF version**, review and update the three lookup files before running:
> - `data/SEF_vX.Y.Z/activity_categorization.csv` — EPA GHGI inventory table references and `MetaSources` keys change between versions; add or remove rows to match.
> - `data/SEF_vX.Y.Z/ListOfFuelsByMetaSource.csv` — same table references appear here; verify each row still maps to a valid MetaSources key in the new FlowSA output.
> - `data/ListOfFuelsByTerm.csv` — term-based fuel lookup; check that any new `PrimaryActivity` strings introduced in the new version are covered.
> - `data/flowable_categorization.csv` — check that any new `Flowable` introduced in the new version are categorized.
>
> The pipeline saves `unmatched_activity_categorization.xlsx` and `unmatched_fuel.xlsx` under `outputs/SEF_vX.Y.Z/` after each run, showing exactly which dataset rows had no match and which CSV rows were never used — use these to guide your edits. Other options:

---

## Project structure

```
├── config.py                            # Configuration (set SEF_VERSION here)
├── terminology.py                       # Column naming definitions
├── data/
│   ├── SEF_v1.3.0/                      # R-exported reference data for v1.3.0
│   │   ├── activity_categorization.csv  # IPCC codes + activity classification lookup
│   │   ├── cpi_adjusted_industry_output.csv   # CPI-adjusted industry output (from R)
│   │   ├── cpi_adjusted_commodity_output.csv  # CPI-adjusted commodity output (from R)
│   │   ├── raw_industry_output_2022.csv       # Raw 2022 industry output (reference)
│   │   ├── naics_bea_allocation.csv     # NAICS→BEA allocation weights (from R)
│   │   ├── B_matrix.csv                 # useeior B matrix for QC/QA (from R)
│   │   ├── V_n.csv                      # Market share matrix (from R)
│   │   ├── naics_to_useeio_crosswalk.csv
│   │   └── sector_classification.csv
│   ├── SEF_v1.4.0/                      # Same structure for v1.4.0
│   │   └── ListOfFuelsByMetaSource.csv  # Table-reference → Fuel lookup (review each version upgrade)
│   ├── flowable_categorization.csv      # Gas → Gas Category mapping
│   ├── ListOfFuelsByTerm.csv            # Term → Fuel lookup (review each version upgrade)
│   └── IPCC_v1.1.1_27ba917.parquet     # IPCC AR5-100 GWP factors
├── scripts/
│   ├── generate_ghg_dataset.py          # Main pipeline entry point
│   ├── setup/
│   │   ├── export_reference_data.R      # One-time R export of useeior matrices
│   │   └── README.md
│   ├── pipeline/                        # Modular pipeline package
│   │   ├── loaders.py                   # Data loading
│   │   ├── enrichers.py                 # Metadata enrichment
│   │   ├── transform.py                 # Normalization + commodity transform
│   │   ├── exporters.py                 # Excel, CSV, JSON-LD export
│   │   ├── validators.py                # Data quality checks
│   │   └── utils.py                     # Shared utilities (incl. compute_ghg_source_id)
│   └── tools/
│       └── install_flowsa.py            # FlowSA installer
├── outputs/                             # Generated outputs (gitignored; via Releases)
├── docs/                                # Documentation
└── local/                               # Scratch area (gitignored)
```

---

## Limitations & planned development

**Known limitations:**
- Activities and fuels with multiple values separated by ` | ` are not yet disaggregated to individual records.

**Planned features:**
- Disaggregate concatenated activities/fuels by tracing back to original EPA GHGI tables
- Custom aggregation hierarchies

Feedback welcome — open a thread in [Discussions](https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation/discussions).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'flowsa'` | `python scripts/tools/install_flowsa.py` |
| Permission error saving Excel | Close the open Excel file and re-run |
| Wrong Python version (3.12+) | Install Python 3.11 from https://www.python.org/downloads/ |
| Network/timeout errors | Re-run; FlowSA downloads ~500 MB from AWS on first run |
| Cached data mismatch | Clear FlowByActivity cache and re-run |

---

## License and attribution

- **Code**: MIT License (`LICENSE`)
- **Output data**: CC BY 4.0 (`outputs/LICENSE.txt`)

**Cite as:**
> DecarbNexus (2026). *USEEIO GHG Sources Disaggregation*. https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation

Also acknowledge upstream sources: EPA GHGI (public domain), FlowSA (MIT, U.S. EPA, Cornerstone), USEEIOR (MIT, U.S. EPA, Cornerstone).

---

## Credits

Built on the US EPA open-science ecosystem:
- [FlowSA](https://github.com/cornerstone-data/flowsa) — GHG inventory → NAICS sector allocation
- [USEEIOR](https://github.com/cornerstone-data/useeior) — US Environmentally Extended I-O model
- [Supply Chain Emission Factors](https://github.com/cornerstone-data/supply-chain-factors)

Project by Damien Lieber @ [DecarbNexus LLC](https://decarbnexus.com)

## Pair with sector disaggregation

To go from "which sectors drive my Scope 3?" to "which GHG sources within those sectors?", pair this with the companion repository:

- [useeio_sectors_disaggregation](https://github.com/DecarbNexus/useeio_sectors_disaggregation) — disaggregates Scope 3 by USEEIO sector and tier

---

**Last Updated:** April 2026