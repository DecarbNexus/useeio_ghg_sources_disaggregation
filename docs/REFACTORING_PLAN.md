# Refactoring Plan: Modularizing enrich_fbs_with_meta.py

**Date**: November 24, 2025  
**Current State**: Single file with 4,107 lines and 91 functions  
**Proposed State**: Modular structure with 10 focused files  
**Estimated Effort**: 4-8 hours

---

## Motivation

The main enrichment script has grown to over 4,000 lines, making it:
- Difficult to navigate and understand
- Harder to test individual components
- Challenging to maintain and debug
- Less reusable across projects

Refactoring into modules will improve:
- **Code organization**: Logical grouping by functionality
- **Testability**: Easier to write unit tests for modules
- **Maintainability**: Changes isolated to specific modules
- **Reusability**: Components can be imported independently
- **Collaboration**: Multiple developers can work on different modules

---

## Proposed Module Structure

### Directory Layout
```
scripts/
├── enrich_fbs_with_meta.py          # Main orchestration (reduced to ~300 lines)
└── enrichment/
    ├── __init__.py                  # Package initialization
    ├── data_loading.py              # ~400 lines - Load parquet, YAML, CSV files
    ├── fuel_enrichment.py           # ~200 lines - Fuel extraction and mapping
    ├── sector_enrichment.py         # ~300 lines - NAICS/USEEIO sector mapping
    ├── activity_enrichment.py       # ~500 lines - Activity categorization
    ├── gwp_enrichment.py            # ~300 lines - GWP and emissions calculations
    ├── metadata_enrichment.py       # ~200 lines - EPA GHGI metadata enrichment
    ├── commodity.py                 # ~500 lines - Commodity transformation
    ├── jsonld_export.py             # ~800 lines - JSON-LD and D3 exports
    ├── validation.py                # ~300 lines - Data validation and comparison
    └── utils.py                     # ~100 lines - Shared utilities
```

---

## Module Descriptions

### 1. `data_loading.py` (~400 lines)
**Purpose**: Load all external data sources

**Functions to migrate**:
- `load_parquet_data()` - Load FlowBySector parquet files
- `load_generated_fbs_data()` - Load pre-generated FBS data
- `load_metadata_mapping()` - Load EPA GHGI metadata CSV
- `load_fuel_lookup()` - Load fuel lookup tables
- `load_naics_to_useeio_crosswalk()` - Load NAICS-USEEIO crosswalk
- `load_metasource_to_ghgsource_mapping()` - Load activity categorization
- `load_flowable_categorization()` - Load gas categorization
- `load_ipcc_ar5_100_gwp()` - Load GWP factors
- `load_sector_classification()` - Load USEEIO sector names
- `load_method_yaml()` - Load FlowSA method YAML
- `extract_primaryactivity_info()` - Parse YAML for activity info
- `extract_attribution_sources()` - Parse attribution from YAML

**Dependencies**: `pandas`, `ruamel.yaml`, `config`

---

### 2. `fuel_enrichment.py` (~200 lines)
**Purpose**: Extract and map fuel information from activities

**Functions to migrate**:
- `extract_fuel_from_primaryactivity()` - Main fuel extraction logic
- `clean_fuel_name()` - Standardize fuel names
- `match_fuel_by_table()` - Match fuel using table-based lookup
- `match_fuel_by_term()` - Match fuel using term-based lookup

**Dependencies**: `pandas`, `re`

---

### 3. `sector_enrichment.py` (~300 lines)
**Purpose**: Enrich with NAICS and USEEIO sector information

**Functions to migrate**:
- `get_useeio_from_naics()` - Convert NAICS to USEEIO
- `map_useeio_sector_codes()` - Apply USEEIO mapping to dataframe
- `add_sector_names()` - Add human-readable sector names
- `validate_sector_mapping()` - Check for unmapped sectors

**Dependencies**: `pandas`, `config`

---

### 4. `activity_enrichment.py` (~500 lines)
**Purpose**: Enrich with activity categories and EPA GHGI metadata

**Functions to migrate**:
- `enrich_with_metasource_mapping()` - Main activity enrichment
- `parse_metasources()` - Parse MetaSources column
- `map_activity_categories()` - Apply activity categorization
- `add_ipcc_categories()` - Add IPCC/UNFCCC categories
- `extract_ghgi_chapter_info()` - Parse chapter/table/description
- `add_activity_sets()` - Map to activity set structure
- `validate_activity_mapping()` - Check for unmapped activities

