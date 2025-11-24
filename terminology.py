"""
Centralized terminology configuration for GHG emissions data.
Update this file to change terminology across all outputs.

Target audience: Corporate sustainability program managers, Scope 3 specialists, carbon credit teams
"""

TERMINOLOGY = {
    # Main entity
    'entity_name': 'GHG Source Instance',
    'entity_plural': 'GHG Sources',
    'dataset_name': 'GHG Sources Dataset',
    
    # Activity hierarchy (4 levels)
    'activity_level_1': 'Activity Category',
    'activity_level_2': 'Activity Subcategory', 
    'activity_level_3': 'Activity Type',
    'activity_level_4': 'Activity',
    
    # Fuel dimension (independent)
    'fuel': 'Fuel Consumed',
    
    # Gas hierarchy (2 levels, independent)
    'gas_level_1': 'Gas Category',
    'gas_level_2': 'Gas',
    
    # Other standard fields
    'ipcc_category': 'IPCC/UNFCCC Category',
    'contribution': "Contribution to USEEIO Sector's Scope 1 (%)",
    'us_ghgi_chapter': 'US GHGI Chapter',
    'us_ghgi_table_id': 'US GHGI Table ID',
    'us_ghgi_table_name': 'US GHGI Table Name',
}

# Column name mappings (old → new)
# These map internal/legacy column names to user-facing names
COLUMN_MAPPING = {
    # Activity hierarchy
    'GHG Source Category': TERMINOLOGY['activity_level_1'],
    'GHG Source Subcategory': TERMINOLOGY['activity_level_2'],
    'GHG Source SubSubcategory': TERMINOLOGY['activity_level_3'],
    'Activity': TERMINOLOGY['activity_level_4'],
    
    # Fuel dimension
    'Fuel': TERMINOLOGY['fuel'],
    
    # Gas hierarchy
    'Gas category': TERMINOLOGY['gas_level_1'],
    'Gas': TERMINOLOGY['gas_level_2'],
    
    # Other fields (kept for completeness)
    'IPCC/UNFCCC Category': TERMINOLOGY['ipcc_category'],
    "Contribution to USEEIO Sector's Scope 1 (%)": TERMINOLOGY['contribution'],
}

# Reverse mapping (new → old) for internal processing
REVERSE_COLUMN_MAPPING = {v: k for k, v in COLUMN_MAPPING.items()}

# JSON-LD property names (snake_case for RDF/semantic web)
JSONLD_PROPERTIES = {
    'activity_level_1': 'activity_category',
    'activity_level_2': 'activity_subcategory',
    'activity_level_3': 'activity_type',
    'activity_level_4': 'activity',
    'fuel': 'fuel_consumed',
    'gas_level_1': 'gas_category',
    'gas_level_2': 'gas',
    'ipcc_category': 'ipcc_unfccc_category',
    'contribution': 'contributionToUSEEIOSectorScope1Percent',
}

# Display names for exports (Excel, CSV headers)
DISPLAY_NAMES = {
    'activity_level_1': TERMINOLOGY['activity_level_1'],
    'activity_level_2': TERMINOLOGY['activity_level_2'],
    'activity_level_3': TERMINOLOGY['activity_level_3'],
    'activity_level_4': TERMINOLOGY['activity_level_4'],
    'fuel': TERMINOLOGY['fuel'],
    'gas_level_1': TERMINOLOGY['gas_level_1'],
    'gas_level_2': TERMINOLOGY['gas_level_2'],
}

def get_display_name(internal_name):
    """Get user-facing display name for an internal column name."""
    return COLUMN_MAPPING.get(internal_name, internal_name)

def get_internal_name(display_name):
    """Get internal column name from user-facing display name."""
    return REVERSE_COLUMN_MAPPING.get(display_name, display_name)

def get_jsonld_property(terminology_key):
    """Get JSON-LD property name for a terminology key."""
    return JSONLD_PROPERTIES.get(terminology_key, terminology_key)
