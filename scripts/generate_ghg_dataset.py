#!/usr/bin/env python3
"""
FlowSA GHG Sources Extraction - Simple Runner

This script provides an easy way to run the complete GHG sources extraction workflow.
It handles the full pipeline:
1. Extract EPA GHGI metadata from FlowSA YAML
2. Generate FlowBySector data using FlowSA (with interactive prompt to use cached data)
3. Enrich data with metadata (fuel types, activities, sectors, etc.)
4. Export enriched data in multiple formats

The script automatically filters out sector F01000 (used goods) from all outputs
as it does not produce emissions.

Usage:
    python generate_ghg_dataset.py              # Run with prompts (recommended)
    python generate_ghg_dataset.py --help       # Show all options
    python generate_ghg_dataset.py --skip-fbs-generation  # Use cached FlowBySector data
    python generate_ghg_dataset.py --force-fbs-generation # Generate new without prompt
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path for imports (config.py is at root)
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))  # Add project root for config.py and terminology.py
sys.path.append(str(current_dir))  # Add scripts/ so 'pipeline' package is importable


def print_banner():
    """Print a nice banner for the tool."""
    print("="*80)
    print("FLOWSA GHG SOURCES EXTRACTION")
    print("Generating supply chain emission factors from EPA data")
    print("="*80)


def check_requirements():
    """Check if required packages are installed and versions match."""
    import config
    
    print("Checking requirements...")
    
    required_packages = ['pandas', 'flowsa', 'ruamel.yaml', 'pyarrow']
    missing_packages = []
    
    for package in required_packages:
        try:
            mod = __import__(package)
            print(f"  [OK] {package}")
            
            # Special check for FlowSA version
            if package == 'flowsa' and config.STRICT_VERSION_CHECK:
                try:
                    import importlib.metadata
                    version = importlib.metadata.version('flowsa')
                except:
                    try:
                        version = mod.__version__
                    except:
                        version = "unknown"
                
                # Handle both single version string and list
                required_versions = config.REQUIRED_FLOWSA_VERSION
                if isinstance(required_versions, str):
                    required_versions = [required_versions]
                
                print(f"       FlowSA version: {version}")
                print(f"       Required: {' or '.join(required_versions)} (tag: {config.REQUIRED_FLOWSA_GIT_TAG})")
                
                if version not in required_versions:
                    print(f"       [WARNING] Version mismatch detected!")
                    print(f"       To install correct version:")
                    print(f"         python install_flowsa_2.0.3.py")
                    
        except ImportError:
            missing_packages.append(package)
            print(f"  [MISSING] {package}")
    
    if missing_packages:
        print(f"\nMISSING PACKAGES: {', '.join(missing_packages)}")
        print("Please install with: pip install " + " ".join(missing_packages))
        return False
    
    print("SUCCESS: All requirements satisfied!")
    return True


def run_metadata_extraction():
    """Run EPA GHGI metadata extraction."""
    print("\nStep 1: Extracting EPA GHGI metadata...")
    
    try:
        from pipeline.extract_metadata import main as extract_main
        extract_main()
        print("SUCCESS: Metadata extraction completed!")
        return True
    except Exception as e:
        print(f"ERROR: Metadata extraction failed: {e}")
        return False


def generate_flowbysector_data(modelname):
    """
    Generate FlowBySector data using FlowSA.
    
    This function generates fresh FBS data each time it's called.
    FlowSA will download FlowByActivity source data and cache it locally.
    
    Parameters:
    -----------
    modelname : str
        FlowSA model name (e.g., 'GHG_national_2022_m2')
        
    Returns:
    --------
    pandas.DataFrame
        Generated FlowBySector data with activity columns retained
    """
    import flowsa
    import pandas as pd
    
    print("\nGenerating FlowBySector data using FlowSA...")
    print("This downloads FlowByActivity data and generates FBS...")
    print("This may take several minutes...")
    
    # Generate FlowBySector data using FlowSA
    # Constants (not configurable - required for this workflow):
    #   - download_sources_ok=True: Download FlowByActivity source data
    #   - retain_activity_columns=True: Preserve activity details for enrichment
    #   - append_sector_names=False: We add USEEIO names during enrichment
    fbs_data = pd.DataFrame(flowsa.flowbysector.FlowBySector.generateFlowBySector(
        modelname,
        download_sources_ok=True,
        retain_activity_columns=True,
        append_sector_names=False
    ))
    
    print(f"[OK] Generated {len(fbs_data):,} records using FlowSA")
    
    return fbs_data


def run_fbs_generation(skip_generation=False, force_generation=False):
    """Generate FlowBySector data with activity details retained.
    
    Parameters:
    -----------
    skip_generation : bool
        If True, skip generation and use cached data
    force_generation : bool
        If True, force new generation without prompting
    """
    import config
    import pandas as pd
    
    print("\nStep 2: FlowBySector Data Generation")
    print("="*60)
    
    # Check if cached FBS data exists
    cache_dir = Path.home() / "AppData" / "Local" / "flowsa" / "FlowBySector"
    cached_files = list(cache_dir.glob(f"{config.MODELNAME}*.parquet")) if cache_dir.exists() else []
    
    if cached_files:
        print(f"Found {len(cached_files)} cached FBS file(s) for {config.MODELNAME}")
        for file in cached_files[:3]:  # Show first 3
            file_size = file.stat().st_size / (1024*1024)  # MB
            print(f"  - {file.name} ({file_size:.1f} MB)")
        if len(cached_files) > 3:
            print(f"  ... and {len(cached_files) - 3} more")
    else:
        print(f"No cached FBS data found for {config.MODELNAME}")
    
    # Handle command-line flags
    if force_generation:
        print("\n--force-fbs-generation flag set, generating new data...")
        should_generate = True
    elif skip_generation:
        print("\n--skip-fbs-generation flag set, using cached data...")
        should_generate = False
    else:
        # Interactive prompt
        print("\nGenerate new FlowBySector data?")
        print("  YES: Download fresh data and generate new FBS (may take several minutes)")
        print("  NO:  Use existing cached FBS data (if available)")
        
        while True:
            response = input("\nGenerate new FBS? [y/N]: ").strip().lower()
            
            if response in ['y', 'yes']:
                should_generate = True
                break
            elif response in ['n', 'no', '']:
                should_generate = False
                break
            else:
                print("Please answer 'y' (yes) or 'n' (no)")
                continue
    
    # Generate or load based on decision
    if should_generate:
        print("\nGenerating new FlowBySector data...")
        print("This will download FlowByActivity source data and generate FBS...")
        print("This may take several minutes...")
        
        try:
            fbs_data = generate_flowbysector_data(config.MODELNAME)
            print(f"[OK] Generated {len(fbs_data):,} FBS records!")
            return fbs_data
        except Exception as e:
            print(f"ERROR: FBS generation failed: {e}")
            return None
    else:
        # Try to load cached data
        print("\nUsing cached FBS data...")
        
        if not cached_files:
            print("ERROR: No cached FBS data found!")
            print("Please run again with --force-fbs-generation or answer 'yes' to the prompt")
            return None
        
        # Use the most recent cached file
        latest_file = max(cached_files, key=lambda f: f.stat().st_mtime)
        print(f"Loading cached file: {latest_file.name}")
        
        try:
            fbs_data = pd.read_parquet(latest_file)
            # Format Location column to match generated format
            fbs_data.Location = fbs_data.Location.apply('="{}"'.format)
            print(f"[OK] Loaded {len(fbs_data):,} FBS records from cache")
            return fbs_data
        except Exception as e:
            print(f"ERROR: Failed to load cached data: {e}")
            return None


def run_data_enrichment(fbs_data):
    """Run the main data enrichment process.
    
    Parameters:
    -----------
    fbs_data : pandas.DataFrame
        Generated FlowBySector data to enrich
    """ 
    print("\nStep 3: Enriching FlowBySector data with metadata...")
    print("This may take a few minutes...")
    
    try:
        from pipeline.enrich_and_export import main as enrich_main
        enrich_main(fbs_calculated=fbs_data)
        print("SUCCESS: Data enrichment completed!")
        return True
    except Exception as e:
        print(f"ERROR: Data enrichment failed: {e}")
        return False


def show_results():
    """Show the user where to find results."""
    import config
    
    print("\nSUCCESS! Your GHG emission factors are ready!")
    print("="*60)
    print("Check these output files:")
    
    # Check for industry output files
    industry_dir = os.path.join(config.OUTPUT_DIR, config.INDUSTRY_OUTPUT_SUBDIR)
    industry_basename = config.MODELNAME + "_industry"
    
    output_files = [
        (f"{config.OUTPUT_DIR}/metadata/EPA_GHGI_meta_sources.csv", "EPA GHGI metadata"),
        (f"{industry_dir}/{industry_basename}.xlsx", "*** FINAL ENRICHED DATA (Excel) ***"),
        (f"{industry_dir}/{industry_basename}.parquet", "Final data (Parquet)"),
        (f"{industry_dir}/{industry_basename}.jsonld", "Emission events (JSON-LD)"),
    ]
    
    for file_path, description in output_files:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path) / (1024*1024)  # MB
            print(f"  [OK] {file_path}")
            print(f"       {description} ({file_size:.1f} MB)")
        else:
            print(f"  [MISSING] {file_path}")
    
    print("\nNext steps:")
    print("   1. Open the enriched Excel file to explore your data")
    print("   2. Use this data in your USEEIO supply chain analysis")
    print("   3. Check the README.md for integration examples")


def main():
    """Main function to run the complete workflow."""
    parser = argparse.ArgumentParser(
        description="FlowSA GHG Sources Extraction - Simple Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_ghg_dataset.py                     # Run with prompts (recommended)
  python generate_ghg_dataset.py --skip-metadata     # Skip metadata extraction
  python generate_ghg_dataset.py --skip-fbs-generation    # Use cached FBS data
  python generate_ghg_dataset.py --force-fbs-generation   # Generate new FBS without prompt
  python generate_ghg_dataset.py --check-only        # Just check requirements

To switch models/years, edit MODELNAME in config.py
        """
    )
    
    parser.add_argument(
        "--skip-metadata", 
        action="store_true",
        help="Skip EPA GHGI metadata extraction (if already done)"
    )
    parser.add_argument(
        "--skip-fbs-generation",
        action="store_true",
        help="Skip FBS generation, use cached data (if available)"
    )
    parser.add_argument(
        "--force-fbs-generation",
        action="store_true",
        help="Force new FBS generation without prompting"
    )
    parser.add_argument(
        "--check-only", 
        action="store_true",
        help="Only check requirements, don't run extraction"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    # Check requirements first
    if not check_requirements():
        return 1
    
    if args.check_only:
        print("SUCCESS: Requirements check complete. Ready to run extraction!")
        return 0
    
    # Load and show current config
    try:
        import config
        print(f"\nCurrent configuration:")
        print(f"   Model: {config.MODELNAME}")
        print(f"   Year: {config.MODEL_YEAR}")
        print(f"   Description: {config.MODEL_DESCRIPTION}")
    except Exception as e:
        print(f"ERROR: Error loading config: {e}")
        return 1
    
    # Run the workflow
    success = True
    
    # Step 1: Extract metadata (unless skipped)
    if not args.skip_metadata:
        success &= run_metadata_extraction()
    else:
        print("\nStep 1: Skipping metadata extraction (--skip-metadata)")
        
        # Check if metadata file exists
        metadata_path = os.path.join(config.OUTPUT_DIR, "metadata", config.EPA_GHGI_META_CSV)
        if not os.path.exists(metadata_path):
            print(f"WARNING: Metadata file not found at {metadata_path}")
            print("   Consider running without --skip-metadata flag")
    
    # Step 2: Generate FlowBySector data
    fbs_data = None
    if success:
        fbs_data = run_fbs_generation(
            skip_generation=args.skip_fbs_generation,
            force_generation=args.force_fbs_generation
        )
        success = fbs_data is not None
    
    # Step 3: Enrich data with metadata
    if success and fbs_data is not None:
        success &= run_data_enrichment(fbs_data)
    
    # Show results
    if success:
        show_results()
        print("\nCOMPLETE! Happy analyzing!")
        return 0
    else:
        print("\nERROR: Extraction failed. Check error messages above.")
        print("TROUBLESHOOTING TIPS:")
        print("   - Ensure FlowSA is properly installed")
        print("   - Check that you have internet connection for data downloads")
        print("   - Verify your model name in config.py")
        return 1


if __name__ == "__main__":
    exit(main())