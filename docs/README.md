# USEEIO GHG Sources Disaggregation – Interactive Sunburst

This directory contains the interactive D3.js sunburst visualization for exploring USEEIO Scope 1 emissions disaggregated by GHG source.

## Quick Start

1. Open `index.html` in a web browser
2. Select a USEEIO sector from the dropdown
3. Hover over sunburst slices or table rows to explore hierarchical paths
4. Adjust minimum contribution filter to show/hide small contributors

## Files

- `index.html` - Main HTML page with layout and controls
- `styles.css` - Dark theme styling with CSS custom properties
- `sunburst.js` - D3.js visualization logic (~585 lines)
- `data/` - Data files for the visualization
  - `GHG_national_2022_m2_DecarbNexus_sunburst.json` - Aggregated emissions data (~3,901 records)
  - `sector_classification.csv` - USEEIO sector names and classifications

## Features

### Interactive Elements
- **Sector selection** with fuzzy search (searches both code and name)
- **Sunburst chart** with three hierarchical rings
- **Side tables** showing breakdowns for each ring
- **Breadcrumb path** displays current selection above the chart
- **Center label** shows contribution percentage in the sunburst hole
- **Bidirectional highlighting** - hover on any element highlights its full hierarchical path

### Hierarchy Structure (Fixed Order)
1. **Inner Ring: Activity Category** (3 categories, fixed order)
   - Electric Power Generation (#0099CC blue)
   - Fossil Fuels Combustion (#FF6B6B red)
   - Process & Fugitive Gases (#9C27B0 purple)
2. **Middle Ring: Activity Set** - Specific activities within each category (all displayed, sorted by contribution)
3. **Outer Ring: Gas Category** - Individual greenhouse gases (all displayed, sorted by contribution)

### Interaction Behavior
- **Hover on sunburst slice**: Highlights the slice + all ancestors + all descendants, updates breadcrumb and center value
- **Hover on table row**: Same highlighting behavior as slice hover
- **Click on table row**: Toggles persistent highlight (click again to clear)
- **Minimum contribution filter**: Dynamically filters sunburst slices (default: 0%)

## Data Format

The sunburst JSON contains aggregated data with 5 columns:
```json
{
  "USEEIO Sector Code": "111120",
  "Activity Category": "Fuels Combustion",
  "Activity Set": "Natural Gas",
  "Gas Category": "Carbon dioxide",
  "Contribution to USEEIO Sector's Scope 1 (%)": 0.234
}
```

**Important**: Contributions are stored as decimals (0-1 scale), where 1.0 = 100%. The UI displays them as percentages.

## Technical Details

### Color Scheme
```css
--source-electric: #0099CC   /* Electric Power Generation */
--source-fossil: #FF6B6B     /* Fossil Fuels Combustion */
--source-process: #9C27B0    /* Process & Fugitive Gases */
--accent: #00D9EA            /* Accent color for highlights */
--bg: #111111                /* Dark background */
--panel: #222222             /* Panel background */
```

### Key Functions in sunburst.js

#### Data Loading
- `loadJSON(urls, label)` - Multi-fallback URL loading strategy
- `tryLoadClassification()` - Loads sector names from CSV

#### Visualization Rendering
- `buildHierarchy(data, minShare)` - Converts flat data to D3 hierarchy using `d3.rollup()`
- `renderSunburst(data, sectorCode, sectorName, minShare)` - Creates the sunburst chart
  - Sorts inner ring by fixed order (Electric, Fossil, Process)
  - Sorts other rings by contribution (largest first)
  - Stores `window.currentSunburstRoot` for highlighting

#### Interactive Highlighting
- `highlightPathFromNode(node)` - Highlights a node + descendants + ancestors
  - Creates a Set with the node and all related nodes
  - Dims non-matching arcs to opacity 0.3
  - Keeps matching arcs at opacity 0.9
- `highlightPath(name, depth)` - Finds nodes by name and depth, then calls highlightPathFromNode
- `clearHighlight()` - Restores all arcs to opacity 0.9

#### UI Updates
- `updateBreadcrumb(pathArray)` - Displays hierarchical path with "▸" separators
- `getPathForItem(name, depth)` - Constructs path array for table items
- `renderRingBreakdown(data, sectorCode)` - Creates the three side tables
  - Inner Ring: Shows all 3 categories with color swatches
  - Middle Ring: Shows all activity sets (sorted by contribution)
  - Outer Ring: Shows all gas categories (sorted by contribution)

### Layout
- CSS Grid: `grid-template-columns: 1fr 320px` (chart left, tables right)
- Responsive breakpoint at 900px (stacks vertically on mobile)
- Chart area: 520px with border and rounded corners
- Tables: Fixed 320px width, scrollable if needed

## Local Testing

The visualization uses a multi-fallback loading strategy:

1. **Same-origin** (fastest): `data/GHG_national_2022_m2_DecarbNexus_sunburst.json`
2. **GitHub raw** (fallback): `https://raw.githubusercontent.com/...`
3. **Relative paths** (local dev): `../outputs/`, `../data/`

Simply open `index.html` in a browser - no server needed (though CORS may block some fallbacks).

For local development with a server:
```bash
# Python 3
python -m http.server 8000

# Then open http://localhost:8000
```

## Deployment to GitHub Pages

1. Ensure all files are in the `docs/` folder
2. Commit and push to the `main` branch
3. Enable GitHub Pages in repository settings:
   - Settings → Pages
   - Source: Deploy from a branch
   - Branch: main
   - Folder: /docs
   - Save

The visualization will be available at:
`https://decarbnexus.github.io/Flowsa_extract_GHG_sources/`

### Auto-Update Workflow

The `.github/workflows/update-docs-data.yml` workflow automatically copies updated data files to `docs/data/` when changes are pushed to `outputs/` or `data/` directories.

## For Future Development

### Adding a New Feature
1. **Locate the relevant section** in `sunburst.js`:
   - Data loading: lines 1-80
   - Hierarchy building: lines 82-120
   - Sunburst rendering: lines 122-230
   - Ring breakdown tables: lines 380-520
   - Highlighting logic: lines 320-370

2. **Styling**: Add CSS to `styles.css` using existing CSS custom properties for consistency

3. **Testing**: Test with multiple sectors (especially edge cases like sectors with few sources)

### Common Modifications
- **Change ring order**: Modify the `order` array in `renderSunburst()` (line ~145)
- **Add new color**: Define in `:root` CSS variables and update `color` scale domain
- **Adjust table display**: Modify `renderRingBreakdown()` - remove `.slice()` limits or change sorting
- **Change minimum filter default**: Update `value="0"` in `index.html` input element

### Code Style
- **Indentation**: 2 spaces
- **Naming**: camelCase for functions and variables
- **D3 patterns**: Use method chaining, `.join()` for enter/update/exit
- **Comments**: Include explanatory comments for complex logic (hierarchy building, highlighting)

## Credits

- **Data Sources:** [USEEIO](https://github.com/USEPA/useeior/) & [FLOWSA](https://github.com/USEPA/flowsa)
- **Visualization:** D3.js v7
- **Font:** Lato (Google Fonts)
- **License:** Data is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
