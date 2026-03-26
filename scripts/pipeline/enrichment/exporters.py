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
# COLUMN_MAPPING removed - using direct column names


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
    
    # TODO: Implement build_emission_event_full() helper function
    # TODO: Add event creation logic
    # for idx, row in df.iterrows():
    #     event = build_emission_event_full(row)
    #     events.append(event)
    
    jsonld_data = {
        "@context": context,
        "@graph": events
    }
    
    print(f"✓ Built {len(events):,} emission events")
    
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
    print("Building D3.js sunburst hierarchy...")
    
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
    
    # TODO: Convert to D3.js format with proper nesting
    # TODO: Add size calculations
    # TODO: Add children arrays
    
    root = {
        "name": "Emissions",
        "children": []
    }
    
    print(f"✓ Built sunburst hierarchy")
    
    return root


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
    
    # TODO: Implement export logic for each form
    # TODO: Export Excel, CSV, Parquet formats
    # TODO: Export JSON-LD and sunburst JSON
    # TODO: Add progress reporting
    
    print("\n✓ All outputs saved successfully")


# TODO: Add more export functions as needed during incremental migration
# Candidates from enrich_fbs_with_meta.py:
# - build_emission_event_full()
# - export_excel()
# - export_csv()
# - export_parquet()
# - export_jsonld()
# etc.
