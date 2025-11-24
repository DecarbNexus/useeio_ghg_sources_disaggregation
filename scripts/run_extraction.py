#!/usr/bin/env python3
"""
FlowSA GHG Sources Extraction - Simple Runner

This script provides an easy way to run the complete workflow with minimal setup.
Perfect for beginners who want to get started quickly.

Usage:
    python run_extraction.py              # Use default config  
    python run_extraction.py --help       # Show all options
    python run_extraction.py --model GHG_national_2023_m2  # Use different model
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path for imports (config.py is at root)
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))  # Add parent dir first for config.py
sys.path.append(str(current_dir))  # Add scripts dir for script imports


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
        from extract_meta_from_EPA_GHGI import main as extract_main
        extract_main()
        print("SUCCESS: Metadata extraction completed!")
        return True
    except Exception as e:
        print(f"ERROR: Metadata extraction failed: {e}")
        return False


def run_data_enrichment():
    """Run the main data enrichment process.""" 
    print("\nStep 2: Generating and enriching FlowBySector data...")
    print("This may take several minutes depending on your model...")
    
    try:
        from enrich_fbs_with_meta import main as enrich_main
        enrich_main()
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
        (f"{config.OUTPUT_DIR}/EPA_GHGI_meta_sources.csv", "EPA GHGI metadata"),
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
  python run_extraction.py                # Run with default settings
  python run_extraction.py --skip-metadata  # Skip metadata extraction
  python run_extraction.py --check-only   # Just check requirements

To switch models/years, edit MODELNAME in config.py
        """
    )
    
    parser.add_argument(
        "--skip-metadata", 
        action="store_true",
        help="Skip EPA GHGI metadata extraction (if already done)"
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
        metadata_path = os.path.join(config.OUTPUT_DIR, config.EPA_GHGI_META_CSV)
        if not os.path.exists(metadata_path):
            print(f"WARNING: Metadata file not found at {metadata_path}")
            print("   Consider running without --skip-metadata flag")
    
    # Step 2: Generate and enrich data
    if success:
        success &= run_data_enrichment()
    
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