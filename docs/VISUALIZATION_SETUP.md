# Interactive Sunburst Visualization - Technical Guide

## Overview

This is a D3.js-based interactive sunburst chart for exploring USEEIO Scope 1 emissions disaggregated by GHG source. The visualization follows a dark theme aesthetic with cyan/blue/purple color scheme.

## Quick Reference

### File Structure
```
docs/
├── index.html              # Main page with layout and controls
├── styles.css              # Dark theme with CSS custom properties
├── sunburst.js             # D3.js visualization logic (~585 lines)
├── README.md               # Detailed documentation
├── VISUALIZATION_SETUP.md  # This file
└── data/
    ├── GHG_national_2022_m2_DecarbNexus_sunburst.json  # ~3,901 records
    └── sector_classification.csv                        # USEEIO sector names
```

### Visual Hierarchy (Fixed, 3 Rings)
1. **Inner Ring: Activity Category** (3 categories, fixed order)
   - Electric Power Generation (#0099CC blue)
   - Fossil Fuels Combustion (#FF6B6B red)
   - Process & Fugitive Gases (#9C27B0 purple)
2. **Middle Ring: Activity Set** - All activities within each category
3. **Outer Ring: Gas Category** - All individual greenhouse gases

### Interaction Model
- **Hover on sunburst slice** → Highlights full path (ancestors + descendants), shows breadcrumb + center value
- **Hover on table row** → Same as slice hover
- **Click on table row** → Toggles persistent highlight
- **Minimum contribution filter** → Dynamically filters small slices (default 0%)

## Color Scheme

```css
/* GHG Source Categories */
--source-electric: #0099CC   /* Electric Power Generation */
--source-fossil: #FF6B6B     /* Fossil Fuels Combustion */
--source-process: #9C27B0    /* Process & Fugitive Gases */

/* UI Colors */
--accent: #00D9EA            /* Highlights and interactive elements */
--bg: #111111                /* Page background */
--panel: #222222             /* Chart/table panel background */
--border: #333333            /* Subtle borders */
--text: #EEEEEE              /* Primary text */
--muted: #999999             /* Secondary text */
```

## Key Technical Details

### Data Format
- **Input:** Aggregated JSON with 5 columns
- **Contribution scale:** Decimal (0-1), where 1.0 = 100%
- **Aggregation:** Groups by 3 categorical columns, sums contributions
- **File size:** ~500KB (vs 25MB+ full dataset)

### D3.js Architecture

#### Data Pipeline
```javascript
loadJSON() 
  → buildHierarchy() 
  → d3.partition() 
  → renderSunburst() 
  → renderRingBreakdown()
```

#### Highlighting System
```javascript
// On hover (slice or table):
1. Get node from D3 hierarchy
2. Build Set: node + descendants + ancestors
3. Dim non-matching arcs (opacity 0.3)
4. Keep matching arcs bright (opacity 0.9)
5. Update breadcrumb path
6. Update center label with contribution %
```

### Layout
- **Chart container:** CSS Grid `1fr 320px` (chart | tables)
- **Responsive:** Stacks vertically at 900px breakpoint
- **Chart:** 520px square SVG with viewBox scaling
- **Tables:** Fixed 320px width, scrollable tbody

## Common Customizations

### Change Color Palette
Edit CSS custom properties in `styles.css`:
```css
:root {
  --source-electric: #0099CC;  /* Change this */
  --source-fossil: #FF6B6B;    /* Change this */
  --source-process: #9C27B0;   /* Change this */
}
```

### Change Ring Order
Edit the fixed order array in `sunburst.js` (line ~145):
```javascript
const order = ["Electric Power Generation", "Fossil Fuels Combustion", "Process & Fugitive Gases"];
```

### Show All Activity Sets (No Limit)
Already configured - all activity sets are displayed, sorted by contribution.

### Adjust Default Filter
Edit `index.html` (line ~40):
```html
<input id="minPct" type="number" value="0" ... />
```

### Change Highlight Duration
Edit transition duration in `sunburst.js` (line ~360):
```javascript
.transition().duration(200)  // Change to desired milliseconds
```

## Code Structure (sunburst.js)

### Main Functions

| Function | Purpose | Lines |
|----------|---------|-------|
| `loadJSON()` | Multi-fallback data loading | 1-80 |
| `buildHierarchy()` | Converts flat data to D3 hierarchy | 82-120 |
| `renderSunburst()` | Creates sunburst chart with arcs | 122-230 |
| `renderRingBreakdown()` | Creates side tables | 380-520 |
| `highlightPathFromNode()` | Highlights node + family | 320-340 |
| `highlightPath()` | Finds and highlights by name | 342-370 |
| `updateBreadcrumb()` | Updates path display | 300-318 |
| `populateSelect()` | Fills sector dropdown | 560-585 |

### Event Handlers
- **Arc mouseover/mouseout** → Updates breadcrumb, center label, highlights path
- **Table row mouseenter/mouseleave** → Same as arc hover
- **Table row click** → Toggles persistent highlight
- **Sector select change** → Re-renders entire visualization
- **Min contribution input** → Filters sunburst dynamically

## Deployment

### GitHub Pages Setup
1. Commit all `docs/` files
2. Settings → Pages → Source: main → Folder: /docs
3. Live at: `https://decarbnexus.github.io/Flowsa_extract_GHG_sources/`

### Auto-Update Workflow
`.github/workflows/update-docs-data.yml` watches for changes to:
- `outputs/GHG_national_2022_m2_DecarbNexus_sunburst.json`
- `data/sector_classification.csv`

On push, it copies updated files to `docs/data/` and commits.

## Local Testing

### Python HTTP Server (Recommended)
```bash
cd docs
python -m http.server 8000
# Open http://localhost:8000
```

### Direct File Open
Open `index.html` in browser (may have CORS restrictions for fallback URLs).

## For AI Assistants / Future Development

### Understanding the Codebase

**"What's the vibe?"**
- Dark sci-fi aesthetic (black background, cyan accents)
- Clean, minimalist UI
- Emphasis on exploration (hover to discover, click to lock)
- Full hierarchy visibility (no hidden parents/children when highlighting)

**"How does highlighting work?"**
- Every node knows its full ancestry via D3's hierarchy
- On hover: collect node + `.descendants()` + `.ancestors()` into a Set
- Dim everything to 0.3 opacity, except Set members (keep 0.9)
- Use `mouseover`/`mouseout` events (not mouseenter/mouseleave) for D3 path elements

**"How do I add a new ring level?"**
- This visualization is intentionally fixed at 3 rings (hierarchy is GHG Source → Activity → Gas)
- Adding a 4th ring would require restructuring `buildHierarchy()` and the data schema
- Not recommended unless data model changes

**"How do I change what data is shown in tables?"**
- Edit `renderRingBreakdown()` function
- Ring data is aggregated via `d3.rollup()`
- Remove `.slice()` calls to show all items (already done for Middle Ring)
- Sort order: `(a, b) => b.value - a.value` (largest first)

**"Why the multi-fallback loading?"**
- GitHub Pages serves from `docs/`, so `data/file.json` is same-origin (fast)
- Fallback to raw.githubusercontent.com for resilience
- Local dev fallback to `../outputs/` and `../data/`
- Order matters: try fastest/most reliable first

**"What's with the decimal vs percentage thing?"**
- Data stored as decimals (0.234 = 23.4%)
- UI displays as percentages using `d3.format(".1%")`
- This is intentional for precision and consistency with Python output

### Common Tasks

**Task: Debug highlighting issue**
1. Check `window.currentSunburstRoot` is set (stores D3 hierarchy)
2. Verify event listeners use `mouseover`/`mouseout` (not mouseenter/leave)
3. Console log the highlight Set to see what nodes are included
4. Check that `.arc-segment` class is on all paths

**Task: Change table content**
1. Find `renderRingBreakdown()` function
2. Modify `d3.rollup()` aggregation for each ring
3. Adjust `.slice()` or `.filter()` to control displayed items
4. Update table title to reflect changes

**Task: Add new control**
1. Add HTML input/select in `index.html`
2. Add event listener in `init()` function
3. Pass new parameter to `renderSunburst()` or `buildHierarchy()`
4. Update visualization logic to use parameter

**Task: Style adjustment**
1. Edit CSS custom properties in `:root` for color changes
2. Edit specific selectors for layout changes
3. Test responsive behavior at 900px breakpoint

## Data License

- **License:** CC BY 4.0
- **Source:** USEEIO & FLOWSA (EPA)
- **Attribution:** Displayed in footer

## Version History

- **v1.0** - Initial release with 3-ring sunburst, sector selection, min filter
- **v1.1** - Added ring breakdown tables with color-coded legend
- **v1.2** - Enhanced highlighting (bidirectional path), removed tooltip, added breadcrumb + center label
- **v1.3** - Removed Top 10 limit on Activity Set, fixed arc hover events (mouseenter→mouseover)

## Support

For issues or questions:
1. Check browser console (F12) for errors
2. Review `docs/README.md` for detailed documentation
3. Inspect Network tab to verify data loading
4. Test in different browser (Chrome, Firefox, Safari)
5. Verify `currentSunburstRoot` exists in console
