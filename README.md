# USEEIO GHG Sources Disaggregation

Reproducible workflow to disaggregate USEEIO sector direct emissions into their underlying greenhouse gas (GHG) sources. Enriches the [flowsa](https://github.com/cornerstone-data/flowsa) output — which allocates the US EPA national GHG inventory to NAICS sectors — with detailed metadata, enabling breakdowns by:

- **Activities**: Category, subcategory, and specific emission source
- **Greenhouse Gases**: CO₂, CH₄, N₂O, and fluorinated gases
- **Fuel Types**: Natural gas, coal, petroleum products, etc. (where applicable)
- **IPCC Categories**: Alphanumeric codes (e.g. 1A1, 2B3ai) down to the deepest available level
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
| `GHG_national_2022_m2_industry.jsonld` | JSON-LD | RDF-ready semantic format |

**Commodity form** (emissions reallocated to commodities via market-share matrix):
| File | Format | Description |
|---|---|---|
| `GHG_national_2022_m2_commodity.xlsx` | Excel | Includes B_Matrix and B_Matrix_Long tabs |
| `GHG_national_2022_m2_commodity.csv` | CSV | Flat commodity-form table |

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
- **Baseline** — Original FlowBySector for QC (F01000 excluded)
- **GHG_Classification** — Unique activity/gas combinations
- **Sector_Classification** — USEEIO sector definitions
- **NAICS_to_USEEIO** — Sector crosswalk
- **V_n_Matrix** — Market share matrix (commodity form only)
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

Everything else (model year, FlowSA version, file paths) is derived automatically from the version spec. Other options:

```python
EXPORT_INDUSTRY = True       # Export industry-form outputs
EXPORT_COMMODITY = True      # Export commodity-form outputs
INCLUDE_BASELINE_TAB = True  # Include original FlowBySector in Excel
EXPORT_BASELINE_CSV = False  # Export baseline as separate CSV
EXCLUDE_QC_COLUMNS = False   # Remove internal QC columns from final output
```

---

## Project structure

```
├── config.py                            # Configuration (set SEF_VERSION here)
├── terminology.py                       # Column naming definitions
├── data/
│   ├── SEF_v1.3.0/                      # R-exported reference data for v1.3.0
│   │   ├── activity_categorization.csv  # IPCC codes + activity classification lookup
│   │   ├── adjusted_output.csv          # CPI-adjusted industry output (from R)
│   │   ├── adjusted_commodity_output.csv
│   │   ├── naics_bea_allocation.csv     # NAICS→BEA allocation weights (from R)
│   │   ├── B_matrix.csv                 # useeior B matrix for QC/QA (from R)
│   │   ├── V_n.csv                      # Market share matrix (from R)
│   │   ├── naics_to_useeio_crosswalk.csv
│   │   └── sector_classification.csv
│   ├── SEF_v1.4.0/                      # Same structure for v1.4.0
│   ├── flowable_categorization.csv      # Gas → Gas Category mapping
│   ├── ListOfFuelsByTerm.csv            # Fuel type lookup
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

## How to use the outputs

1. **Open the Excel workbook** from Releases — start with **Author_Info** for attribution requirements, then **Model_Specs** for data provenance.

2. **Key columns in the Enriched sheet:**
   | Column | Description |
   |---|---|
   | `GHG Source ID` | 8-char hash — foreign key into ghg_source_classification |
   | `USEEIO Sector Name` | Human-readable sector (e.g. "Oilseed farming") |
   | `Activity Category` | High-level source type (e.g. "Stationary Combustion") |
   | `IPCC Category Code` | Alphanumeric IPCC code (e.g. "1A1", "2B3ai") |
   | `Gas` | GHG species (e.g. "Carbon dioxide", "Methane") |
   | `Emissions (MTCO2e)` | Absolute emissions in metric tons CO₂e |
   | `Emissions Intensity (MTCO2e/million_USD_2022)` | Intensity per million USD output |
   | `Contribution to USEEIO Sector's Scope 1 (%)` | Share of sector total |

3. **Disaggregate your sector emissions:** multiply a sector's total Scope 1 by `Contribution to USEEIO Sector's Scope 1 (%)` to identify the largest emission sources.

4. **JOIN with ghg_source_classification** on `GHG Source ID` to pull in the full activity hierarchy without duplicating classification columns in your working file.

---

## Limitations & planned development

**Known limitations:**
- Requires FlowSA v2.0.3 (SEF v1.3.0) or v2.1.0 (SEF v1.4.0) for reproducibility. Cached FlowByActivity files from other versions can cause mismatches.
- Activities and fuels with multiple values separated by ` | ` are not yet disaggregated to individual records.

**Planned features:**
- Disaggregate concatenated activities/fuels by tracing back to original EPA GHGI tables
- Multi-country support for other UNFCCC national inventories
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
> DecarbNexus (2026). *U.S. Greenhouse Gas Emissions by USEEIO Sector — Disaggregated EPA GHGI Data*. https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation

Also acknowledge upstream sources: EPA GHGI (public domain), FlowSA v2.0.3 (MIT, U.S. EPA), USEEIOR (MIT, U.S. EPA). See `CITATION.md` in Releases for BibTeX entries.

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

**Last Updated:** March 2026


- **Activities**: Activity categories (Electric Power Generation, Fuel Combustion, Process & Fugitive Gases), subcategories, and specific activities
- **Greenhouse Gases**: CO2, CH4, N2O, and fluorinated gases
- **Fuel Types**: Natural gas, coal, petroleum products, etc. (when applicable)
- **IPCC Categories**: Energy, Industrial Processes, Agriculture, Waste, etc.

The main outputs are Excel workbooks and CSVs with absolute emissions (kg, kgCO2e, MTCO2e) and relative contributions to sector totals.

## Just here for the data? (no coding required)

### Interactive visual

- Try the interactive sunburst visualization: https://open.decarbnexus.com/useeio_ghg_sources_disaggregation/
- Pick a sector and explore the composition of its scope 1 emissions

### Data tables

Download the latest data files from the [**Releases**](https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation/releases) section:

- **Excel** (comprehensive workbook): `GHG_national_2022_m2_DecarbNexus_industry.xlsx`
  - 📋 **Author_Info** - Attribution, license, citations
  - 📋 **Model_Specs** - Configuration, EPA GHGI source links
  - 📋 **Enriched** - Main emission data with full metadata
  - 📋 **Baseline** - Original FlowBySector for QC, F01000 excluded (optional)
  - 📋 **GHG_Classification** - Activity hierarchy (unique combinations)
  - 📋 **Sector_Classification** - USEEIO sector definitions
  - 📋 **NAICS_to_USEEIO** - Sector crosswalk mapping
  - 📋 **V_n_Matrix** - Market share matrix (403×403)
  - 📋 **x_Vector** - Industry output in USD

- **CSV** (flat tables):
  - Main emissions: `GHG_national_2022_m2_DecarbNexus_industry.csv`
  - Baseline FlowBySector: `GHG_national_2022_m2_DecarbNexus_industry_baseline.csv`

- **Parquet** (columnar, data science): `GHG_national_2022_m2_DecarbNexus_industry.parquet`

- **JSON** (hierarchical): `GHG_national_2022_m2_DecarbNexus_industry_sunburst.json`

- **JSON-LD** (RDF-ready): `GHG_national_2022_m2_DecarbNexus_industry.jsonld`

- **GHG Classification** (separate folder):
  - CSV format: `GHG_national_2022_m2_ghg_source_classification.csv`
  - JSON-LD format: `GHG_national_2022_m2_ghg_source_classification.jsonld`

- **License & Attribution**:
  - `LICENSE.txt` - CC BY 4.0 license for data
  - `THIRD_PARTY_LICENSES.txt` - MIT licenses (FlowSA, USEEIOR)
  - `CITATION.md` - Complete citation guide with BibTeX

Open Excel files in your spreadsheet tool or explore the enriched data with full GHG source metadata. All reference data and classifications are included for complete reproducibility.

#### Format guide

- **Excel/CSV**: Flat tables, best for spreadsheet users and simple imports. Excel includes comprehensive metadata tabs with attribution, model specs, and all reference data.
- **Parquet**: Snappy-compressed columnar format; optimized for pandas, Polars, DuckDB, Apache Spark. ~10× faster reads than CSV
- **JSON**: Nested hierarchy (sector > category > gas); ideal for web APIs, JavaScript/Python data science pipelines
- **JSON-LD**: RDF-ready with `@context` vocabulary; can be ingested into triple stores (Apache Jena, RDF4J) or converted to Turtle/N-Triples for knowledge graphs

What's inside (high level):
- **Enriched emissions** show how each USEEIO sector's emissions break down by GHG source, activity, and gas
- **"Absolute" columns** are emissions in kg, kgCO2e, or MTCO2e for the specified model year (typically 2022)
- **"Relative contribution"** shows the percentage split across all GHG sources for a given sector (sums to 100%)
- **"Emissions Intensity"** shows kgCO2e per USD of sector output for the specified IO year
- **Baseline CSV** provides the original FlowBySector data for quality checks (F01000 excluded)
- **Excel tabs** include complete documentation: author info, model specs, reference data (classifications, crosswalks, matrices)
- **GHG Classification** files provide the unique activity/gas combinations as standalone datasets

### Use cases

This dataset helps you:
- Connect sector-level emissions to specific activities (e.g., natural gas combustion)
- Identify emission hotspots by GHG source within each economic sector
- Map emissions to IPCC categories
- Conduct hybrid EEIO accounting under the GHG Protocol

## Quick start (to reproduce the data)

1) Install Python (≥ 3.9, ≤ 3.11) and ensure pip is available. **NOT Python 3.12+** (FlowSA v2.0.3 requires Python 3.9-3.11)
2) Install R (≥ 4.1) — needed once to export reference data from useeior
3) Clone or download this repository
4) Edit `config.py` (see below) if you want to change the model year or configuration options
5) **One-time R setup** — export reference matrices from useeior:
   ```bash
   Rscript scripts/setup/export_reference_data.R
   ```
   This builds the `USEEIOv2.2.22-GHG` model in R and exports five CSV files to `data/`
   (CPI-adjusted output, NAICS→BEA allocation weights, B matrix for validation, etc.).
   See [scripts/setup/README.md](scripts/setup/README.md) for details.

6) Run the Python pipeline:
   ```bash
   python scripts/generate_ghg_dataset.py
   ```
   This runs the full pipeline end-to-end:
   - Extracts EPA GHGI metadata from FlowSA YAML
   - Loads FlowBySector data and enriches with metadata, activities, fuels, GWP, sectors
   - Expands 1:many NAICS→BEA mappings using allocation weights from R
   - Normalizes emissions by CPI-adjusted industry output (denominator from R)
   - Transforms to commodity form via matrix multiply (`B_industry @ V_n`)
   - Validates commodity-form results against useeior's B matrix
   - Writes industry-form and commodity-form outputs to `outputs/`
   - Generates a QC/QA workbook (`outputs/QCQA.xlsx`) comparing against the B matrix

Artifacts will be saved under the local `outputs/` folder. For distribution, data files are packaged and published as GitHub Releases rather than committed to the repository.

**Note:** Sector F01000 (Used/Secondhand Goods) is excluded from all outputs — including the enriched data and the baseline FlowBySector — because it is a final demand sector that does not produce emissions and is not used in USEEIO input-output modeling or Scope 3 emission factor (SEF) calculations.

## Requirements

This workflow installs packages on first run. At minimum, you'll need:

- Internet access (to download FlowSA data and install packages)
- **R ≥ 4.1** (one-time setup to export reference data from useeior; see [scripts/setup/README.md](scripts/setup/README.md))
- **Python 3.9-3.11** (NOT 3.12+) for FlowSA v2.0.3 compatibility
- Python packages: pandas, numpy, ruamel.yaml, pyarrow, openpyxl, flowsa
- FlowSA v2.0.3 (install via: `python scripts/install_flowsa_2.0.3.py`)

The scripts will download EPA GHGI data from FlowSA's AWS server on first run (~500 MB cached data).

## Configuration (`config.py`)

Example in `config.py`:

```python
MODELNAME = "GHG_national_2022_m2_DecarbNexus"
MODEL_YEAR = 2022
FILE_NAME_PARQUET = "GHG_national_2022_m2_v2.0.3_1cb504c.parquet"

# Export options
EXPORT_INDUSTRY = True   # Export industry/sector-based outputs
EXPORT_COMMODITY = True  # Export commodity-based outputs (requires additional data)
INCLUDE_BASELINE_TAB = True  # Include original FlowBySector as "Baseline" tab in Excel
EXPORT_BASELINE_CSV = False   # Export baseline as separate CSV

# Quality control
EXCLUDE_QC_COLUMNS = False  # Set to True to exclude QC columns from final output
```

- `MODELNAME`: FlowSA model to process (e.g., "GHG_national_2022_m2_DecarbNexus")
- `MODEL_YEAR`: Year for emissions intensity column naming
- `EXPORT_INDUSTRY`: Whether to export industry/sector-based perspective
- `EXPORT_COMMODITY`: Whether to export commodity-based perspective (requires Use and Make tables)
- `INCLUDE_BASELINE_TAB`: Whether to include baseline FlowBySector data in Excel output
- `EXPORT_BASELINE_CSV`: Whether to export baseline as separate CSV file

## Project structure

```
Flowsa_extract_GHG_sources/
├── config.py                          # User configuration (model, year, export options)
├── terminology.py                     # Terminology and column mapping definitions
├── data/                              # Lookup tables and R-exported reference data
│   ├── adjusted_output.csv            # CPI-adjusted industry output (from R)
│   ├── naics_bea_allocation.csv       # NAICS→BEA allocation weights (from R)
│   ├── B_matrix.csv                   # useeior B matrix for QC/QA (from R)
│   ├── V_n.csv                        # Market share matrix (from R)
│   ├── q.csv                          # Commodity output vector
│   ├── NAICS_to_USEEIO_crosswalk.csv  # NAICS→USEEIO sector mapping
│   └── ...                            # Fuel types, sector classifications, etc.
├── scripts/
│   ├── generate_ghg_dataset.py        # Main pipeline script (run this)
│   ├── setup/
│   │   └── export_reference_data.R    # One-time R export of useeior matrices
│   ├── pipeline/                      # Modular Python package
│   │   ├── __init__.py
│   │   ├── loaders.py                 # Data loading (parquet, CSV, YAML)
│   │   ├── enrichers.py               # Metadata enrichment functions
│   │   ├── transform.py               # Normalization + commodity transform
│   │   ├── exporters.py               # Output formatting (Excel, CSV, JSON-LD)
│   │   ├── validators.py              # Data quality checks
│   │   └── utils.py                   # Shared utility functions
│   └── tools/                         # Utility scripts
├── outputs/                           # Generated files (not tracked; via Releases)
│   ├── QCQA.xlsx                      # QC/QA workbook (B matrix comparison)
│   └── ...                            # Industry + commodity form outputs
├── docs/                              # Documentation
└── local/                             # Scratch area (ignored by Git)
```

### Key scripts

- `scripts/generate_ghg_dataset.py` – **Main pipeline script**; runs the full workflow from data loading through enrichment, commodity transformation, and export
- `scripts/setup/export_reference_data.R` – One-time R setup; exports CPI-adjusted output, allocation weights, and B matrix from useeior
- `scripts/pipeline/` – Modular Python package with separate modules for loading, enrichment, transformation, export, and validation
- `config.py` – User configuration; edit model name, year, export options, and file paths

## How to use the outputs (practical guide)

1) **Download and open the Excel file** from the [Releases](https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation/releases) section
   - Start with **Author_Info** tab for licensing and attribution requirements
   - Check **Model_Specs** tab for model configuration and EPA GHGI source links
   
2) **Explore the enriched data** (Enriched tab) with columns like:
   - `USEEIO Sector Name`: Human-readable sector name (e.g., "Oilseed farming")
   - `Activity Category`: High-level GHG source type (e.g., "Stationary Combustion")
   - `Activity`: Specific emission source (e.g., "Natural Gas Combustion")
   - `Gas`: Greenhouse gas species (e.g., "Carbon dioxide", "Methane")
   - `Emissions (MTCO2e)`: Emissions in metric tons CO2 equivalent
   - `Contribution to USEEIO Sector's Scope 1 (%)`: Percentage of sector's total emissions
   
3) **Use "Relative Contribution"** to disaggregate your sector emissions: multiply your sector's total emissions by the "Contribution to USEEIO Sector's Scope 1 (%)" values to identify the largest emission sources