**Dependencies**: `pandas`, `re`, `config`

---

### 5. `gwp_enrichment.py` (~300 lines)
**Purpose**: Add GWP factors and calculate CO2-equivalent emissions

**Functions to migrate**:
- `add_gwp_column()` - Main GWP enrichment function
- `lookup_gwp_by_uuid()` - Get GWP from FlowUUID
- `calculate_emissions_mtco2e()` - Convert to metric tons CO2e
- `calculate_emissions_intensity()` - Calculate emissions per dollar
- `calculate_sector_contributions()` - Calculate % contribution to sector
- `validate_gwp_coverage()` - Check GWP lookup success rate

**Dependencies**: `pandas`, `numpy`, `config`

---

### 6. `metadata_enrichment.py` (~200 lines)
**Purpose**: Add gas categories and other metadata

**Functions to migrate**:
- `add_gas_categories()` - Map flowables to gas categories
- `add_row_ids()` - Add unique row identifiers
- `reorder_columns()` - Apply final column ordering
- `filter_columns()` - Filter to configured columns

**Dependencies**: `pandas`, `config`

---

### 7. `commodity.py` (~500 lines)
**Purpose**: Transform industry form to commodity form

**Functions to migrate**:
- `transform_to_commodity_form()` - Main transformation function
- `load_io_matrices()` - Load Use and Make tables
- `calculate_commodity_coefficients()` - Calculate transformation matrix
- `apply_commodity_transformation()` - Apply transformation to data
- `aggregate_commodity_emissions()` - Aggregate by commodity
- `validate_commodity_transformation()` - Check mass balance

**Dependencies**: `pandas`, `numpy`, `config`

---

### 8. `jsonld_export.py` (~800 lines)
**Purpose**: Generate JSON-LD and D3.js visualization exports

**Functions to migrate**:
- `build_emission_events_jsonld()` - Build event-based JSON-LD
- `build_d3_sunburst_hierarchy()` - Build D3.js sunburst hierarchy
- `build_ghg_source_classification_jsonld()` - Build GHG classification
- `create_emission_event()` - Create single emission event
- `create_hierarchical_node()` - Create D3 hierarchy node
- `aggregate_by_hierarchy()` - Aggregate emissions by category
- `format_jsonld_context()` - Create JSON-LD @context

**Dependencies**: `pandas`, `json`, `terminology`

---

### 9. `validation.py` (~300 lines)
**Purpose**: Validate data quality and compare outputs

**Functions to migrate**:
- `validate_enriched_data()` - Main validation function
- `check_required_columns()` - Verify required columns present
- `check_data_types()` - Verify data types correct
- `check_value_ranges()` - Verify values in valid ranges
- `check_null_values()` - Check for unexpected nulls
- `aggregate_to_reference_format()` - Prepare for comparison
- `compare_with_reference()` - Compare with reference parquet
- `compare_totals()` - Compare total emissions
- `compare_columns()` - Compare column structures
- `compare_data_match()` - Compare row-level data

**Dependencies**: `pandas`, `numpy`, `config`

---

### 10. `utils.py` (~100 lines)
**Purpose**: Shared utility functions

**Functions to migrate**:
- `check_flowsa_version()` - Check FlowSA version
- `validate_flowsa_version()` - Validate version against config
- `get_emissions_intensity_col()` - Get dynamic column name
- `safe_division()` - Division with zero handling
- `format_number()` - Format numbers for display
- `create_output_directories()` - Ensure output dirs exist

**Dependencies**: `subprocess`, `pathlib`, `config`

---

### 11. `enrich_fbs_with_meta.py` (Main, ~300 lines)
**Purpose**: Orchestrate the enrichment workflow

