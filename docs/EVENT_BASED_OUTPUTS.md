# Event-Based JSON-LD Outputs

## Overview

The enrichment pipeline now generates **event-based emission data** in addition to traditional tabular formats. This enables multi-dimensional analysis, semantic queries, and interactive visualizations.

## New Output Files

### 1. Full RDF/Knowledge Graph Format
**File:** `{model}_emission_events.jsonld`  
**Size:** ~18 MB (8,772 events)  
**Purpose:** Semantic web, SPARQL queries, knowledge graphs

```json
{
  "@id": "emission_event:331313_aluminum_production_hexafluoroethane_none",
  "@type": "EmissionEvent",
  
  "hasCategory": {
    "name": "Process & Fugitive Gases",
    "subcategory": "Industrial Production Processes",
    "subSubcategory": "PFCs from aluminum production"
  },
  
  "fromActivity": {
    "activitySet": "PFCs from aluminum production",
    "activity": "Aluminum Production"
  },
  
  "emitsGas": {
    "gasCategory": "Fluorinated gases (F-Gases)",
    "gas": "Hexafluoroethane",
    "co2eGWP": "AR5-100yr",
    "gwpAR5_100": 11100
  },
  
  "inSector": {
    "useeioCode": "331313",
    "naicsCodes": ["331313"]
  },
  
  "hasEmission": {
    "contributionToSectorScope1Percent": 0.023000239
  }
}
```

### 2. D3.js Sunburst Format
**File:** `{model}_emission_events_sunburst.json`  
**Size:** ~4.5 MB (20,714 nodes)  
**Purpose:** Interactive D3.js sunburst visualization

```json
{
  "name": "GHG Emissions",
  "children": [
    {
      "name": "331313",
      "category": "useeio_sector",
      "useeio_code": "331313",
      "children": [
        {
          "name": "Process & Fugitive Gases",
          "category": "ghg_source",
          "children": [
            {
              "name": "Industrial Production Processes",
              "category": "subcategory",
              "children": [
                {
                  "name": "PFCs from aluminum production",
                  "category": "sub_subcategory",
                  "children": [
                    {
                      "name": "Aluminum Production",
                      "category": "activity",
                      "children": [
                        {
                          "name": "none",
                          "category": "fuel",
                          "children": [
                            {
                              "name": "Fluorinated gases (F-Gases)",
                              "category": "gas_category",
                              "children": [
                                {
                                  "name": "Hexafluoroethane",
                                  "category": "gas",
                                  "value": 0.023000239
                                }
                              ]
                            }
                          ]
                        }
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

## Key Features

### Event-Based Structure (RDF)

**Benefits:**
- ✅ **Multi-dimensional:** Not forced into single hierarchy
- ✅ **Semantic queries:** SPARQL-ready for complex questions
- ✅ **Explicit relationships:** Clear predicates (hasCategory, emitsGas, inSector)
- ✅ **Knowledge graphs:** Ready for RDF triple stores
- ✅ **Linked data:** @id and @type annotations

**Structure Components:**
- `hasCategory` - GHG source categorization (3 levels)
- `fromActivity` - Activity context (set + specific activity)
- `fromProcess` - Manufacturing/combustion process (future)
- `consumesFuel` - Fuel type and category
- `emitsGas` - Gas species with GWP
- `mapsToIPCC` - IPCC category mapping
- `inSector` - Economic sector (USEEIO + NAICS)
- `hasEmission` - Contribution percentage
- `derivedFrom` - EPA GHGI data provenance
- `attributedBy` - FlowSA attribution method
- `metadata` - Model version and source

### D3.js Sunburst Format

**Benefits:**
- ✅ **Optimized for visualization:** Nested structure with values
- ✅ **Dynamic filtering:** Each node has category metadata
- ✅ **Hierarchical exploration:** 7 levels deep
- ✅ **Contribution values:** Leaf nodes contain percentages
- ✅ **Compact:** Aggregated by unique paths

**Hierarchy:**
```
USEEIO Sector
  └─ GHG Source Category
      └─ Subcategory
          └─ Sub-subcategory
              └─ Activity
                  └─ Fuel
                      └─ Gas Category
                          └─ Gas (with value)