4) **Reference data tabs** provide complete context:
   - **GHG_Classification**: Unique activity/gas combinations (standalone classification)
   - **Sector_Classification**: USEEIO sector definitions
   - **NAICS_to_USEEIO**: Crosswalk for mapping NAICS codes to USEEIO sectors
   - **V_n_Matrix**: Market share matrix for commodity transformation
   - **x_Vector**: Industry output for intensity calculations

5) **Use categorization fields** for analysis:
   - "Activity Category" to distinguish combustion vs. process vs. fugitive emissions
   - "IPCC/UNFCCC Category" for international reporting categories
   - "Fuel" to identify fuel-specific emissions (where applicable)

6) **Check the Baseline tab** (if included) to verify against original FlowBySector data
6) Check the "Baseline" tab (or baseline CSV) for the original FlowBySector data used as input

Deeper dive (optional columns):
- `Fuel`: Type of fuel (when applicable)
- `AR5-100 GWP`: IPCC AR5 100-year Global Warming Potential
- `US GHGI Table ID`: EPA GHGI source table
- `Attribution Sources`: How emissions were allocated to sectors

Additional reading and context:
- EPA's Supply Chain Emission Factors: https://www.epa.gov/climateleadership/supply-chain-emission-factors
- FlowSA documentation: https://github.com/cornerstone-data/flowsa
- EPA GHGI: https://www.epa.gov/ghgemissions/inventory-us-greenhouse-gas-emissions-and-sinks

