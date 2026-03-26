"""
FlowSA v2.0.3 Installation Script

This script installs the exact version of FlowSA used to generate the reference
parquet file (v2.0.3 with git hash 1cb504c).

This ensures reproducibility and consistency with baseline emissions data.
"""

import subprocess
import sys
import os

# Target version details
# Installing from GitHub release tag v2.0.3
FLOWSA_VERSION_EXPECTED = "2.0.3"
FLOWSA_GIT_TAG = "v2.0.3"  # GitHub release tag
FLOWSA_GIT_HASH = "1cb504c0e7a656ec8d9f2bf00b479df855838c43"  # Full hash for reference
FLOWSA_SHORT_HASH = "1cb504c"  # Short hash for display

def run_command(cmd, description, show_output=False):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    print(f"Command: {' '.join(cmd)}")
    
    if show_output:
        print("\n[Real-time output - this may take 2-5 minutes for git installation]")
        print("-" * 80)
        
    try:
        if show_output:
            # Show real-time output for long-running commands
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Stream output in real-time
            for line in process.stdout:
                print(line, end='')
            
            process.wait()
            
            if process.returncode == 0:
                print("-" * 80)
                print(f"SUCCESS: {description}")
                return True
            else:
                print("-" * 80)
                print(f"ERROR: {description} failed with return code {process.returncode}")
                return False
        else:
            # Capture output for quick commands
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            print(f"SUCCESS: {description}")
            if result.stdout:
                print(result.stdout)
            return True
            
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {description} failed")
        print(f"Return code: {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False
    except KeyboardInterrupt:
        print("\n\nINTERRUPTED: Installation cancelled by user")
        return False


def main():
    """Main installation function."""
    print("="*80)
    print("FlowSA v2.0.3 Installation")
    print("="*80)
    print(f"Target version: {FLOWSA_VERSION_EXPECTED}")
    print(f"Installing from GitHub release tag: {FLOWSA_GIT_TAG}")
    print("="*80)
    
    # Get Python executable
    python_exe = sys.executable
    python_version = sys.version_info
    print(f"\nUsing Python: {python_exe}")
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check Python version compatibility
    if python_version.major != 3 or python_version.minor < 9 or python_version.minor > 11:
        print("\n" + "="*80)
        print("ERROR: Incompatible Python Version")
        print("="*80)
        print(f"You have Python {python_version.major}.{python_version.minor}")
        print(f"FlowSA v2.0.3 requires Python 3.9, 3.10, or 3.11")
        print("")
        print("Python 3.14 is too new - pandas 2.0.3 cannot build on it!")
        print("")
        print("Solutions:")
        print("  1. Create a new venv with Python 3.11:")
        print("     py -3.11 -m venv .venv")
        print("     .venv\\Scripts\\activate")
        print("     python install_flowsa_2.0.3.py")
        print("")
        print("  2. Download Python 3.11 from: https://www.python.org/downloads/")
        print("")
        print("See PYTHON_VERSION_FIX.md for detailed instructions")
        print("="*80)
        return False
    
    # Step 1: Uninstall existing FlowSA
    print("\n" + "="*80)
    print("STEP 1: Uninstalling existing FlowSA")
    print("="*80)
    
    uninstall_cmd = [python_exe, "-m", "pip", "uninstall", "-y", "flowsa"]
    if not run_command(uninstall_cmd, "Uninstalling FlowSA"):
        print("Warning: Uninstall may have failed, but continuing...")
    
    # Step 2: Install FlowSA from specific git release tag
    print("\n" + "="*80)
    print("STEP 2: Installing FlowSA v2.0.3 from GitHub release tag")
    print("="*80)
    print("\nNOTE: This step typically takes 2-5 minutes as it:")
    print("  - Clones the FlowSA repository from GitHub")
    print(f"  - Checks out the release tag ({FLOWSA_GIT_TAG})")
    print("  - Builds and installs all dependencies")
    print("\nPlease be patient... (Press Ctrl+C to cancel if needed)")
    
    install_url = f"git+https://github.com/USEPA/flowsa.git@{FLOWSA_GIT_TAG}"
    install_cmd = [python_exe, "-m", "pip", "install", install_url]
    
    # Show real-time output for this long-running command
    if not run_command(install_cmd, "Installing FlowSA v2.0.3", show_output=True):
        print("\nERROR: Installation failed!")
        print("\nTroubleshooting:")
        print("1. Ensure git is installed and in PATH")
        print("2. Check internet connection")
        print("3. Try manual installation:")
        print(f"   pip install {install_url}")
        return False
    
    # Step 3: Verify installation
    print("\n" + "="*80)
    print("STEP 3: Verifying installation")
    print("="*80)
    
    try:
        import flowsa
        import importlib.metadata
        
        installed_version = importlib.metadata.version('flowsa')
        print(f"Installed FlowSA version: {installed_version}")
        
        # Try to get git hash
        try:
            from pathlib import Path
            flowsa_path = Path(flowsa.__file__).parent
            
            result = subprocess.run(
                ['git', 'rev-parse', '--short=7', 'HEAD'],
                cwd=flowsa_path,
                capture_output=True,
                text=True,
                check=True
            )
            git_hash = result.stdout.strip()
            print(f"Installed git hash: {git_hash}")
            
            if git_hash == FLOWSA_SHORT_HASH:
                print("\nSUCCESS: Correct version installed!")
            else:
                print(f"\nWARNING: Git hash mismatch!")
                print(f"  Expected: {FLOWSA_SHORT_HASH}")
                print(f"  Got: {git_hash}")
        except:
            print("Note: Could not verify git hash (git not available)")
        
        if installed_version == FLOWSA_VERSION_EXPECTED:
            print(f"\nSUCCESS: FlowSA v{installed_version} installed correctly!")
            print(f"Installed from GitHub release tag: {FLOWSA_GIT_TAG}")
            print("\nYou can now run:")
            print("  python run_extraction.py")
            return True
        else:
            print(f"\nWARNING: Version mismatch!")
            print(f"  Expected: {FLOWSA_VERSION_EXPECTED}")
            print(f"  Got: {installed_version}")
            print(f"\nInstalled from tag: {FLOWSA_GIT_TAG}")
            return False
            
    except ImportError as e:
        print(f"\nERROR: Could not import FlowSA after installation!")
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    print("\n")
    success = main()
    
    print("\n" + "="*80)
    if success:
        print("Installation completed successfully!")
    else:
        print("Installation completed with warnings/errors.")
        print("Please review the output above.")
    print("="*80)
    
    sys.exit(0 if success else 1)