**Structure**:
```python
# Imports
from enrichment import (
    data_loading,
    fuel_enrichment,
    sector_enrichment,
    activity_enrichment,
    gwp_enrichment,
    metadata_enrichment,
    commodity,
    jsonld_export,
    validation,
    utils
)

def main():
    \"\"\"
    Main workflow orchestration:
    1. Validate FlowSA version
    2. Load configuration
    3. Load baseline data
    4. Load enrichment data sources
    5. Apply enrichments
    6. Transform to commodity form (if enabled)
    7. Validate results
    8. Export outputs
    \"\"\"
    # Step-by-step workflow using imported modules
    pass

def save_outputs():
    \"\"\"Export all formats (Excel, CSV, Parquet, JSON-LD, JSON)\"\"\"
    pass

if __name__ == "__main__":
    main()
```

---

## Implementation Strategy

### Phase 1: Preparation (30 min)
1. Create `scripts/enrichment/` directory
2. Create `__init__.py` with package docstring
3. Set up test baseline for comparison

### Phase 2: Extract Data Loading (45 min)
1. Create `data_loading.py`
2. Move all `load_*()` functions
3. Update imports in main script
4. Test data loading still works

### Phase 3: Extract Enrichment Modules (2-3 hours)
1. Create each enrichment module in order:
   - `fuel_enrichment.py`
   - `sector_enrichment.py`
   - `activity_enrichment.py`
   - `gwp_enrichment.py`
   - `metadata_enrichment.py`
2. Move functions to appropriate module
3. Update imports after each module
4. Test enrichment pipeline after each module

### Phase 4: Extract Commodity & Export (1 hour)
1. Create `commodity.py`
2. Create `jsonld_export.py`
3. Move respective functions
4. Test commodity transformation
5. Test all export formats

### Phase 5: Extract Validation & Utils (30 min)
1. Create `validation.py`
2. Create `utils.py`
3. Move remaining functions
4. Clean up main script

### Phase 6: Testing & Documentation (1 hour)
1. Run full pipeline end-to-end
2. Compare outputs with baseline
3. Update docstrings
4. Update README with new structure
5. Commit changes

---

## Testing Strategy

### Unit Tests (Future Enhancement)
After refactoring, add unit tests for each module:
```
tests/
├── test_data_loading.py
├── test_fuel_enrichment.py
├── test_sector_enrichment.py
├── test_activity_enrichment.py
├── test_gwp_enrichment.py
├── test_metadata_enrichment.py
├── test_commodity.py
├── test_jsonld_export.py
├── test_validation.py
└── test_utils.py
```

### Integration Testing
1. **Baseline Comparison**: Run pipeline before and after refactoring
2. **Output Verification**: Ensure all exports match exactly
3. **Performance Check**: Verify no performance degradation

---

## Benefits Summary

### Immediate Benefits
- **Easier navigation**: Jump to specific functionality quickly
- **Better IDE support**: Code completion and go-to-definition works better
- **Clearer dependencies**: See what imports what
- **Isolated testing**: Test modules independently

### Long-term Benefits
- **Maintainability**: Changes isolated to specific modules
- **Reusability**: Import modules in other projects
- **Collaboration**: Multiple developers can work simultaneously
- **Documentation**: Smaller, focused modules easier to document
- **Testability**: Unit tests for each module

---

## Risks & Mitigation

### Risk 1: Breaking Changes
**Mitigation**: 
- Keep original file as backup until testing complete
- Use git branch for refactoring work
- Run comprehensive comparison tests

### Risk 2: Import Circular Dependencies
**Mitigation**: 
- Design clear dependency hierarchy
- Utils at bottom, main orchestration at top
- No cross-imports between enrichment modules

### Risk 3: Performance Impact
**Mitigation**: 
- Profile before and after refactoring
- Ensure no unnecessary data copies
- Keep module imports at top of main script

---

## Success Criteria

1. ✅ All 91 functions moved to appropriate modules
2. ✅ Main script reduced to <300 lines
3. ✅ All outputs match baseline exactly (byte-for-byte comparison)
4. ✅ No performance degradation (within 5% of baseline)
5. ✅ All imports work correctly
6. ✅ Documentation updated
7. ✅ Git history preserved with clear commit messages

---

## Next Steps

When ready to proceed:
1. Create git branch for refactoring: `git checkout -b refactor-modularize`
2. Run baseline test to capture current outputs
3. Follow Phase 1-6 implementation strategy
4. Test thoroughly
5. Merge to main branch when complete

---

**Note**: This refactoring is **optional** and should only be done when time permits. The current script is fully functional and production-ready in its current state.