## Limitations & planned development

**Known limitations:**

1) **FlowSA version dependency**
   - This workflow requires FlowSA v2.0.3 for reproducibility (matches Supply Chain Emission Factors v1.3.0)
   - Using different FlowSA versions may produce different results (different row counts, missing sources)
   - Cached FlowByActivity files from other versions can cause data mismatches. Run `python scripts/clear_flowsa_cache.py --activity-only` to fix

2) **Planned features**
   - **Disaggregate concatenated activities and fuels**: When multiple activities or fuels are present (separated by ` | `), disaggregate these by going back to the original tables in the US EPA GHGI to create separate emission records for each activity/fuel combination
   - **Multi-country support**: Extend this workflow to process other countries' national GHG inventories submitted to the UNFCCC
   - **Custom aggregation hierarchies**: Support for user-defined grouping and rollup structures

Advanced users can extend the enrichment pipeline by modifying `scripts/enrich_fbs_with_meta.py` or adding new lookup tables in `data/`.

We welcome feedback on which features to prioritize for future releases. Please open a thread in the repository's Discussions to share your thoughts on what would be most useful.

## Beginner setup: getting Python and R running (no prior coding experience)

Windows (recommended simplest path):
1) Install Python 3.11: https://www.python.org/downloads/ (NOT 3.12+)
   - During installation, check "Add Python to PATH"