```

**Node Metadata:**
- `name` - Display label
- `category` - Node type (for filtering/styling)
- `useeio_code` - Sector code (at sector level)
- `value` - Contribution percentage (at leaf level)
- `children` - Nested child nodes

## Event ID System

**Format:** `{useeio}_{activity}_{gas}_{fuel}`

**Examples:**
- `331313_aluminum_production_hexafluoroethane_none`
- `1111a0_crop_production_nitrous_oxide_none`
- `221100_electric_power_carbon_dioxide_natural_gas`

**Properties:**
- ✅ Human-readable
- ✅ Unique per emission event
- ✅ Deterministic (reproducible)
- ✅ URI-compatible (no spaces/special chars)

## Use Cases

### 1. Knowledge Graph Queries (SPARQL)

```sparql
# Find all F-Gas emissions in manufacturing
SELECT ?event ?sector ?gas ?gwp
WHERE {
  ?event a :EmissionEvent ;
         :inSector ?s ;
         :emitsGas ?g .
  ?s :useeioCode ?sector .
  ?g :gasCategory "Fluorinated gases (F-Gases)" ;
     :gas ?gas ;
     :gwpAR5_100 ?gwp .
  FILTER(STRSTARTS(?sector, "3"))
}
```

### 2. D3.js Sunburst Visualization

```javascript
// Load and create interactive sunburst
d3.json("emission_events_sunburst.json").then(data => {
  const sunburst = d3.partition()
    .size([2 * Math.PI, radius])
    (d3.hierarchy(data)
      .sum(d => d.value)
      .sort((a, b) => b.value - a.value));
  
  // Add filtering by category
  const filtered = sunburst.descendants()
    .filter(d => d.data.category === 'gas_category' && 
                 d.data.name === 'Carbon dioxide');
});
```

### 3. Multi-Dimensional Filtering

```python
import json

with open('emission_events.jsonld') as f:
    data = json.load(f)

# Filter: High-GWP gases in energy sector
high_gwp_energy = [
    event for event in data['@graph']
    if event['emitsGas']['gwpAR5_100'] > 1000
    and event['mapsToIPCC']['category'] == 'Energy'
]

# Group by fuel type
from collections import defaultdict
by_fuel = defaultdict(list)
for event in data['@graph']:
    fuel = event['consumesFuel']['name'] or 'none'
    by_fuel[fuel].append(event)
```

## Implementation Details

### New Functions

1. **`generate_event_id(row)`**  
   Creates composite unique IDs from sector, activity, gas, and fuel

2. **`build_emission_event_full(row)`**  
   Converts DataFrame row to complete RDF event structure

3. **`build_emission_events_jsonld(df)`**  
   Generates full JSON-LD with @context and @graph

4. **`build_d3_sunburst_hierarchy(df)`**  
   Creates optimized nested structure for D3.js

5. **`export_event_based_outputs(enriched_data, output_dir, model_name)`**  
   Orchestrates export of both formats

### Processing Stats

- **Events generated:** 8,772
- **Sunburst nodes:** 20,714 (aggregated)
- **USEEIO sectors:** 384
- **GHG categories:** 687
- **Processing time:** ~2 seconds

## Migration from Hierarchical Format

**Old (Single Hierarchy):**
```json
{
  "useeio_sector_code": "331313",
  "naics_sectors": [
    {
      "naics_sector_code": "331313",
      "ghg_categories": [
        {
          "ghg_source_category": "Process & Fugitive Gases",
          "ipcc_categories": [...]
        }
      ]
    }
  ]
}
```

**New (Event-Based):**
```json
{
  "@id": "emission_event:331313_...",
  "@type": "EmissionEvent",
  "hasCategory": {...},
  "inSector": {...},
  "emitsGas": {...},
  "mapsToIPCC": {...}
}
```

**Key Differences:**
- ❌ **Old:** Forced nesting, single path, hard to query
- ✅ **New:** Parallel facets, semantic relationships, SPARQL-ready

## Backward Compatibility

**All existing outputs still generated:**
- ✅ Excel, CSV, Parquet (tabular)
- ✅ Hierarchical JSON-LD (legacy)
- ✅ GHG source classification JSON-LD
- ✅ Industry & commodity forms

**New outputs added:**
- ⭐ Event-based JSON-LD (RDF)
- ⭐ D3.js sunburst JSON

## Next Steps

### Visualization
1. Create D3.js sunburst with filters
2. Add zoom and drill-down capabilities
3. Implement category-based color coding

### Knowledge Graph
1. Load into RDF triple store (Apache Jena, GraphDB)
2. Define custom SPARQL queries
3. Link with other environmental datasets

### Analysis
1. Multi-dimensional pivoting
2. Cross-sector comparisons
3. Supply chain tracing

## References

- **RDF/JSON-LD:** https://www.w3.org/TR/json-ld/
- **D3.js Sunburst:** https://observablehq.com/@d3/sunburst
- **SPARQL:** https://www.w3.org/TR/sparql11-query/
- **IPCC GWP:** https://www.ipcc.ch/

---

**Generated:** November 17, 2025  
**Model Version:** GHG_national_2022_m2_DecarbNexus  
**Source:** FlowSA with DecarbNexus Custom Outputs
