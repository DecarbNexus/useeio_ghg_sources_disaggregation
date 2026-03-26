# Scripts

## How to run

```
python scripts/generate_ghg_dataset.py
```

That's the only file you need to run. Everything else is called automatically.

## Folder structure

```
scripts/
  generate_ghg_dataset.py   ← entry point; orchestrates the full pipeline
  pipeline/                 ← internal steps; do not run these directly
    extract_metadata.py       step 1: parses EPA_GHGI.yaml → outputs/metadata/
    enrich_and_export.py      step 3: enriches FBS data and writes all output files
    enrichment/               submodules called by enrich_and_export.py
      loaders.py                load parquet, CSV, and YAML data sources
      enrichers.py              apply fuel, sector, activity, and GWP enrichments
      exporters.py              write Excel, CSV, Parquet, JSON-LD, and sunburst outputs
      validators.py             QC checks against reference data
      utils.py                  shared helpers
  tools/                    ← standalone utilities; run independently as needed
    clear_flowsa_cache.py     removes cached FlowByActivity/FlowBySector files
    install_flowsa_2.0.3.py   installs the pinned FlowSA version for reproducibility
```

## Pipeline steps

1. **Extract metadata** — reads the FlowSA `EPA_GHGI.yaml` package file and produces a flat
   CSV/YAML lookup of table IDs, chapters, and descriptions used in step 3.

2. **Generate FlowBySector** — calls `flowsa.FlowBySector.generateFlowBySector()` directly.
   Downloads FlowByActivity source data on first run and caches it in
   `AppData/Local/flowsa/`. You can skip this step with `--skip-fbs-generation` if a
   cached file already exists.

3. **Enrich and export** — joins the FBS data with fuel lookups, USEEIO sector mappings,
   IPCC activity categories, GWP factors, and the EPA GHGI metadata from step 1.
   Writes all output formats (Excel, CSV, Parquet, JSON-LD, sunburst JSON) to `outputs/`.

## Configuration

All model settings (model name, year, file paths) live in `config.py` at the project root.
Display labels and JSON-LD property names are in `terminology.py`, also at the project root.