2) Install R ≥ 4.1: https://cran.r-project.org/bin/windows/base/
   - During installation, check "Add R to PATH"
3) Download/clone this repository
4) Open PowerShell or Command Prompt in the repository folder
5) Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
6) Install FlowSA v2.0.3:
   ```bash
   python scripts/install_flowsa_2.0.3.py
   ```
7) Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
8) Run the one-time R setup (exports useeior reference data):
   ```bash
   Rscript scripts/setup/export_reference_data.R
   ```
9) Run the pipeline:
   ```bash
   python scripts/generate_ghg_dataset.py
   ```

macOS/Linux:
1) Install Python 3.11: https://www.python.org/downloads/
2) Install R ≥ 4.1: https://cran.r-project.org/
3) Open Terminal in the repository folder
4) Create a virtual environment:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```
5) Install FlowSA v2.0.3:
   ```bash
   python scripts/install_flowsa_2.0.3.py
   ```
6) Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
7) Run the one-time R setup:
   ```bash
   Rscript scripts/setup/export_reference_data.R
   ```
6) Run the pipeline:
   ```bash
   python scripts/run_extraction.py
   ```

If you don't want to install anything, you can still download the pre-built files directly from the [Releases](https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation/releases) section.

## Troubleshooting

- **ModuleNotFoundError: No module named 'flowsa'**: Install FlowSA: `python scripts/install_flowsa_2.0.3.py`
- **Permission error saving Excel**: Close the Excel file and run again
- **Wrong Python version**: See `docs/PYTHON_VERSION_FIX.md` for how to install Python 3.11
- **Network/timeout errors**: Check connectivity and re-run (FlowSA downloads data from AWS)
- **Package install issues**: Ensure pip is up to date: `python -m pip install --upgrade pip`

## Feedback, questions, and feature requests

We're learning with you. Please use the repository's Discussions tab to ask questions, request features, or share how you're using the data.

Peer review status: We aim to have this workflow and its outputs peer-reviewed over the next few months. If you're interested in participating in the review or testing the methods on your data, please open a Discussion or contact us via the repository.

## License and Attribution

### This Project

- **Code**: MIT License (see `LICENSE` in repository root)
- **Output Data**: CC BY 4.0 (see `outputs/LICENSE.txt`)
  - All files under `outputs/` folder
  - Data attached to GitHub releases
  - Creative Commons Attribution 4.0: https://creativecommons.org/licenses/by/4.0/

### Required Attribution

When using the enriched data from this project, please cite:

**DecarbNexus (2025). U.S. Greenhouse Gas Emissions by USEEIO Sector - Enriched EPA GHGI Data. https://github.com/damienlieber-dnexus/flowsa-ghg-extraction**

You must also acknowledge the original data sources:
- EPA GHGI 2022 (U.S. EPA, public domain)
- FlowSA v2.0.3 (U.S. EPA, MIT License)
- USEEIOR (U.S. EPA, MIT License)

See `outputs/CITATION.md` for complete citation information and BibTeX entries.

### Third-Party Dependencies

This project uses the following open-source software:

- **FlowSA** (v2.0.3): MIT License - Copyright (c) 2022 U.S. EPA
- **USEEIOR**: MIT License - Copyright (c) 2021 U.S. EPA
- **EPA GHGI Data**: Public domain (U.S. federal government work)
- **BEA Input-Output Data**: Public domain (U.S. federal government work)

Full license texts and compliance information: `outputs/THIRD_PARTY_LICENSES.txt`

### License Compliance

✓ **MIT License Compliance** (FlowSA & USEEIOR):
- Copyright notices preserved in THIRD_PARTY_LICENSES.txt
- Permission granted for commercial and non-commercial use
- Attribution provided in all documentation and outputs

✓ **CC BY 4.0 Compliance** (Output Data):
- Attribution information in every output file
- Changes clearly indicated in documentation
- License URL provided in all distribution materials

All license requirements are fully satisfied. See licensing files in `outputs/` folder for details.

## Credits and acknowledgement

Huge thanks to the USEPA teams whose work powers this project:
- FlowSA: https://github.com/cornerstone-data/flowsa
- Supply Chain Emission Factors: https://github.com/cornerstone-data/supply-chain-factors
- USEEIO: https://github.com/cornerstone-data/useeior

Project by Damien Lieber @ [DecarbNexus LLC](https://decarbnexus.com)

## Pair this with sector disaggregation

This project focuses on disaggregating sector emissions into GHG sources. You can combine it with a companion workflow that disaggregates Scope 3 emissions by USEEIO sectors and tiers:

- Companion repository: https://github.com/DecarbNexus/useeio_sectors_disaggregation
- Data foundation: Both workflows leverage the US EPA's data ecosystem (FlowSA, USEEIO, Supply Chain Emission Factors)
- Pairing the two lets you go from "which sectors contribute to my Scope 3?" to "which GHG sources within those sectors?"

When used together, you can organize Scope 3 in the intuitive language of Scope 1 & 2 - by sector, tier, and source.

**Last Updated:** November 26, 2025  
**Repository:** https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation
