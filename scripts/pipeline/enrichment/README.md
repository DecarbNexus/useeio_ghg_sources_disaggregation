# FlowSA GHG Enrichment Package

Modular package for enriching FlowBySector data with EPA GHGI metadata and emissions calculations.

## 📁 Structure

```
enrichment/
├── __init__.py          # Package exports and documentation
├── utils.py             # Utility functions (version checks, column helpers)
├── validators.py        # Data validation and comparison
├── loaders.py           # Data loading from CSV, parquet, YAML
├── enrichers.py         # Data enrichment (fuel, sectors, activities)
├── exporters.py         # Export to Excel, CSV, Parquet, JSON-LD
└── README.md           # This file
```

## 🎯 Design Philosophy

**Separation of Concerns**:
- **loaders**: Pure I/O operations, no business logic
- **enrichers**: Core transformations, return new DataFrames (immutable)
- **exporters**: Output formatting, independent of enrichment
- **validators**: Data quality checks, separate from main workflow
- **utils**: Shared helpers used across modules

**Key Principles**:
- Functions are small and focused
- Each module has a single responsibility
- Imports are explicit and traceable
- Backward compatibility maintained during migration

## 📖 Usage

### Basic Import

```python
from enrichment import loaders, enrichers, validators, exporters

# Load data
metadata = loaders.load_metadata_mapping("data/EPA_GHGI_meta_sources.csv")
fbs_data = loaders.load_parquet_data(input_path, "FlowBySector", "file.parquet")

# Enrich
enriched = enrichers.enrich_with_metadata(fbs_data, metadata)

# Validate
is_valid = validators.validate_data(enriched, "GHG_national_2022_m2")

# Export
exporters.save_outputs(None, fbs_data, enriched, config_dict)
```

### Individual Function Import

```python
from enrichment.utils import validate_flowsa_version
from enrichment.loaders import load_metadata_mapping
from enrichment.enrichers import enrich_with_useeio

# Use functions directly
validate_flowsa_version()
metadata = load_metadata_mapping("path/to/file.csv")
enriched = enrich_with_useeio(df, naics_to_useeio_dict)
```

## 🔧 Current Status

**Phase 1 Complete** (Nov 26, 2025):
- ✅ Package infrastructure created
- ✅ Core utility functions migrated (4 functions)
- ✅ Validation functions migrated (3 functions)
- ✅ Initial loaders created (3 functions)
- ✅ Initial enrichers created (4 function skeletons)
- ✅ Initial exporters created (3 function skeletons)
- ✅ All modules import successfully
- ✅ COLUMN_MAPPING removed - using direct column names throughout
- ✅ GHG classification export (CSV + JSON-LD)
- ✅ Comprehensive Excel metadata tabs (Author_Info, Model_Specs, reference data)
- ✅ Licensing documentation (CC BY 4.0 for data, MIT for dependencies)

**Incremental Migration**:
- Original functions remain in `enrich_fbs_with_meta.py` for backward compatibility
- Complex functions have skeletons with TODO comments
- Migrate additional functions as needed
- Remove duplicates gradually

## 📊 Module Summary

| Module | Lines | Status | Functions |
|--------|-------|--------|-----------|
| `utils.py` | 189 | ✅ Complete | 4 migrated |
| `validators.py` | 238 | ✅ Complete | 3 migrated |
| `loaders.py` | 135 | 🟡 Skeleton | 3 migrated, ~10 TODO |
| `enrichers.py` | 224 | 🟡 Skeleton | 4 skeletons, ~5 TODO |
| `exporters.py` | 181 | 🟡 Skeleton | 3 skeletons, ~10 TODO |

**Total**: ~1,108 lines (vs 4,140 in original monolithic file)

## 🚀 Next Steps

When adding new functionality:

1. **Choose the right module**:
   - Loading data? → `loaders.py`
   - Enriching data? → `enrichers.py`
   - Exporting data? → `exporters.py`
   - Validating data? → `validators.py`
   - Helper function? → `utils.py`

2. **Add the function** to the appropriate module

3. **Update `__init__.py`** to export it:
   ```python
   from .loaders import (
       load_parquet_data,
       load_metadata_mapping,
       your_new_function,  # Add here
   )
   
   __all__ = [
       'load_parquet_data',
       'load_metadata_mapping',
       'your_new_function',  # And here
   ]
   ```

4. **Test the import**:
   ```python
   from enrichment.loaders import your_new_function
   ```

5. **Gradually remove duplicates** from `enrich_fbs_with_meta.py` when ready

## 📝 Notes

- All modules use absolute imports for clarity
- Functions maintain original signatures for compatibility
- TODOs mark functions needing full implementation
- Original code preserved in `enrich_fbs_with_meta.py` until migration complete
