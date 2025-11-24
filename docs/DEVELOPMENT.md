# Development Guide - GHG Sources Sunburst Visualization

## For AI Coding Assistants

This guide helps AI assistants quickly understand and modify the visualization codebase.

### The Vibe
- **Aesthetic:** Dark sci-fi (black bg, cyan/blue/purple accents)
- **Interaction:** Hover to explore, click to lock highlights
- **Philosophy:** Show the full hierarchy - when you hover on a node, you see its entire family tree (parents + children)
- **Data:** Always decimals (0-1), display as percentages
- **Performance:** Lightweight (~500KB JSON), instant updates

### Quick Architecture

```
User hovers → Event handler → Build highlight Set → Dim non-matches → Update UI
                ↓
        Find D3 node → Add ancestors + descendants → Apply to arcs
```

### Critical Code Locations

| What | Where | Line |
|------|-------|------|
| Arc hover events | `sunburst.js` | ~207-217 |
| Highlighting logic | `highlightPathFromNode()` | ~320-340 |
| Table rendering | `renderRingBreakdown()` | ~380-520 |
| Color scheme | `styles.css` | ~2-12 |
| Ring order | `renderSunburst()` sort | ~145-155 |
| Data loading | `loadJSON()` | ~1-80 |

## Common Modifications

### 1. Fix Arc Hover Not Working
**Symptom:** Hovering on sunburst slices doesn't highlight or update breadcrumb

**Solution:**
```javascript
// BAD (doesn't work on SVG paths)
.on("mouseenter", handler)
.on("mouseleave", handler)

// GOOD (works on SVG paths)
.on("mouseover", handler)
.on("mouseout", handler)
```

**Why:** D3 path elements don't reliably fire `mouseenter`/`mouseleave` events. Use `mouseover`/`mouseout` instead.

### 2. Change Highlighting Behavior
**Current:** Highlights node + all ancestors + all descendants

**To show only the node:**
```javascript
function highlightPathFromNode(node) {
  const highlightSet = new Set([node]); // Only the node itself
  // ... rest of function
}
```

**To show only ancestors (path to root):**
```javascript
function highlightPathFromNode(node) {
  const highlightSet = new Set();
  node.ancestors().forEach(d => highlightSet.add(d));
  // ... rest of function
}
```

### 3. Add/Remove Table Row Limit
**Show top N only:**
```javascript
const ring2Array = Array.from(ring2Data, ([name, value]) => ({name, value}))
  .sort((a, b) => b.value - a.value)
  .slice(0, 10); // Take only top 10
```

**Show all (current state):**
```javascript
const ring2Array = Array.from(ring2Data, ([name, value]) => ({name, value}))
  .sort((a, b) => b.value - a.value);
  // No .slice() - shows everything
```

### 4. Change Color Palette
**Step 1:** Edit CSS variables in `styles.css`
```css
:root {
  --source-electric: #0099CC;  /* Your color here */
  --source-fossil: #FF6B6B;    /* Your color here */
  --source-process: #9C27B0;   /* Your color here */
}
```

**Step 2:** Update color scale domain in `sunburst.js` (if category names changed)
```javascript
const color = d3.scaleOrdinal()
  .domain(["Electric Power Generation", "Fossil Fuels Combustion", "Process & Fugitive Gases"])
  .range([
    getComputedStyle(document.documentElement).getPropertyValue('--source-electric').trim(),
    getComputedStyle(document.documentElement).getPropertyValue('--source-fossil').trim(),
    getComputedStyle(document.documentElement).getPropertyValue('--source-process').trim()
  ]);
```

### 5. Adjust Layout (Chart vs Tables)
**Current:** Chart takes up remaining space, tables are fixed 320px

```css
/* In styles.css */
#chart-container {
  display: grid;
  grid-template-columns: 1fr 320px; /* Chart | Tables */
  gap: 1.5rem;
}

/* To make tables wider: */
grid-template-columns: 1fr 400px;

/* To make chart narrower: */
grid-template-columns: 600px 320px;

/* 50/50 split: */
grid-template-columns: 1fr 1fr;
```

### 6. Change Breadcrumb Separator
**Current:** Uses "▸" (U+25B8 Black Right-Pointing Small Triangle)

```javascript
// In updateBreadcrumb()
return `<span class="separator">▸</span><span class="path">${name}</span>`;

// Change to arrow:
return `<span class="separator">→</span><span class="path">${name}</span>`;

// Change to slash:
return `<span class="separator">/</span><span class="path">${name}</span>`;
```

## Understanding the Hierarchy

### Data Transformation Flow
```
Flat JSON → d3.rollup() → Nested Map → D3 Hierarchy → Partition Layout → Arcs
```

**Example:**
```javascript
// Input (flat)
[
  {category: "Fossil", activity: "Coal", gas: "CO2", value: 0.5},
  {category: "Fossil", activity: "Coal", gas: "CH4", value: 0.1}
]

// After d3.rollup()
Map {
  "Fossil" => Map {
    "Coal" => Map {
      "CO2" => 0.5,
      "CH4" => 0.1
    }
  }
}

// After buildHierarchy() → D3 hierarchy
root
└─ Fossil (0.6)
   └─ Coal (0.6)
      ├─ CO2 (0.5)
      └─ CH4 (0.1)
```

### Node Properties (D3 Hierarchy)
```javascript
node.depth        // 0 = root, 1 = inner ring, 2 = middle, 3 = outer
node.data.name    // Category/Activity/Gas name
node.value        // Sum of all descendant values
node.parent       // Parent node (or null for root)
node.ancestors()  // [node, parent, grandparent, ..., root]
node.descendants() // [node, child1, child2, grandchild1, ...]
```

## Debugging Tips

### Check if Data Loaded
```javascript
// In browser console
console.log(window.currentSunburstRoot);
// Should show D3 hierarchy object with data
```

### Inspect Highlighted Nodes
Add to `highlightPathFromNode()`:
```javascript
console.log("Highlighting nodes:", Array.from(highlightSet).map(n => n.data.name));
```

### Verify Event Listeners
Add to arc event handlers:
```javascript
.on("mouseover", (event, d) => {
  console.log("Hovered on:", d.data.name, "depth:", d.depth);
  // ... rest of handler
})
```

### Check CSS Variables
```javascript
// In browser console
const style = getComputedStyle(document.documentElement);
console.log("Electric color:", style.getPropertyValue('--source-electric'));
```

## Performance Considerations

### Why Aggregated Data?
- **Full dataset:** 8,772 records, ~25MB
- **Sunburst JSON:** 3,901 records, ~500KB
- **Reason:** Unique combinations only, no duplicates
- **Speed:** Instant loading, no lag on re-render

### Why Store Root in Global?
```javascript
window.currentSunburstRoot = root;
```
- **Reason:** Table rows need to query hierarchy to find matching nodes
- **Alternative:** Pass root to `renderRingBreakdown()` - more "pure" but requires threading it through
- **Tradeoff:** Global is simpler, no noticeable downsides in this use case

### Transition Duration
```javascript
.transition().duration(200)  // 200ms for highlight changes
```
- **Too fast (<100ms):** Feels jarring
- **Too slow (>300ms):** Feels laggy
- **Sweet spot:** 150-250ms for smooth but responsive feel

## Common Gotchas

### 1. Decimal vs Percentage Confusion
```javascript
// Data is stored as 0.234 (not 23.4)
// Display as percentage:
formatPct(0.234)  // "23.4%"

// Don't do this:
centerLabel.text(d.value + "%")  // Shows "0.234%" ❌
```

### 2. Ring Depth Off-by-One
```javascript
// Ring numbering (user-facing): Inner=1, Middle=2, Outer=3
// D3 depth: root=0, inner=1, middle=2, outer=3

// When matching table items to nodes:
const matchingNode = root.descendants().find(d => 
  d.depth === ringDepth  // ringDepth is 1, 2, or 3
  && d.data.name === name
);
```

### 3. Fixed Ring Order Only Applies to Inner Ring
```javascript
// Inner ring (depth 1): Fixed order
const order = ["Electric Power Generation", "Fossil Fuels Combustion", "Process & Fugitive Gases"];

// Middle and outer rings: Sorted by value (largest first)
return (b.value || 0) - (a.value || 0);
```

### 4. Header Rows Must Be Excluded
```css
/* Wrong - makes header clickable */
.ring-table tr { cursor: pointer; }

/* Right - only tbody rows */
.ring-table tbody tr { cursor: pointer; }
```

## Testing Checklist

Before deploying changes:
- [ ] Test with multiple sectors (especially edge cases: single source, many sources)
- [ ] Verify hover on all 3 rings highlights correctly
- [ ] Check table row hover/click works
- [ ] Test breadcrumb updates on hover
- [ ] Verify center label shows percentage
- [ ] Adjust min contribution filter (0%, 1%, 5%)
- [ ] Resize window to test responsive layout (<900px)
- [ ] Open browser console, check for errors
- [ ] Inspect network tab, verify data loads
- [ ] Test in Chrome, Firefox, Safari

## File Modification Summary

When making changes, here's what each file controls:

| File | Purpose | When to Edit |
|------|---------|--------------|
| `index.html` | Page structure, controls | Add new UI elements, change layout |
| `styles.css` | Visual styling | Change colors, spacing, responsive behavior |
| `sunburst.js` | Visualization logic | Modify interactions, data processing, rendering |
| `README.md` | User documentation | Explain features to end users |
| `DEVELOPMENT.md` | Developer guide | Help future coders understand the system |
| `VISUALIZATION_SETUP.md` | Technical reference | Quick reference for common tasks |

## Version Control

When committing changes, use descriptive messages:
```bash
# Good commit messages
git commit -m "Fix arc hover events (mouseenter → mouseover)"
git commit -m "Remove Activity Set top 10 limit, show all"
git commit -m "Add breadcrumb path display above chart"

# Bad commit messages
git commit -m "Fix bug"
git commit -m "Update sunburst.js"
git commit -m "Changes"
```

## Need Help?

1. **Check browser console** - Most issues show errors here
2. **Review README.md** - Covers user-facing features
3. **Check VISUALIZATION_SETUP.md** - Technical quick reference
4. **Read this file** - Covers common modifications
5. **Inspect the code** - Well-commented, ~585 lines total
