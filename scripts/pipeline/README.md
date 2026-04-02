# Pipeline Package

Modular Python package for the GHG sources enrichment pipeline. Called by `scripts/generate_ghg_dataset.py`.

## Structure

```
pipeline/
├── __init__.py      # Package exports
├── loaders.py       # Data loading (CSV, parquet, YAML, R-exported matrices)
├── enrichers.py     # Metadata enrichment (fuel, sector, activity, GWP, NAICS→BEA)
├── transform.py     # Normalization + commodity-form transformation
├── exporters.py     # Multi-format export (Excel, CSV, Parquet, JSON-LD, sunburst)
├── validators.py    # Data quality checks
└── utils.py         # Shared helpers (column naming, GHG Source ID, FlowSA version)
```

## Modules

### loaders.py (~890 lines, 18 functions)

Pure I/O — loads all external data sources with no business logic.

| Function | Purpose |
|---|---|
| `load_parquet_data()` | Load FlowBySector parquet from FlowSA cache |
| `load_generated_fbs_data()` | Load previously generated FBS from output dir |
| `load_metadata_mapping()` | EPA GHGI metadata CSV |
| `load_fuel_lookup()` | Fuel-by-table and fuel-by-term CSVs |
| `load_activity_sets_lookup()` | Activity set CSV |
| `load_naics_to_useeio_crosswalk()` | NAICS→USEEIO crosswalk (returns dict with 1:many lists) |
| `load_metasource_to_ghgsource_mapping()` | Activity categorization CSV (IPCC codes, categories) |
| `load_flowable_categorization()` | Gas→Gas Category mapping |
| `load_sector_classification()` | USEEIO sector names and categories |
| `load_ipcc_ar5_100_gwp()` | AR5 100-year GWP factors from IPCC parquet |
| `load_method_yaml()` | FlowSA method YAML |
| `extract_primary_activities_mapping()` | Parse activity sets from YAML content |
| `load_industry_output()` | Raw industry output (from R) |
| `load_commodity_output()` | CPI-adjusted commodity output (from R) |
| `load_market_share_matrix()` | V_n market share matrix (from R) |
| `load_naics_bea_allocation()` | NAICS→BEA allocation weights (from R) |
| `load_adjusted_output()` | CPI-adjusted industry output (from R) |
| `load_b_matrix()` | useeior B matrix for QC/QA (from R) |

### enrichers.py (~900 lines, 10 functions)

Core transformations — each function takes a DataFrame and returns an enriched copy.

| Function | Purpose |
|---|---|
| `enrich_with_metadata()` | Merge FlowSA MetaSources with EPA GHGI metadata |
| `enrich_with_primary_activities()` | Add PrimaryActivity from YAML-parsed activity sets |
| `enrich_with_activity_sets()` | Add Activity Set column |
| `enrich_with_useeio()` | Map NAICS→BEA codes; expand 1:many with allocation weights |
| `enrich_with_useeio_sector_name()` | Add human-readable sector names |
| `enrich_with_ghg_source_categories()` | Add IPCC codes, Activity Category/Subcategory/Type |
| `enrich_with_gas_category()` | Map Flowable to Gas Category |
| `enrich_with_ar5_100_gwp()` | Add GWP factors and compute kgCO₂e |
| `enrich_with_fuel()` | Match fuel types by table reference and term |
| `_prompt_continue()` | Interactive continue/stop prompt for unmatched data |

### transform.py (~460 lines, 3 functions)

Normalization and industry→commodity transformation.

| Function | Purpose |
|---|---|
| `calculate_contribution_by_sector()` | Compute % contribution of each source to sector total |
| `normalize_emissions_by_output()` | Divide emissions by CPI-adjusted industry output → kg/$ intensity |
| `transform_to_commodity_form()` | Pivot to intensity matrix, multiply by V_n, convert back to long form |

### exporters.py (~1,200 lines, 7 functions)

Output formatting for all distribution formats.

| Function | Purpose |
|---|---|
| `save_outputs()` | Main export orchestrator — Excel, CSV, Parquet, JSON-LD, sunburst JSON |
| `build_hierarchical_jsonld()` | Full emission-level JSON-LD |
| `build_ghg_source_classification_jsonld()` | Standalone GHG classification JSON-LD |
| `build_ghg_source_classification_csv()` | Standalone GHG classification CSV |
| `build_emission_events_jsonld()` | Event-based JSON-LD for RDF/knowledge graphs |
| `build_d3_sunburst_hierarchy()` | D3.js-optimized hierarchy for web visualization |
| `export_event_based_outputs()` | Write event-based JSON-LD and sunburst files |

### validators.py (~130 lines, 2 functions)

| Function | Purpose |
|---|---|
| `aggregate_to_reference_format()` | Roll up enriched data to FlowSA reference format for comparison |
| `validate_data()` | Check for nulls, negatives, tiny values, row counts |

### utils.py (~600 lines, 14 functions)

Shared helpers used across modules.

| Function | Purpose |
|---|---|
| `compute_ghg_source_id()` | 8-char hash of 9 classification columns |
| `get_emissions_intensity_col()` | Dynamic column name from config |
| `get_emissions_intensity_kgco2e_col()` | kgCO₂e intensity column name |
| `get_emissions_intensity_mtco2e_musd_col()` | MTCO₂e/million USD column name |
| `check_flowsa_version()` | Return installed FlowSA version |
| `validate_flowsa_version()` | Warn if FlowSA version doesn't match config |
| `filter_columns()` | Select/exclude columns for final output |
| `rename_and_create_columns()` | Rename FlowSA columns to human-readable names |
| `generate_event_id()` | UUID for emission event records |
| `build_emission_event_full()` | Build a single emission event dict |
| `_extract_meta_id()` | Parse MetaSources field |
| `_deduplicate_and_simplify_activities()` | Clean concatenated activity strings |
| `_parse_primary_activity_value()` | Parse PrimaryActivity field |
| `count_unique_valid()` | Count non-null unique values in a column |

## Pipeline flow

Called from `generate_ghg_dataset.py` in this order:

```
loaders.*              → Load all inputs (FBS parquet, CSVs, YAML, R matrices)
enrichers.*            → Enrich FBS with metadata, activities, fuels, sectors, GWP
utils.rename_and_create_columns()
utils.compute_ghg_source_id()
transform.calculate_contribution_by_sector()
transform.normalize_emissions_by_output()
transform.transform_to_commodity_form()   → Industry × V_n → Commodity
validators.validate_data()
exporters.save_outputs()                  → Excel, CSV, Parquet, JSON-LD, sunburst
```

## Design principles

- **loaders**: Pure I/O, no business logic
- **enrichers**: Return new DataFrames (original unchanged)
- **transform**: Numerical operations (normalization, matrix multiply)
- **exporters**: Output formatting, independent of enrichment
- **validators**: Data quality checks, separate from main workflow
- **utils**: Shared helpers used across modules