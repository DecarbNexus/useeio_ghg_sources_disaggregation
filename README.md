# USEEIO GHG Sources Disaggregation

This repository provides a reproducible workflow to disaggregate USEEIO sector direct emissions into their underlying greenhouse gas (GHG) sources. It enriches the greenhouse gas data output of flowsa, which allocates the US EPA's national greenhouse gas inventory (GHGI) data to NAICS sectors, with detailed metadata. This allows users to break down each sector's emissions by:

- **Activities**: Activity categories (combustion, processes, fugitives), subcategories, and specific activities
- **Greenhouse Gases**: CO2, CH4, N2O, HFCs, PFCs, SF6, NF3, and other fluorinated gases
- **Fuel Types**: Natural gas, coal, petroleum products, etc. (when applicable)
- **IPCC Categories**: Energy, Industrial Processes, Agriculture, Waste, etc.

The main outputs are Excel workbooks and CSVs with absolute emissions (kg, kgCO2e, MTCO2e) and relative contributions to sector totals.

## Just here for the data? (no coding required)

### Interactive visual

- Try the [interactive sunburst visualization](https://decarbnexus.github.io/useeio_ghg_sources_disaggregation/)
- Pick a sector and explore the composition of its scope 1 emissions

### Data tables

Download the latest data files from the [**Releases**](https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation/releases) section:

- **Excel** (comprehensive workbook): `GHG_national_2022_m2_DecarbNexus_industry.xlsx`
  - 📋 **Author_Info** - Attribution, license, citations
  - 📋 **Model_Specs** - Configuration, EPA GHGI source links
  - 📋 **Enriched** - Main emission data with full metadata
  - 📋 **Baseline** - Original FlowBySector for QC (optional)
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
- **Baseline CSV** provides the original FlowBySector data for quality checks
- **Excel tabs** include complete documentation: author info, model specs, reference data (classifications, crosswalks, matrices)
- **GHG Classification** files provide the unique activity/gas combinations as standalone datasets

### Use cases

This dataset helps you:
- Connect sector-level emissions to specific activities (e.g., "Natural Gas Combustion" vs "Aluminum Production")
- Identify emission hotspots by GHG source within each economic sector
- Map emissions to IPCC categories
- Conduct hybrid EEIO accounting under the GHG Protocol

## Quick start (to reproduce the data)

1) Install Python (≥ 3.9, ≤ 3.11) and ensure pip is available. **NOT Python 3.12+** (FlowSA v2.0.3 requires Python 3.9-3.11)
2) Clone or download this repository
3) Edit `config.py` (see below) if you want to change the model year or configuration options
4) Run the analysis:
   - Option A – script (recommended):
     ```bash
     python scripts/run_extraction.py
     ```
     This runs the full pipeline end-to-end, writing Excel/CSVs to the local `outputs/` folder
   - Option B – interactive: run the main enrichment script directly:
     ```bash
     python scripts/enrich_fbs_with_meta.py
     ```

5) Optional: First-time setup requires extracting EPA GHGI metadata:
   ```bash
   python scripts/extract_meta_from_EPA_GHGI.py
   ```
   (The `run_extraction.py` script handles this automatically)
   
   To extract legacy IPCC_Category and Subcategory fields (disabled by default):
   ```bash
   python scripts/extract_meta_from_EPA_GHGI.py --extract-categories
   ```

Artifacts will be saved under the local `outputs/` folder. For distribution, data files are packaged and published as GitHub Releases rather than committed to the repository.

**Note:** Sector F01000 (used goods) is automatically excluded from all outputs as it does not produce emissions.

## Requirements

This workflow installs packages on first run. At minimum, you'll need:

- Internet access (to download FlowSA data and install packages)
- Python 3.9-3.11 (NOT 3.12+) for FlowSA v2.0.3 compatibility
- Python packages: pandas, ruamel.yaml, pyarrow, openpyxl, flowsa
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

- `scripts/enrich_fbs_with_meta.py` – Main enrichment script; loads FlowBySector data, applies enrichments, and exports outputs
- `scripts/extract_meta_from_EPA_GHGI.py` – Extracts EPA GHGI table metadata from FlowSA YAML
- `scripts/run_extraction.py` – Run the full pipeline (extract metadata + enrich data)
- `scripts/clear_flowsa_cache.py` – Clear cached FlowByActivity files if data mismatch occurs
- `scripts/install_flowsa_2.0.3.py` – Install the correct FlowSA version for reproducibility
- `config.py` – User configuration (model, year, export options). Edit this
- `terminology.py` – Terminology and column mapping definitions
- `data/` – Lookup tables for fuel types, sector classifications, GWP factors, etc.
- `outputs/` – Local generation folder (not tracked in repository; data distributed via Releases)
- `local/` – Your scratch area; ignored by Git

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
   - "Fuel Consumed" to identify fuel-specific emissions (where applicable)

6) **Check the Baseline tab** (if included) to verify against original FlowBySector data
6) Check the "Baseline" tab (or baseline CSV) for the original FlowBySector data used as input

Deeper dive (optional columns):
- `Fuel Consumed`: Type of fuel (when applicable)
- `AR5-100 GWP`: IPCC AR5 100-year Global Warming Potential
- `US GHGI Table ID`: EPA GHGI source table
- `Attribution Sources`: How emissions were allocated to sectors

Additional reading and context:
- EPA's Supply Chain Emission Factors: https://www.epa.gov/climateleadership/supply-chain-emission-factors
- FlowSA documentation: https://github.com/USEPA/flowsa
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

## Beginner setup: getting Python running (no prior coding experience)

Windows (recommended simplest path):
1) Install Python 3.11: https://www.python.org/downloads/ (NOT 3.12+)
   - During installation, check "Add Python to PATH"
2) Download/clone this repository
3) Open PowerShell or Command Prompt in the repository folder
4) Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
5) Install FlowSA v2.0.3:
   ```bash
   python scripts/install_flowsa_2.0.3.py
   ```
6) Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
7) Run the pipeline:
   ```bash
   python scripts/run_extraction.py
   ```

macOS/Linux:
1) Install Python 3.11: https://www.python.org/downloads/
2) Open Terminal in the repository folder
3) Create a virtual environment:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```
4) Install FlowSA v2.0.3:
   ```bash
   python scripts/install_flowsa_2.0.3.py
   ```
5) Install dependencies:
   ```bash
   pip install -r requirements.txt
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
- FlowSA: https://github.com/USEPA/flowsa
- Supply Chain Emission Factors: https://github.com/USEPA/supply-chain-factors
- USEEIO: https://github.com/USEPA/useeior

Project by Damien Lieber @ [DecarbNexus LLC](https://decarbnexus.com)

## Pair this with sector disaggregation

This project focuses on disaggregating sector emissions into GHG sources. You can combine it with a companion workflow that disaggregates Scope 3 emissions by USEEIO sectors and tiers:

- Companion repository: https://github.com/DecarbNexus/useeio_sectors_disaggregation
- Data foundation: Both workflows leverage the US EPA's data ecosystem (FlowSA, USEEIO, Supply Chain Emission Factors)
- Pairing the two lets you go from "which sectors contribute to my Scope 3?" to "which GHG sources within those sectors?"

When used together, you can organize Scope 3 in the intuitive language of Scope 1 & 2 - by sector, tier, and source.

**Last Updated:** November 26, 2025  
**Repository:** https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation
