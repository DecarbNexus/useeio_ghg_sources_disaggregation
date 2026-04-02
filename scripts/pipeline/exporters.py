"""
Data Export Functions for FlowBySector Processing

This module contains functions for exporting enriched data in various formats
including Excel, CSV, Parquet, JSON-LD, and D3.js visualization hierarchies.
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Add parent directory to path to import config
parent_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(parent_dir))
import config
from .utils import build_emission_event_full, generate_event_id, compute_ghg_source_id
from terminology import TERMINOLOGY, get_jsonld_property

# Version-specific EPA GHGI report metadata (publication year lags model year by ~2 years)
_EPA_GHGI_META = {
    "v1.3.0": {
        "label":           "EPA GHGI Report (2022)",
        "report_url":      "https://www.epa.gov/ghgemissions/inventory-us-greenhouse-gas-emissions-and-sinks-1990-2022",
        "main_text_zip":   "https://www.epa.gov/system/files/other-files/2024-06/2024-main-text-tables.zip",
        "annexes_pdf":     "https://www.epa.gov/system/files/documents/2024-04/us-ghg-inventory-2024-annexes.pdf",
        "annex_tables_zip":"https://www.epa.gov/system/files/other-files/2024-06/2024-annex-tables.zip",
        "ghg_explorer":    "https://cfpub.epa.gov/ghgdata/inventoryexplorer/chartindex.html",
        "ghgi_cite":       "U.S. EPA (2024). Inventory of U.S. GHG Emissions and Sinks: 1990-2022. EPA 430-R-24-004.",
        "flowsa_cite":     "U.S. EPA (2023). FlowSA v2.0.3. MIT License. https://github.com/cornerstone-data/flowsa",
        "useeior_cite":    "U.S. EPA (2022). useeior v1.5.3. MIT License. https://github.com/cornerstone-data/useeior",
        "sef_cite":        "U.S. EPA (2024). Supply Chain Emission Factors v1.3.0. https://github.com/cornerstone-data/supply-chain-factors",
    },
    "v1.4.0": {
        "label":           "EPA GHGI Report (2023)",
        "report_url":      "https://www.edf.org/freedom-information-act-documents-epas-greenhouse-gas-inventory?tab=complete_report",
        "main_text_zip":   None,
        "annexes_pdf":     None,
        "annex_tables_zip":None,
        "ghg_explorer":    None,
        "ghgi_cite":       "U.S. EPA (2025). Inventory of U.S. GHG Emissions and Sinks: 1990-2023.",
        "flowsa_cite":     "Cornerstone Data (2024). FlowSA v2.1.0. MIT License. https://github.com/cornerstone-data/flowsa",
        "useeior_cite":    "Cornerstone Data (2024). useeior v1.8.0. MIT License. https://github.com/cornerstone-data/useeior",
        "sef_cite":        "Cornerstone Data (2025). Supply Chain Emission Factors v1.4.0. https://github.com/cornerstone-data/supply-chain-factors",
    },
}

def build_hierarchical_jsonld(df, include_all_fields=True):
    """
    Build hierarchical JSON-LD structure from flat DataFrame.
    
    Note: Row ID is excluded from JSON-LD exports (only for tabular formats).
    
    Full Hierarchy:
    - USEEIO Sector Code (top level)
      - USEEIO Sector Name (attribute)
      - NAICS Sector Code (child)
        - Activity Category (child)
          - IPCC/UNFCCC Category (child)
            - Activity Subcategory (child)
              - Activity Type (child)
                - GHG Source (child)
                  - Fuel (child)
                    - Gas Category (child)
                      - Gas (leaf with emission values)
    
    Light/Sunburst Hierarchy (aggregated):
    - USEEIO Sector Code (top level)
      - Activity Category (child)
        - Activity Type (child)
          - Gas category (child with summed contributions)
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Enriched data with all columns
    include_all_fields : bool
        If True, include all fields (full version with complete hierarchy)
        If False, simplified hierarchy for visualization with aggregated contributions
        
    Returns:
    --------
    dict
        JSON-LD structure with @context and @graph
    """
    import json
    from collections import defaultdict
    
    print(f"Building {'full' if include_all_fields else 'light'} hierarchical JSON-LD...")
    
    if include_all_fields:
        # Full hierarchy structure
        hierarchy = defaultdict(lambda: {
            'naics_sectors': defaultdict(lambda: {
                'ghg_categories': defaultdict(lambda: {
                    'ipcc_categories': defaultdict(lambda: {
                        'ghg_subcategories': defaultdict(lambda: {
                            'activity_sets': defaultdict(lambda: {
                                'activities': defaultdict(lambda: {
                                    'fuels': defaultdict(lambda: {
                                        'gas_categories': defaultdict(lambda: {
                                            'gases': defaultdict(lambda: {
                                                'ghgi_tables': defaultdict(lambda: {
                                                    'emissions': []
                                                })
                                            })
                                        })
                                    })
                                })
                            })
                        })
                    })
                })
            })
        })
        
        # Fields that are part of the hierarchy structure (don't duplicate in emissions)
        hierarchy_fields = {
            'Row ID',  # Exclude Row ID from hierarchy (only for tabular exports)
            'USEEIO Sector Name', 'USEEIO Sector Code', 'NAICS Sector Code',
            'Activity Category', 'IPCC/UNFCCC Category', 'Activity Subcategory',
            'Activity Type', 'GHG Source', 'Fuel', 'Gas Category', 'Gas',
            'US GHGI Chapter', 'US GHGI Table ID', 'US GHGI Table Name', 'Attribution Sources'
        }
        
        # Build full hierarchy
        for _, row in df.iterrows():
            useeio_code = row.get('USEEIO Sector Code')
            if pd.isna(useeio_code):
                continue
                
            useeio_name = row.get('USEEIO Sector Name')
            naics_code = row.get('NAICS Sector Code')
            ghg_category = row.get('Activity Category')
            ipcc_category = row.get('IPCC/UNFCCC Category')
            ghg_subcategory = row.get('Activity Subcategory')
            ghg_sub_subcategory = row.get('Activity Type')
            ghg_source = row.get('GHG Source')
            fuel = row.get('Fuel')
            gas_category = row.get('Gas Category')
            gas = row.get('Gas')
            ghgi_table_id = row.get('US GHGI Table ID')
            ghgi_chapter = row.get('US GHGI Chapter')
            ghgi_table_name = row.get('US GHGI Table Name')
            attribution_sources = row.get('Attribution Sources')
            
            # Convert NaN to None for JSON compatibility
            if pd.isna(useeio_name):
                useeio_name = None
            if pd.isna(ghg_subcategory):
                ghg_subcategory = None
            if pd.isna(ghg_sub_subcategory):
                ghg_sub_subcategory = None
            if pd.isna(fuel):
                fuel = None
            if pd.isna(attribution_sources):
                attribution_sources = None
            
            # Store USEEIO sector info
            if 'useeio_sector_name' not in hierarchy[useeio_code]:
                hierarchy[useeio_code]['useeio_sector_name'] = useeio_name
            
            # Navigate full hierarchy
            naics_dict = hierarchy[useeio_code]['naics_sectors'][naics_code]
            ghg_dict = naics_dict['ghg_categories'][ghg_category]
            ipcc_dict = ghg_dict['ipcc_categories'][ipcc_category]
            subcategory_dict = ipcc_dict['ghg_subcategories'][ghg_subcategory]
            sub_subcategory_dict = subcategory_dict['activity_sets'][ghg_sub_subcategory]
            source_dict = sub_subcategory_dict['activities'][ghg_source]
            fuel_dict = source_dict['fuels'][fuel]
            gas_cat_dict = fuel_dict['gas_categories'][gas_category]
            gas_dict = gas_cat_dict['gases'][gas]
            
            # Store gas-level attributes (only once)
            if 'attribution_sources' not in gas_dict:
                gas_dict['attribution_sources'] = attribution_sources
            
            # Navigate to GHGI table level
            ghgi_table_dict = gas_dict['ghgi_tables'][ghgi_table_id]
            
            # Store GHGI table metadata (only once)
            if 'ghgi_chapter' not in ghgi_table_dict:
                ghgi_table_dict['ghgi_chapter'] = ghgi_chapter
            if 'ghgi_table_name' not in ghgi_table_dict:
                ghgi_table_dict['ghgi_table_name'] = ghgi_table_name
            
            # Store emission data (only non-hierarchy fields)
            emission_record = {}
            for col, val in row.items():
                if col not in hierarchy_fields and not pd.isna(val):
                    emission_record[col] = val
            
            if emission_record:
                ghgi_table_dict['emissions'].append(emission_record)
    
    else:
        # Light hierarchy: USEEIO → Activity Category → Activity Set → Gas Category
        # Aggregate by summing contributions
        aggregation = defaultdict(lambda: {
            'ghg_categories': defaultdict(lambda: {
                'activity_sets': defaultdict(lambda: {
                    'gas_categories': defaultdict(float)
                })
            })
        })
        
        # Aggregate contributions
        for _, row in df.iterrows():
            useeio_code = row.get('USEEIO Sector Code')
            if pd.isna(useeio_code):
                continue
                
            ghg_category = row.get('Activity Category')
            ghg_sub_subcategory = row.get('Activity Type')
            gas_category = row.get('Gas Category')
            contribution = row.get("Contribution to USEEIO Sector's Scope 1 (%)", 0)
            
            if pd.isna(contribution):
                contribution = 0
            
            # Sum contributions for this combination
            aggregation[useeio_code]['ghg_categories'][ghg_category]['activity_sets'][ghg_sub_subcategory]['gas_categories'][gas_category] += contribution
        
        hierarchy = aggregation
    
    # Convert nested defaultdicts to regular dicts for JSON serialization
    def convert_to_dict(obj):
        if isinstance(obj, defaultdict):
            obj = {k: convert_to_dict(v) for k, v in obj.items()}
        return obj
    
    hierarchy = convert_to_dict(hierarchy)
    
    # Build final JSON-LD structure
    graph = []
    
    if include_all_fields:
        # Full hierarchy structure
        for useeio_code, useeio_data in hierarchy.items():
            useeio_obj = {
                'useeio_sector_code': useeio_code,
                'useeio_sector_name': useeio_data.get('useeio_sector_name'),
                'naics_sectors': []
            }
            
            for naics_code, naics_data in useeio_data['naics_sectors'].items():
                naics_obj = {
                    'naics_sector_code': naics_code,
                    'ghg_categories': []
                }
                
                for ghg_cat, ghg_data in naics_data['ghg_categories'].items():
                    ghg_obj = {
                        'ghg_source_category': ghg_cat,
                        'ipcc_categories': []
                    }
                    
                    for ipcc_cat, ipcc_data in ghg_data['ipcc_categories'].items():
                        ipcc_obj = {
                            'ipcc_unfccc_category': ipcc_cat,
                            'ghg_subcategories': []
                        }
                        
                        for subcategory, subcategory_data in ipcc_data['ghg_subcategories'].items():
                            subcategory_obj = {
                                'ghg_source_subcategory': subcategory,
                                'activity_sets': []
                            }
                            
                            for activity_set, activity_set_data in subcategory_data['activity_sets'].items():
                                activity_set_obj = {
                                    'ghg_source_sub_subcategory': activity_set,
                                    'activities': []
                                }
                                
                                for activity, activity_data in activity_set_data['activities'].items():
                                    activity_obj = {
                                        'ghg_source': activity,
                                        'fuels': []
                                    }
                                    
                                    for fuel, fuel_data in activity_data['fuels'].items():
                                        fuel_obj = {
                                            'fuel': fuel,
                                            'gas_categories': []
                                        }
                                        
                                        for gas_cat, gas_cat_data in fuel_data['gas_categories'].items():
                                            gas_cat_obj = {
                                                'gas_category': gas_cat,
                                                'gases': []
                                            }
                                            
                                            for gas, gas_data in gas_cat_data['gases'].items():
                                                gas_obj = {
                                                    'gas': gas,
                                                    'attribution_sources': gas_data.get('attribution_sources'),
                                                    'ghgi_tables': []
                                                }
                                                
                                                # Add GHGI table hierarchy
                                                for ghgi_table_id, ghgi_table_data in gas_data['ghgi_tables'].items():
                                                    ghgi_table_obj = {
                                                        'ghgi_table_id': ghgi_table_id,
                                                        'ghgi_chapter': ghgi_table_data.get('ghgi_chapter'),
                                                        'ghgi_table_name': ghgi_table_data.get('ghgi_table_name'),
                                                        'emissions': ghgi_table_data['emissions']
                                                    }
                                                    gas_obj['ghgi_tables'].append(ghgi_table_obj)
                                                
                                                gas_cat_obj['gases'].append(gas_obj)
                                            
                                            fuel_obj['gas_categories'].append(gas_cat_obj)
                                        
                                        activity_obj['fuels'].append(fuel_obj)
                                    
                                    activity_set_obj['activities'].append(activity_obj)
                                
                                subcategory_obj['activity_sets'].append(activity_set_obj)
                            
                            ipcc_obj['ghg_subcategories'].append(subcategory_obj)
                        
                        ghg_obj['ipcc_categories'].append(ipcc_obj)
                    
                    naics_obj['ghg_categories'].append(ghg_obj)
                
                useeio_obj['naics_sectors'].append(naics_obj)
            
            graph.append(useeio_obj)
        
        # Count nodes at each level for full hierarchy
        total_useeio = len(graph)
        total_naics = sum(len(u['naics_sectors']) for u in graph)
        total_ghg = sum(len(n['ghg_categories']) for u in graph for n in u['naics_sectors'])
        total_ipcc = sum(len(g['ipcc_categories']) for u in graph for n in u['naics_sectors'] 
                        for g in n['ghg_categories'])
        
        print(f"[SUCCESS] Built full hierarchy: {total_useeio} USEEIO sectors → {total_naics} NAICS → {total_ghg} GHG categories → {total_ipcc} IPCC categories")
    
    else:
        # Light hierarchy structure (aggregated)
        for useeio_code, useeio_data in hierarchy.items():
            useeio_obj = {
                'useeio_sector_code': useeio_code,
                'ghg_categories': []
            }
            
            for ghg_cat, ghg_data in useeio_data['ghg_categories'].items():
                ghg_obj = {
                    'ghg_source_category': ghg_cat,
                    'activity_sets': []
                }
                
                for activity_set, activity_set_data in ghg_data['activity_sets'].items():
                    activity_set_obj = {
                        'ghg_source_sub_subcategory': activity_set,
                        'gas_categories': []
                    }
                    
                    for gas_cat, contribution in activity_set_data['gas_categories'].items():
                        gas_cat_obj = {
                            'gas_category': gas_cat,
                            'contribution_pct': contribution
                        }
                        activity_set_obj['gas_categories'].append(gas_cat_obj)
                    
                    ghg_obj['activity_sets'].append(activity_set_obj)
                
                useeio_obj['ghg_categories'].append(ghg_obj)
            
            graph.append(useeio_obj)
        
        # Count nodes at each level for light hierarchy
        total_useeio = len(graph)
        total_ghg = sum(len(u['ghg_categories']) for u in graph)
        total_activity_sets = sum(len(g['activity_sets']) for u in graph for g in u['ghg_categories'])
        total_gas_cats = sum(len(a['gas_categories']) for u in graph for g in u['ghg_categories'] 
                            for a in g['activity_sets'])
        
        print(f"[SUCCESS] Built light hierarchy: {total_useeio} USEEIO sectors → {total_ghg} GHG categories → {total_activity_sets} activity sets → {total_gas_cats} gas categories")
    
    # Create JSON-LD with context
    jsonld = {
        "@context": {
            "@vocab": "http://example.org/ghg#",
            "useeio": "http://useeio.org/sectors/",
            "naics": "http://naics.org/sectors/",
            "ipcc": "http://ipcc.org/categories/",
            "xsd": "http://www.w3.org/2001/XMLSchema#"
        },
        "@graph": graph
    }
    
    return jsonld


def build_ghg_source_classification_jsonld(df):
    """
    Build GHG source classification in multidimensional JSON-LD format.
    
    Creates separate hierarchies for different dimensions:
    1. GHG Source Hierarchy: Category → Subcategory → SubSubcategory → Activity
    2. Fuel Dimension: Independent list of fuels
    3. Gas Hierarchy: Gas Category → Gas
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Enriched data with GHG classification columns
        
    Returns:
    --------
    dict
        JSON-LD structure with @context and @graph containing multidimensional GHG classifications
    """
    from collections import defaultdict
    import json
    
    print("Building GHG source classification JSON-LD...")
    
    # Build GHG Source Hierarchy: Category → Subcategory → SubSubcategory → Activity
    ghg_hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    
    # Build Fuel list (independent dimension)
    fuels = set()
    
    # Build Gas Hierarchy: Gas Category → Gas
    gas_hierarchy = defaultdict(set)
    
    for _, row in df.iterrows():
        ghg_cat = row.get('Activity Category', 'Unknown')
        ghg_subcat = row.get('Activity Subcategory', 'Unknown')
        ghg_subsubcat = row.get('Activity Type', 'Unknown')
        activity = row.get('Activity', 'Unknown')
        fuel = row.get('Fuel')
        gas_cat = row.get('Gas Category', 'Unknown')
        gas = row.get('Gas', 'Unknown')
        
        # Handle None values
        if pd.isna(ghg_cat) or ghg_cat is None:
            ghg_cat = 'Unknown'
        if pd.isna(ghg_subcat) or ghg_subcat is None:
            ghg_subcat = 'Unknown'
        if pd.isna(ghg_subsubcat) or ghg_subsubcat is None:
            ghg_subsubcat = 'Unknown'
        if pd.isna(activity) or activity is None:
            activity = 'Unknown'
        if pd.isna(gas_cat) or gas_cat is None:
            gas_cat = 'Unknown'
        if pd.isna(gas) or gas is None:
            gas = 'Unknown'
        
        # Store in GHG source hierarchy
        ghg_hierarchy[ghg_cat][ghg_subcat][ghg_subsubcat].add(activity)
        
        # Store fuel (independent)
        if pd.notna(fuel) and fuel is not None and fuel != 'None' and fuel != '':
            fuels.add(fuel)
        
        # Store in gas hierarchy
        gas_hierarchy[gas_cat].add(gas)
    
    # Convert to JSON-LD graph structure
    graph = []
    
    # 1. GHG Source Hierarchy
    ghg_source_categories = []
    for ghg_cat in sorted(ghg_hierarchy.keys()):
        category_obj = {
            get_jsonld_property('activity_level_1'): ghg_cat,
            "subcategories": []
        }
        
        for ghg_subcat in sorted(ghg_hierarchy[ghg_cat].keys()):
            subcat_obj = {
                get_jsonld_property('activity_level_2'): ghg_subcat,
                "activity_types": []
            }
            
            for ghg_subsubcat in sorted(ghg_hierarchy[ghg_cat][ghg_subcat].keys()):
                subsubcat_obj = {
                    get_jsonld_property('activity_level_3'): ghg_subsubcat,
                    "activities": sorted(list(ghg_hierarchy[ghg_cat][ghg_subcat][ghg_subsubcat]))
                }
                subcat_obj["activity_types"].append(subsubcat_obj)
            
            category_obj["subcategories"].append(subcat_obj)
        
        ghg_source_categories.append(category_obj)
    
    # 2. Fuel Dimension (independent list)
    fuel_list = sorted(list(fuels))
    
    # 3. Gas Hierarchy
    gas_categories = []
    for gas_cat in sorted(gas_hierarchy.keys()):
        gas_cat_obj = {
            get_jsonld_property('gas_level_1'): gas_cat,
            "gases": sorted(list(gas_hierarchy[gas_cat]))
        }
        gas_categories.append(gas_cat_obj)
    
    # Build graph with all three dimensions
    graph.append({
        "classification_type": "activity_hierarchy",
        "categories": ghg_source_categories
    })
    
    graph.append({
        "classification_type": "fuel_dimension",
        "fuels": fuel_list
    })
    
    graph.append({
        "classification_type": "gas_hierarchy",
        "gas_categories": gas_categories
    })
    
    # Count unique elements
    total_ghg_categories = len(ghg_hierarchy)
    total_fuels = len(fuels)
    total_gas_categories = len(gas_hierarchy)
    
    print(f"[SUCCESS] Built GHG source classification:")
    print(f"  - {total_ghg_categories} activity categories")
    print(f"  - {total_fuels} unique fuels")
    print(f"  - {total_gas_categories} gas categories")
    
    # Create JSON-LD with context
    jsonld = {
        "@context": {
            "@vocab": "http://example.org/ghg#",
            "ipcc": "http://ipcc.org/categories/",
            "xsd": "http://www.w3.org/2001/XMLSchema#"
        },
        "@graph": graph
    }
    
    return jsonld


def build_ghg_source_classification_csv(df):
    """
    Build GHG source classification as CSV with unique combinations.
    
    Extracts unique combinations of classification columns from enriched data.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Enriched data with GHG classification columns
        
    Returns:
    --------
    pandas.DataFrame
        DataFrame with unique classification combinations
    """
    print("Building GHG source classification CSV...")
    
    # Define classification columns
    classification_columns = [
        'Activity Category',
        'IPCC/UNFCCC Category',
        'IPCC Category Code',
        'Activity Subcategory',
        'Activity Type',
        'Activity',
        'Fuel',
        'Gas Category',
        'Gas'
    ]
    
    # Drop rows where Activity Category is unmatched (enrichment lookup miss)
    available = [c for c in classification_columns if c in df.columns]
    dropna_cols = [c for c in ['Activity Category'] if c in available]
    subset = df[available + (['US GHGI Table ID'] if 'US GHGI Table ID' in df.columns else [])].dropna(subset=dropna_cols) if dropna_cols else df[available + (['US GHGI Table ID'] if 'US GHGI Table ID' in df.columns else [])]

    # Aggregate table IDs per unique combination, then drop duplicates on classification cols
    if 'US GHGI Table ID' in subset.columns:
        table_ids = (
            subset.dropna(subset=['US GHGI Table ID'])
            .groupby(available, dropna=False)['US GHGI Table ID']
            .apply(lambda s: ', '.join(sorted(s.dropna().unique())))
            .reset_index()
            .rename(columns={'US GHGI Table ID': 'EPA GHGI Table IDs'})
        )
        classification_df = subset[available].drop_duplicates().sort_values(by=available).merge(
            table_ids, on=available, how='left'
        )
    else:
        classification_df = subset[available].drop_duplicates().sort_values(by=available)

    # Reset index to get clean row numbers
    classification_df = classification_df.reset_index(drop=True)

    # Add stable hash key as first column
    classification_df.insert(0, 'GHG Source ID', compute_ghg_source_id(classification_df))

    print(f"[SUCCESS] Built GHG source classification CSV with {len(classification_df)} unique combinations")
    
    return classification_df

def build_emission_events_jsonld(df):
    """
    Build event-based JSON-LD for RDF/knowledge graph.
    
    Converts flat DataFrame to semantic event structure suitable for
    SPARQL queries, knowledge graphs, and linked data applications.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Enriched emissions data
        
    Returns:
    --------
    dict
        JSON-LD structure with @context and @graph
    """
    print("Building event-based JSON-LD for RDF/knowledge graph...")
    
    context = {
        "@vocab": "http://decarbonexus.org/ghg#",
        "ipcc": "http://ipcc.org/categories/",
        "naics": "http://naics.com/",
        "useeio": "http://useeio.org/sectors/",
        "xsd": "http://www.w3.org/2001/XMLSchema#"
    }
    
    events = []
    for idx, row in df.iterrows():
        event = build_emission_event_full(row)
        events.append(event)
        
        # Progress indicator for large datasets
        if (idx + 1) % 5000 == 0:
            print(f"  Processed {idx + 1:,} emission events...")
    
    jsonld_data = {
        "@context": context,
        "@graph": events
    }
    
    print(f"[SUCCESS] Built {len(events):,} emission events")
    
    return jsonld_data


def build_d3_sunburst_hierarchy(df):
    """
    Build simplified 3-level D3.js sunburst hierarchy.
    
    Creates a clean 3-ring structure:
    - USEEIO Sector (root level)
      → Activity Category (ring 1)
        → Activity Type (ring 2)
          → Gas Category (ring 3, with contribution values)
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Enriched emissions data
        
    Returns:
    --------
    dict
        D3.js-optimized hierarchical structure with 3 levels
    """
    from collections import defaultdict
    
    print("Building D3.js sunburst hierarchy...")
    
    # Filter out F01000 sector (used goods, non-emission producing)
    df = df[df['USEEIO Sector Code'] != 'F01000'].copy()
    
    # Build 3-level nested hierarchy: USEEIO → GHG Category → SubSubcategory → Gas Category
    hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float))))
    
    for _, row in df.iterrows():
        useeio = row.get('USEEIO Sector Code')
        if pd.isna(useeio):
            continue
            
        ghg_cat = row.get('Activity Category', 'Unknown')
        subsubcat = row.get('Activity Type', 'Unknown')
        gas_cat = row.get('Gas Category', 'Unknown')
        contribution = row.get("Contribution to USEEIO Sector's Scope 1 (%)", 0)
        
        if pd.isna(contribution):
            contribution = 0
        
        # Aggregate contributions at this level
        hierarchy[useeio][ghg_cat][subsubcat][gas_cat] += contribution
    
    # Convert to D3.js format
    root_children = []
    
    for useeio, ghg_cats in hierarchy.items():
        ghg_cat_children = []
        
        for ghg_cat, subsubcats in ghg_cats.items():
            subsubcat_children = []
            
            for subsubcat, gas_cats in subsubcats.items():
                gas_cat_children = []
                
                for gas_cat, contrib in gas_cats.items():
                    gas_cat_children.append({
                        "name": gas_cat,
                        get_jsonld_property('contribution'): contrib,
                        "category": get_jsonld_property('gas_level_1')
                    })
                
                subsubcat_children.append({
                    "name": subsubcat,
                    "children": gas_cat_children,
                    "category": get_jsonld_property('activity_level_3')
                })
            
            ghg_cat_children.append({
                "name": ghg_cat,
                "children": subsubcat_children,
                "category": get_jsonld_property('activity_level_1')
            })
        
        root_children.append({
            "name": useeio,
            "children": ghg_cat_children,
            "category": "useeio_sector",
            "useeio_code": useeio
        })
    
    root = {
        "name": "GHG Emissions",
        "children": root_children
    }
    
    # Count nodes
    total_useeio = len(root_children)
    total_ghg_cats = sum(len(u['children']) for u in root_children)
    total_nodes = 1  # root
    for sector in root_children:
        total_nodes += 1  # sector
        for ghg in sector['children']:
            total_nodes += 1  # ghg category
            for subsubcat in ghg['children']:
                total_nodes += 1  # subsubcategory
                total_nodes += len(subsubcat['children'])  # gas categories
    
    print(f"[SUCCESS] Built D3.js sunburst: {total_useeio} USEEIO sectors → {total_ghg_cats} GHG categories")
    
    return root


def export_event_based_outputs(enriched_data, output_dir, model_name):
    """
    Export event-based JSON-LD files.
    
    Exports:
    --------
    1. {model}_emission_events.jsonld - Full RDF structure for knowledge graphs
    2. {model}_emission_events_sunburst.json - Optimized for D3.js visualization
    
    Parameters:
    -----------
    enriched_data : pandas.DataFrame
        Enriched emissions data
    output_dir : str
        Output directory path
    model_name : str
        Model name for file naming
        
    Returns:
    --------
    dict
        Paths to exported files
    """
    print("\n" + "="*80)
    print("EXPORTING EVENT-BASED OUTPUTS")
    print("="*80)
    
    # Filter out F01000 sector (used goods, non-emission producing)
    enriched_data = enriched_data[enriched_data['USEEIO Sector Code'] != 'F01000'].copy()
    
    # Full RDF format
    print("\n1. Full Emission Events (RDF/Knowledge Graph)")
    print("-" * 40)
    full_jsonld = build_emission_events_jsonld(enriched_data)
    full_path = os.path.join(output_dir, f"{model_name}_emission_events.jsonld")
    
    try:
        with open(full_path, 'w') as f:
            import json
            json.dump(full_jsonld, f, indent=2)
        print(f"[SUCCESS] Saved: {os.path.basename(full_path)}")
        print(f"  Events: {len(full_jsonld['@graph']):,}")
    except Exception as e:
        print(f"⚠ Error saving full events: {e}")
        full_path = None
    
    # D3.js Sunburst format
    print("\n2. D3.js Sunburst Visualization")
    print("-" * 40)
    sunburst_data = build_d3_sunburst_hierarchy(enriched_data)
    sunburst_path = os.path.join(output_dir, f"{model_name}_emission_events_sunburst.json")
    
    try:
        with open(sunburst_path, 'w') as f:
            import json
            json.dump(sunburst_data, f, indent=2)
        print(f"[SUCCESS] Saved: {os.path.basename(sunburst_path)}")
        
        # Count total nodes for info
        def count_nodes(node):
            count = 1
            if 'children' in node:
                for child in node['children']:
                    count += count_nodes(child)
            return count
        
        total_nodes = count_nodes(sunburst_data)
        print(f"  Total nodes: {total_nodes:,}")
    except Exception as e:
        print(f"⚠ Error saving sunburst: {e}")
        sunburst_path = None
    
    print("\n" + "="*80)
    
    return {
        'full_events': full_path,
        'sunburst': sunburst_path
    }


def save_outputs(fbs_parquet, fbs_calculated, enriched_data, config_dict, commodity_data=None):
    """
    Save all outputs in multiple formats for different use cases.
    
    Exports both industry form and commodity form (if provided):
    - Excel (.xlsx) - For manual analysis
    - CSV (.csv) - For general data interchange
    - Parquet (.parquet) - For efficient data science workflows (columnar format)
    - JSON-LD (.jsonld) - Event-based emission events for RDF/knowledge graphs
    - JSON (_sunburst.json) - D3.js-optimized hierarchy for visualization
    
    Parameters:
    -----------
    fbs_parquet : pandas.DataFrame
        Raw parquet data (optional, can be None)
    fbs_calculated : pandas.DataFrame  
        Generated FlowBySector data (not exported anymore)
    enriched_data : pandas.DataFrame
        Final enriched data with metadata (industry form)
    config_dict : dict
        Configuration parameters for file naming
    commodity_data : pandas.DataFrame, optional
        Commodity-form data (if None, only industry form is exported)
    """
    # Ensure output directory exists
    os.makedirs(config_dict["output_dir"], exist_ok=True)
    
    # Create subdirectories for industry and commodity forms
    industry_dir = os.path.join(config_dict["output_dir"], "industry")
    commodity_dir = os.path.join(config_dict["output_dir"], "commodity")
    os.makedirs(industry_dir, exist_ok=True)
    os.makedirs(commodity_dir, exist_ok=True)
    
    print("="*80)
    print("SAVING OUTPUTS")
    print("="*80)
    
    # Prepare both forms for export
    forms_to_export = [
        {'data': enriched_data, 'suffix': '_industry', 'label': 'Industry form', 'subdir': industry_dir}
    ]
    
    if commodity_data is not None:
        forms_to_export.append({
            'data': commodity_data, 
            'suffix': '_commodity', 
            'label': 'Commodity form',
            'subdir': commodity_dir
        })
    
    # Export each form
    for form in forms_to_export:
        data = form['data']
        suffix = form['suffix']
        label = form['label']
        subdir = form['subdir']
        
        print(f"\n{label}:")
        print("-" * 40)
        
        # Filter out F01000 sector (used goods, non-emission producing)
        data = data[data['USEEIO Sector Code'] != 'F01000'].copy()
        
        # Remove QC columns if configured (for Excel, CSV, Parquet)
        export_data = data.copy()
        
        # For commodity form, remove NAICS Sector Code column
        if suffix == '_commodity' and 'NAICS Sector Code' in export_data.columns:
            export_data = export_data.drop(columns=['NAICS Sector Code'])
            print(f"  Excluded NAICS Sector Code (not applicable to commodity form)")
        
        if config.EXCLUDE_QC_COLUMNS:
            qc_cols_present = [col for col in config.QC_ONLY_COLUMNS if col in export_data.columns]
            if qc_cols_present:
                export_data = export_data.drop(columns=qc_cols_present)
                print(f"  Excluded {len(qc_cols_present)} QC columns from flat exports")
        
        # For JSON-LD exports, ALWAYS exclude QC columns (regardless of config flag)
        jsonld_data = data.copy()
        
        # For commodity form, remove NAICS Sector Code from JSON-LD too
        if suffix == '_commodity' and 'NAICS Sector Code' in jsonld_data.columns:
            jsonld_data = jsonld_data.drop(columns=['NAICS Sector Code'])
        
        qc_cols_in_jsonld = [col for col in config.QC_ONLY_COLUMNS if col in jsonld_data.columns]
        if qc_cols_in_jsonld:
            jsonld_data = jsonld_data.drop(columns=qc_cols_in_jsonld)
            if config.EXCLUDE_QC_COLUMNS:  # Only print if not already printed above
                pass
            else:
                print(f"  Excluded {len(qc_cols_in_jsonld)} QC columns from JSON-LD exports")
        
        # Base filename without extension
        base_filename = config.MODELNAME + suffix
        
        # -------------------------------------------------------------------------
        # 1. Excel format - for manual analysis and Excel users
        # -------------------------------------------------------------------------
        excel_path = os.path.join(subdir, f"{base_filename}.xlsx")
        try:
            # Create metadata sheets
            _ghgi = _EPA_GHGI_META.get(config.SEF_VERSION, _EPA_GHGI_META["v1.4.0"])
            author_info = pd.DataFrame({
                'Field': [
                    'Author',
                    'Organization',
                    'Website',
                    'Contact',
                    'Open-source repository',
                    'Q&A + Discussion',
                    'Data License',
                    'License URL',
                    '',  # Blank row
                    'Required Attribution',
                    'Cite This Dataset',
                    'Cite EPA GHGI',
                    'Cite FlowSA',
                    'Cite USEEIOR',
                    'Cite Supply Chain Emission Factors',
                    '',  # Blank row
                    'License Compliance',
                    'Third-Party Licenses'
                    ],
                'Value': [
                    'Damien Lieber',
                    'DecarbNexus LLC',
                    'decarbnexus.com',
                    'contact@decarbnexus.com',
                    'https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation',
                    'https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation/discussions',
                    'CC BY 4.0',
                    'https://creativecommons.org/licenses/by/4.0/',
                    '',  # Blank
                    'You must cite this dataset AND the original sources (EPA GHGI, FlowSA, USEEIOR, SCF)',
                    f'DecarbNexus (2026). U.S. Greenhouse Gas Emissions by USEEIO Sector — Disaggregated EPA GHGI Data ({config.SEF_VERSION}). https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation',
                    _ghgi['ghgi_cite'],
                    _ghgi['flowsa_cite'],
                    _ghgi['useeior_cite'],
                    _ghgi['sef_cite'],
                    '',  # Blank
                    'FlowSA, USEEIOR, and SCF are MIT licensed. Full license texts in outputs/THIRD_PARTY_LICENSES.txt',
                    'See outputs/THIRD_PARTY_LICENSES.txt for MIT license text (FlowSA, USEEIOR, SCF)'
                ]
            })
            
            # Determine perspective type
            perspective = 'Industry' if suffix == '_industry' else 'Commodity'
            
            model_specs = pd.DataFrame({
                'Field': [
                    'SEF Version',
                    'Model Name',
                    'Model Description',
                    'Model Year',
                    'FlowSA Version',
                    'USEEIOR Version',
                    'Reference File',
                    'IPCC Indicator',
                    'IPCC GWP Data File',
                    'Input-Output Perspective',
                    '',  # Blank row
                    _ghgi['label'],
                    *(['Main Text Tables (zip)'] if _ghgi.get('main_text_zip') else []),
                    *(['All Annexes (pdf)'] if _ghgi.get('annexes_pdf') else []),
                    *(['Annex Tables (zip)'] if _ghgi.get('annex_tables_zip') else []),
                    *(['GHG Inventory Data Explorer'] if _ghgi.get('ghg_explorer') else []),
                ],
                'Value': [
                    config.SEF_VERSION,
                    config.MODELNAME,
                    config.MODEL_DESCRIPTION,
                    str(config.MODEL_YEAR),
                    config.REQUIRED_FLOWSA_VERSION,
                    config.USEEIOR_VER,
                    config.FILE_NAME_PARQUET,
                    config.IPCC_INDICATOR,
                    config.IPCC_AR5_100_PARQUET,
                    perspective,
                    '',  # Blank
                    _ghgi['report_url'],
                    *([_ghgi['main_text_zip']] if _ghgi.get('main_text_zip') else []),
                    *([_ghgi['annexes_pdf']] if _ghgi.get('annexes_pdf') else []),
                    *([_ghgi['annex_tables_zip']] if _ghgi.get('annex_tables_zip') else []),
                    *([_ghgi['ghg_explorer']] if _ghgi.get('ghg_explorer') else []),
                ]
            })
            
            # Load reference data for additional tabs
            # GHG source classification - use the final classification we just built
            ghg_classification_df = build_ghg_source_classification_csv(export_data)
            
            try:
                # Sector classification
                sector_classification_df = pd.read_csv(config.SECTOR_CLASSIFICATION_CSV)
            except:
                sector_classification_df = None
            
            try:
                # NAICS to USEEIO crosswalk
                naics_useeio_df = pd.read_csv(config.NAICS_TO_USEEIO_CSV)
            except:
                naics_useeio_df = None
            
            try:
                # V_n matrix (market share)
                v_n_df = pd.read_csv('data/V_n.csv', index_col=0)
            except:
                v_n_df = None
            
            try:
                # x vector (industry output)
                x_df = pd.read_csv('data/x.csv')
            except:
                x_df = None

            # B matrix (flows × commodities) — commodity form only
            b_matrix_df = None
            b_matrix_long_df = None
            if suffix == '_commodity' and hasattr(config, 'B_MATRIX_CSV'):
                try:
                    import os as _os
                    _b_path = _os.path.join(
                        str(__file__).split('scripts')[0],
                        config.B_MATRIX_CSV
                    )
                    from .loaders import load_b_matrix as _load_b
                    _b = _load_b(_b_path)
                    if not _b.empty:
                        # Wide form: index = flow name, columns = commodity codes
                        b_matrix_df = _b.reset_index().rename(columns={_b.index.name or 'index': 'Flow'})
                        # Long form: one row per (flow, commodity, value) — easier for analysis
                        b_matrix_long_df = (
                            _b.reset_index()
                            .rename(columns={_b.index.name or 'index': 'Flow'})
                            .melt(id_vars='Flow', var_name='USEEIO Commodity Code', value_name='Intensity (kg/USD)')
                        )
                        b_matrix_long_df = b_matrix_long_df[b_matrix_long_df['Intensity (kg/USD)'] != 0].reset_index(drop=True)
                except Exception:
                    pass
            
            # Check if baseline tab should be included
            if config.INCLUDE_BASELINE_TAB and fbs_parquet is not None:
                # Export with multiple sheets
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    # Front matter
                    author_info.to_excel(writer, sheet_name='Author_Info', index=False)
                    model_specs.to_excel(writer, sheet_name='Model_Specs', index=False)
                    # Main data
                    export_data.to_excel(writer, sheet_name='Enriched', index=False)
                    if suffix == '_industry':
                        fbs_parquet.to_excel(writer, sheet_name='Baseline', index=False)
                    # Reference data
                    if ghg_classification_df is not None:
                        ghg_classification_df.to_excel(writer, sheet_name='GHG_Classification', index=False)
                    if sector_classification_df is not None:
                        sector_classification_df.to_excel(writer, sheet_name='Sector_Classification', index=False)
                    if naics_useeio_df is not None:
                        naics_useeio_df.to_excel(writer, sheet_name='NAICS_to_USEEIO', index=False)
                    if v_n_df is not None and suffix == '_commodity':
                        v_n_df.to_excel(writer, sheet_name='V_n_Matrix', index=True)
                    if b_matrix_long_df is not None:
                        b_matrix_long_df.to_excel(writer, sheet_name='B_Matrix_Long', index=False)
                print(f"  [SUCCESS] Excel: {base_filename}.xlsx (with Author_Info, Model_Specs, Baseline, and reference data tabs)")
            else:
                # Export single sheet
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    # Front matter
                    author_info.to_excel(writer, sheet_name='Author_Info', index=False)
                    model_specs.to_excel(writer, sheet_name='Model_Specs', index=False)
                    # Main data
                    export_data.to_excel(writer, sheet_name='Enriched', index=False)
                    # Reference data
                    if ghg_classification_df is not None:
                        ghg_classification_df.to_excel(writer, sheet_name='GHG_Classification', index=False)
                    if sector_classification_df is not None:
                        sector_classification_df.to_excel(writer, sheet_name='Sector_Classification', index=False)
                    if naics_useeio_df is not None:
                        naics_useeio_df.to_excel(writer, sheet_name='NAICS_to_USEEIO', index=False)
                    if v_n_df is not None and suffix == '_commodity':
                        v_n_df.to_excel(writer, sheet_name='V_n_Matrix', index=True)
                    if b_matrix_long_df is not None:
                        b_matrix_long_df.to_excel(writer, sheet_name='B_Matrix_Long', index=False)
                print(f"  [SUCCESS] Excel: {base_filename}.xlsx (with Author_Info, Model_Specs, and reference data tabs)")
        except PermissionError:
            print(f"  ⚠ Excel export skipped - file is open")
        except Exception as e:
            print(f"  ⚠ Excel export failed: {str(e)}")
        
        # -------------------------------------------------------------------------
        # 2. CSV format - for general data interchange
        # -------------------------------------------------------------------------
        csv_path = os.path.join(subdir, f"{base_filename}.csv")
        try:
            export_data.to_csv(csv_path, index=False)
            print(f"  [SUCCESS] CSV: {base_filename}.csv")
        except PermissionError:
            print(f"  ⚠ CSV export skipped - file is open")
        except Exception as e:
            print(f"  ⚠ CSV export failed: {str(e)}")
        
        # Export baseline CSV if configured
        if config.EXPORT_BASELINE_CSV and config.INCLUDE_BASELINE_TAB and fbs_parquet is not None:
            baseline_csv_path = os.path.join(subdir, f"{config.MODELNAME}{suffix}_baseline.csv")
            try:
                fbs_parquet.to_csv(baseline_csv_path, index=False)
                print(f"  [SUCCESS] CSV (baseline): {config.MODELNAME}{suffix}_baseline.csv")
            except PermissionError:
                print(f"  ⚠ Baseline CSV export skipped - file is open")
            except Exception as e:
                print(f"  ⚠ Baseline CSV export failed: {str(e)}")
        
        # -------------------------------------------------------------------------
        # 3. Parquet format - for efficient data science workflows
        # -------------------------------------------------------------------------
        parquet_path = os.path.join(subdir, f"{base_filename}.parquet")
        try:
            export_data.to_parquet(parquet_path, index=False, engine='pyarrow', compression='snappy')
            print(f"  [SUCCESS] Parquet: {base_filename}.parquet")
        except PermissionError:
            print(f"  ⚠ Parquet export skipped - file is open")
        except Exception as e:
            print(f"  ⚠ Parquet export failed: {str(e)}")
        
        # -------------------------------------------------------------------------
        # 4. JSON-LD format (Full) - Event-based emission events for RDF/knowledge graphs
        # -------------------------------------------------------------------------
        jsonld_path = os.path.join(subdir, f"{base_filename}.jsonld")
        
        try:
            # Build event-based JSON-LD
            emission_events_jsonld = build_emission_events_jsonld(jsonld_data)
            
            with open(jsonld_path, 'w') as f:
                import json
                json.dump(emission_events_jsonld, f, indent=2)
            
            event_count = len(emission_events_jsonld.get('@graph', []))
            print(f"  [SUCCESS] JSON-LD (event-based): {base_filename}.jsonld ({event_count:,} events)")
        except PermissionError:
            print(f"  ⚠ JSON-LD export skipped - file is open")
        except Exception as e:
            print(f"  ⚠ JSON-LD export failed: {str(e)}")
        
        # -------------------------------------------------------------------------
        # 5. JSON format (Sunburst) - D3.js-optimized hierarchy for visualization
        # -------------------------------------------------------------------------
        sunburst_path = os.path.join(subdir, f"{base_filename}_sunburst.json")
        
        try:
            # Build D3.js sunburst hierarchy
            sunburst_hierarchy = build_d3_sunburst_hierarchy(jsonld_data)
            
            with open(sunburst_path, 'w') as f:
                json.dump(sunburst_hierarchy, f, indent=2)
            
            # Count total nodes in hierarchy
            def count_nodes(node):
                count = 1
                if 'children' in node:
                    for child in node['children']:
                        count += count_nodes(child)
                return count
            
            total_nodes = count_nodes(sunburst_hierarchy)
            print(f"  [SUCCESS] JSON (sunburst): {base_filename}_sunburst.json ({total_nodes:,} nodes)")
            
            # Copy industry sunburst to docs/visualization/data for web visualization
            if suffix == '_industry':
                import shutil
                viz_data_dir = os.path.join(os.path.dirname(config_dict["output_dir"]), "docs", "visualization", "data")
                if os.path.exists(viz_data_dir):
                    viz_sunburst_path = os.path.join(viz_data_dir, "industry_sunburst.json")
                    try:
                        shutil.copy2(sunburst_path, viz_sunburst_path)
                        print(f"  [SUCCESS] Copied to visualization: docs/visualization/data/industry_sunburst.json")
                    except Exception as e:
                        print(f"  ⚠ Could not copy to visualization folder: {e}")
                        print(f"  → Manual step: Copy {base_filename}_sunburst.json to docs/visualization/data/industry_sunburst.json")
                else:
                    print(f"  ℹ Visualization folder not found: {viz_data_dir}")
                    print(f"  → To enable web visualization, manually copy:")
                    print(f"      {sunburst_path}")
                    print(f"      to docs/visualization/data/industry_sunburst.json")
        except PermissionError:
            print(f"  ⚠ Sunburst JSON export skipped - file is open")
        except Exception as e:
            print(f"  ⚠ Sunburst JSON export failed: {str(e)}")
    
    # Export GHG source classification (separate from sector-based data)
    print("\n" + "-"*80)
    print("Exporting GHG Source Classification...")
    print("-"*80)
    
    ghg_classification_dir = os.path.join(config_dict["output_dir"], "ghg_source_classification")
    os.makedirs(ghg_classification_dir, exist_ok=True)
    
    # Build classification structures from industry form data (most complete)
    ghg_classification_csv_df = build_ghg_source_classification_csv(enriched_data)
    ghg_classification_jsonld = build_ghg_source_classification_jsonld(enriched_data)
    
    # Export CSV
    ghg_classification_csv_path = os.path.join(
        ghg_classification_dir,
        f"{config.MODELNAME}_ghg_source_classification.csv"
    )
    try:
        ghg_classification_csv_df.to_csv(ghg_classification_csv_path, index=False)
        print(f"[SUCCESS] GHG source classification CSV saved: {os.path.basename(ghg_classification_csv_path)}")
    except PermissionError:
        print(f"⚠ Permission denied: Close {os.path.basename(ghg_classification_csv_path)} if it's open")
    except Exception as e:
        print(f"⚠ Error saving GHG classification CSV: {e}")
    
    # Export JSON-LD
    ghg_classification_jsonld_path = os.path.join(
        ghg_classification_dir,
        f"{config.MODELNAME}_ghg_source_classification.jsonld"
    )
    try:
        with open(ghg_classification_jsonld_path, 'w') as f:
            import json
            json.dump(ghg_classification_jsonld, f, indent=2)
        print(f"[SUCCESS] GHG source classification JSON-LD saved: {os.path.basename(ghg_classification_jsonld_path)}")
    except PermissionError:
        print(f"⚠ Permission denied: Close {os.path.basename(ghg_classification_jsonld_path)} if it's open")
    except Exception as e:
        print(f"⚠ Error saving GHG classification JSON-LD: {e}")
    
    print("\n" + "="*80)
    print("ALL OUTPUTS SAVED")
    print("="*80)
    print(f"Output directory: {config_dict['output_dir']}/")
    print(f"\nDirectory structure:")
    print(f"  - industry/: Emissions by producing industry")
    if commodity_data is not None:
        print(f"  - commodity/: Emissions by product/commodity (supply chain analysis)")
    print(f"  - ghg_source_classification/: GHG classification JSON-LD")
    print(f"\nFormat recommendations:")
    print(f"  - Excel: Manual analysis, visualization in Excel")
    print(f"  - CSV: Import into any tool, simple text format")
    print(f"  - Parquet: Python/R data science (pandas, polars, DuckDB)")
    print(f"  - JSON-LD: Event-based emission events for RDF/knowledge graphs")
    print(f"  - JSON (sunburst): D3.js-optimized hierarchy for visualization")
    print(f"  - JSON-LD (classification): GHG source taxonomy (ghg_source_classification/ folder)")
