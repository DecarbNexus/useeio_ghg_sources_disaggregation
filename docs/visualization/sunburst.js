// USEEIO GHG Sources Disaggregation – Interactive Sunburst
// - Loads event-based sunburst JSON from GitHub
// - Lets user select a USEEIO Sector
// - 3-level hierarchy: Activity Category -> Activity Type -> Gas Category
// - Uses optimized D3.js format (no JSON-LD transformation needed)

// Repo configuration
const OWNER = "DecarbNexus";
const REPO = "Flowsa_extract_GHG_sources";
const DATA_FILENAME = "industry_sunburst.json"; // D3.js hierarchy format
const CLASS_FILENAME = "sector_classification.jsonld"; // JSON-LD format

// Data URLs - prefer GitHub Pages deployment, fallback to repo
const DATA_URLS = [
  // Same-origin (GitHub Pages)
  "data/" + DATA_FILENAME,
  // Raw from main branch (industry subdirectory)
  `https://raw.githubusercontent.com/${OWNER}/${REPO}/main/outputs/industry/${DATA_FILENAME}`,
  // Relative path for local testing
  "../outputs/industry/" + DATA_FILENAME,
];

const CLASS_URLS = [
  // Same-origin (GitHub Pages)
  "data/" + CLASS_FILENAME,
  // Raw from main branch
  `https://raw.githubusercontent.com/${OWNER}/${REPO}/main/docs/data/${CLASS_FILENAME}`,
  // Relative path for local testing
  "../docs/data/" + CLASS_FILENAME,
];

// Dynamic sizing
let WIDTH = 700;
let RADIUS = WIDTH / 2;

const formatPct = d3.format(".1%");
const formatNum = d3.format(",.4f");

const breadcrumb = d3.select("#breadcrumb");
const centerLabel = d3.select("#centerLabel");
const tooltip = d3.select("#tooltip");

// Track persistent selection (click to lock)
let persistentSelection = null;

// Detect touch device - use matchMedia for more accurate detection
const isTouchDevice = window.matchMedia("(pointer: coarse)").matches;
let tooltipTimeout = null;
let lastTappedNode = null;

// Chart scale factor
const CHART_SCALE = 0.75; // 75% of container width

async function loadJSON(urls, description) {
  let lastErr;
  for (const url of urls) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      console.log(`Loaded ${description} from: ${url} (records: ${data.length || Object.keys(data).length})`);
      return data;
    } catch (e) {
      lastErr = e;
      continue;
    }
  }
  throw new Error(`Failed to load ${description} from any URL: ` + lastErr);
}

async function tryLoadClassification() {
  let lastErr;
  for (const url of CLASS_URLS) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const jsonld = await res.json();
      
      // Extract from JSON-LD format
      const graph = jsonld['@graph'] || [];
      
      const map = new Map();
      
      // Process each category in the graph
      for (const category of graph) {
        const subcategories = category.subcategories || [];
        
        for (const subcategory of subcategories) {
          const sectors = subcategory.sectors || [];
          
          for (const sector of sectors) {
            const code = sector.sector_code;
            const name = sector.sector_name || sector.commodity_name || code;
            
            if (code) {
              map.set(code, { sector_name: name });
            }
          }
        }
      }

      console.log(`Loaded sector classification from: ${url} (sectors: ${map.size})`);
      return { map };
    } catch (e) {
      lastErr = e;
      continue;
    }
  }
  console.warn("Classification JSON-LD not found; defaulting to sector codes.", lastErr);
  return { map: new Map() };
}

function buildHierarchy(hierarchyData, sectorCode) {
  // Data is in D3.js hierarchy format with USEEIO sectors as root children
  // Structure: root → USEEIO sectors → GHG categories → ... → gases
  
  if (!hierarchyData || !hierarchyData.children) {
    console.error("Invalid hierarchy data structure");
    return { name: "No Data", children: [] };
  }
  
  // Find the selected sector in the hierarchy
  const sectorNode = hierarchyData.children.find(d => 
    d.useeio_code === sectorCode || d.name === sectorCode
  );
  
  if (!sectorNode) {
    console.warn(`Sector ${sectorCode} not found in data`);
    return { name: "Sector Not Found", children: [] };
  }
  
  // Return the sector's subtree
  return {
    name: sectorNode.name || sectorCode,
    useeio_code: sectorNode.useeio_code,
    children: sectorNode.children || []
  };
}

function renderSunburst(rootData, centerLabel, minShare) {
  // NEW: Color by category type (more levels now)
  const colorByCategory = d3.scaleOrdinal()
    .domain(['activity_category', 'activity_type', 'gas_category'])
    .range(['#0099CC', '#FF6B6B', '#9C27B0', '#4CAF50', '#FF9800', '#00BCD4', '#E91E63']);
  
  // Color by specific GHG Source Categories
  const colorByName = d3.scaleOrdinal()
    .domain([
      "Electric Power Generation",
      "Fuel Combustion",
      "Process & Fugitive Gases"
    ])
    .range(["#0099CC", "#FF6B6B", "#9C27B0"]);
  


  // Compute container size and scale down
  const container = document.getElementById("chart");
  const maxW = Math.min(900, (container.clientWidth || 700));
  const size = Math.max(315, Math.floor(maxW * CHART_SCALE));
  WIDTH = size;
  RADIUS = size / 2;

  const partition = d3.partition().size([2 * Math.PI, RADIUS]);

  const root = d3.hierarchy(rootData)
    .sum((d) => d.contributionToUSEEIOSectorScope1Percent || d.value || 0)
    .sort((a, b) => {
      // Sort siblings
      if (a.parent && b.parent && a.parent === b.parent) {
        // First ring: fixed order Electric Power, Fuel, Process & Fugitive
        if (a.depth === 1) {
          const order = ["Electric Power Generation", "Fuel Combustion", "Process & Fugitive Gases"];
          const aIdx = order.indexOf(a.data.name);
          const bIdx = order.indexOf(b.data.name);
          if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx;
        }
        // All other rings: sort by value (largest first)
        return (b.value || 0) - (a.value || 0);
      }
      return 0;
    });

  partition(root);

  d3.select("#chart").selectAll("svg").remove();

  const svg = d3
    .select("#chart")
    .append("svg")
    .attr("viewBox", [0, 0, WIDTH, WIDTH])
    .style("width", WIDTH + "px")
    .style("height", WIDTH + "px");

  const g = svg.append("g").attr("transform", `translate(${RADIUS},${RADIUS})`);

  const arc = d3
    .arc()
    .startAngle((d) => d.x0)
    .endAngle((d) => d.x1)
    .padAngle(1 / RADIUS)
    .padRadius(RADIUS / 3)
    .innerRadius((d) => d.y0)
    .outerRadius((d) => d.y1 - 1);

  const total = root.value || 1;

  const isVisible = (d) => {
    if (d.depth <= 1) return true; // always show center and first ring
    const share = (d.value || 0) / total;
    return share >= (minShare || 0);
  };

  const path = g
    .append("g")
    .selectAll("path")
    .data(root.descendants().filter((d) => d.depth))
    .join("path")
    .attr("display", (d) => (d.depth && isVisible(d) ? null : "none"))
    .attr("d", arc)
    .attr("fill", (d) => {
      // All rings inherit color from their depth-1 parent (Activity Category)
      let cur = d;
      while (cur.depth > 1) cur = cur.parent;
      return colorByName(cur.data.name) || "#93c5fd";
    })
    .attr("fill-opacity", 0.9)
    .attr("class", "arc-segment")
    .style("cursor", "pointer");

  // Add event handlers separately to ensure they work
  if (!isTouchDevice) {
    // Desktop: use hover for tooltips
    path.on("mouseover", (event, d) => {
        // Show tooltip on arc hover (don't affect table highlights or persistent selection)
        const seq = d.ancestors().map((n) => n.data.name).reverse().slice(1);
        tooltip
          .style("opacity", 1)
          .html(
            `<strong>${seq.join(" ▸ ")}</strong><br/>Contribution: ${formatPct(d.value || 0)}`
          )
          .style("left", event.pageX + 10 + "px")
          .style("top", event.pageY + 10 + "px");
      })
      .on("mousemove", (event, d) => {
        tooltip
          .style("left", event.pageX + 10 + "px")
          .style("top", event.pageY + 10 + "px");
      })
      .on("mouseout", () => {
        tooltip.style("opacity", 0);
      });
  }
  
  path.on("click", (event, d) => {
      event.stopPropagation();
      
      if (isTouchDevice) {
        // Mobile: First tap shows tooltip, second tap selects
        if (tooltipTimeout) clearTimeout(tooltipTimeout);
        
        // Check if this is the same node that was just tapped
        const isSameNodeAsBefore = lastTappedNode === d;
        const tooltipVisible = parseFloat(tooltip.style("opacity")) > 0.5;
        
        if (!isSameNodeAsBefore || !tooltipVisible) {
          // First tap: show tooltip
          const seq = d.ancestors().map((n) => n.data.name).reverse().slice(1);
          
          // Get touch/click coordinates
          let x, y;
          if (event.touches && event.touches.length > 0) {
            x = event.touches[0].clientX;
            y = event.touches[0].clientY;
          } else if (event.changedTouches && event.changedTouches.length > 0) {
            x = event.changedTouches[0].clientX;
            y = event.changedTouches[0].clientY;
          } else {
            x = event.clientX;
            y = event.clientY;
          }
          
          // Position tooltip with smart placement to avoid going off-screen
          const tooltipNode = tooltip.node();
          tooltip
            .style("opacity", 1)
            .html(
              `<strong>${seq.join(" ▸ ")}</strong><br/>Contribution: ${formatPct(d.value || 0)}`
            );
          
          // Calculate position after setting content (so we know dimensions)
          const tooltipWidth = tooltipNode.offsetWidth;
          const tooltipHeight = tooltipNode.offsetHeight;
          const viewportWidth = window.innerWidth;
          const viewportHeight = window.innerHeight;
          
          // Default: 10px offset from tap
          let left = x + 10;
          let top = y + 10;
          
          // If tooltip would go off right edge, position to the left of tap
          if (left + tooltipWidth > viewportWidth - 10) {
            left = x - tooltipWidth - 10;
          }
          
          // If tooltip would go off bottom edge, position above tap
          if (top + tooltipHeight > viewportHeight - 10) {
            top = y - tooltipHeight - 10;
          }
          
          // Ensure tooltip stays on screen
          left = Math.max(10, Math.min(left, viewportWidth - tooltipWidth - 10));
          top = Math.max(10, Math.min(top, viewportHeight - tooltipHeight - 10));
          
          tooltip
            .style("left", left + "px")
            .style("top", top + "px");
          
          lastTappedNode = d;
          
          // Auto-hide tooltip after 4.5 seconds
          tooltipTimeout = setTimeout(() => {
            tooltip.style("opacity", 0);
            lastTappedNode = null;
          }, 4500);
          return; // Don't select yet
        }
        
        // Second tap: hide tooltip and proceed to selection
        tooltip.style("opacity", 0);
        lastTappedNode = null;
      } else {
        // Desktop: hide tooltip on click
        tooltip.style("opacity", 0);
      }
      
      // Toggle persistent selection
      if (persistentSelection && persistentSelection.node === d) {
        // Clicking the same arc - deselect
        persistentSelection = null;
        breadcrumb.html("");
        centerLabel.text("");
        clearHighlight();
        clearTableHighlights();
      } else {
        // New selection
        const seq = d.ancestors().map((n) => n.data.name).reverse().slice(1);
        persistentSelection = { node: d, type: 'arc' };
        updateBreadcrumb(seq);
        centerLabel.text(formatPct(d.value || 0));
        highlightPathFromNode(d);
        highlightTableRowsForNode(d);
      }
    });

  // White center disc to prevent label overlap with the first ring
  const firstRing = root.descendants().find((d) => d.depth === 1);
  const innerR = firstRing ? firstRing.y0 : RADIUS * 0.33;
  const panelColor = getComputedStyle(document.documentElement)
    .getPropertyValue('--panel') || '#111111';
  g.append("circle").attr("r", innerR - 1).attr("fill", panelColor.trim());
  
  // Store root for highlighting
  window.currentSunburstRoot = root;
  
  // Clear persistent selection when rendering new chart
  persistentSelection = null;
  
  // Add click handler to SVG background to clear selection
  svg.on('click', () => {
    if (persistentSelection) {
      persistentSelection = null;
      breadcrumb.html("");
      centerLabel.text("");
      clearHighlight();
      clearTableHighlights();
    }
  });
  
  // Add click handler to document to clear table selection when clicking outside
  document.addEventListener('click', (event) => {
    if (persistentSelection && persistentSelection.type === 'table') {
      const clickedInChart = event.target.closest('#chart-container');
      const clickedInControls = event.target.closest('.controls');
      if (!clickedInChart && !clickedInControls) {
        persistentSelection = null;
        breadcrumb.html("");
        centerLabel.text("");
        clearHighlight();
        clearTableHighlights();
      }
    }
  });
}

async function init() {
  const classData = await tryLoadClassification();
  const allData = await loadJSON(DATA_URLS, "sunburst data");

  const toName = (code) => {
    const rec = classData.map.get(code);
    return (rec && rec.sector_name) ? rec.sector_name : code;
  };

  // Get unique USEEIO sectors from the hierarchy
  // allData structure: {name: "GHG Emissions", children: [{name: "sector_code", useeio_code: "...", ...}, ...]}
  const uniqueCodes = allData.children ? allData.children.map(d => d.useeio_code).filter(Boolean) : [];
  let sectors = uniqueCodes.map((code) => ({ code, name: toName(code) }));
  sectors.sort((a, b) => d3.ascending(a.name, b.name));
  const allSectors = sectors.slice();

  const select = document.getElementById("sectorSelect");
  const search = document.getElementById("sectorSearch");
  
  function populateSelect(items, keepValue) {
    const prev = keepValue || select.value;
    while (select.firstChild) select.removeChild(select.firstChild);
    for (const s of items) {
      const opt = document.createElement("option");
      opt.value = s.code;
      opt.textContent = s.name;
      select.appendChild(opt);
    }
    // Try to keep previous value if still present
    if (prev && items.some(it => it.code === prev)) {
      select.value = prev;
    } else {
      select.selectedIndex = 0;
    }
  }

  populateSelect(allSectors);

  // Fuzzy search
  const norm = (s) => (s || "").toLowerCase();
  const isSubsequence = (q, s) => {
    let i = 0;
    for (let c of s) if (q[i] === c) i++;
    return i === q.length;
  };
  const scoreMatch = (q, name, code) => {
    if (!q) return 100;
    // exact code match highest
    if (code === q) return 1000;
    // code startswith
    if (code.startsWith(q)) return 500;
    // name startswith token
    if (name.startsWith(q)) return 400;
    // substring matches
    let sc = 0;
    if (code.includes(q)) sc += 200;
    if (name.includes(q)) sc += 150;
    // tokenized contains
    const tokens = q.split(/\s+/).filter(Boolean);
    if (tokens.length > 1) {
      if (tokens.every(t => name.includes(t))) sc += 100;
    }
    // subsequence
    if (isSubsequence(q, name.replace(/\s+/g, ''))) sc += 50;
    return sc;
  };

  // Debounce redraw
  let searchTimer = null;
  const triggerRedraw = () => {
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => select.dispatchEvent(new Event('change')), 120);
  };

  if (search) {
    search.addEventListener('input', (e) => {
      const q = e.target.value.trim();
      if (!q) {
        populateSelect(allSectors, select.value);
        return;
      }
      // Exact match only - filter by code or name containing the search string
      const filtered = allSectors.filter(s => 
        s.code.toLowerCase().includes(q.toLowerCase()) || 
        s.name.toLowerCase().includes(q.toLowerCase())
      );
      populateSelect(filtered.slice(0, 50), select.value);
      
      // If exact code match exists, auto-select and redraw
      const exactMatch = filtered.find(s => s.code.toLowerCase() === q.toLowerCase());
      if (exactMatch && select.value !== exactMatch.code) {
        select.value = exactMatch.code;
        triggerRedraw();
      }
    });

    search.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        select.dispatchEvent(new Event('change'));
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        select.focus();
        select.selectedIndex = 0;
      }
    });
  }

  function redraw() {
    const chosen = select.value;
    setLoading(true);
    
    const sectorName = toName(chosen);
    
    // Update figure title
    const title = `${sectorName} Scope 1 emissions disaggregated by Activity Category, Activity Type, and Gas Category (% of total Scope 1 MTCO2e emissions)`;
    const titleEl = document.getElementById("figureTitle");
    if (titleEl) titleEl.textContent = title;

    // Render ring breakdown tables
    renderRingBreakdown(allData, chosen);

    const tree = buildHierarchy(allData, chosen);
    const minPct = Math.max(0, (+document.getElementById("minPct").value || 0) / 100);
    renderSunburst(tree, sectorName, minPct);
    setLoading(false);
  }

  document.getElementById("redrawBtn").addEventListener("click", redraw);
  select.addEventListener("change", redraw);
  document.getElementById("minPct").addEventListener("change", redraw);

  // Initial render with default sector: Iron and steel mills and ferroalloy manufacturing
  const defaultSector = allSectors.find(s => 
    s.name.toLowerCase().includes("iron and steel") || s.code === "331110"
  );
  if (defaultSector) {
    select.value = defaultSector.code;
  } else {
    select.selectedIndex = 0;
  }
  redraw();

  // Redraw on resize
  let resizeTimer = null;
  window.addEventListener('resize', () => {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => redraw(), 150);
  });
}

init().catch((err) => {
  console.error(err);
  d3.select("#chart").append("p").text("Failed to load or render the chart.");
});

function renderRingBreakdown(data, sectorCode) {
  const container = d3.select('#ringBreakdown');
  if (container.empty()) return;
  container.selectAll('*').remove();

  // Find the selected sector in the hierarchy
  if (!data || !data.children) return;
  const sectorNode = data.children.find(d => 
    d.useeio_code === sectorCode || d.name === sectorCode
  );
  
  if (!sectorNode || !sectorNode.children) return;

  // Color mapping
  const categoryColors = {
    "Electric Power Generation": "#0099CC",
    "Fuel Combustion": "#FF6B6B",
    "Process & Fugitive Gases": "#9C27B0"
  };

  // Helper function to sum values in a tree
  const sumTree = (node) => {
    const nodeValue = node.contributionToUSEEIOSectorScope1Percent || node.value;
    if (nodeValue) return nodeValue;
    if (!node.children || node.children.length === 0) return 0;
    return d3.sum(node.children, sumTree);
  };

  // Ring 1: Activity Category (immediate children of sector)
  const ring1Array = sectorNode.children
    .filter(d => d.category === 'activity_category')
    .map(d => ({
      name: d.name,
      value: sumTree(d),
      depth: 1
    }))
    .sort((a, b) => {
      const order = ["Electric Power Generation", "Fossil Fuels Combustion", "Process & Fugitive Gases"];
      const aIdx = order.indexOf(a.name);
      const bIdx = order.indexOf(b.name);
      if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx;
      return b.value - a.value;
    });

  // Ring 2: Activity Type (collect all unique activity types across activity categories)
  const subsubcatMap = new Map();
  sectorNode.children.forEach(ghgCat => {
    if (ghgCat.children) {
      ghgCat.children.forEach(subsubcat => {
        const subsubcatName = subsubcat.name || 'Unknown';
        const val = sumTree(subsubcat);
        subsubcatMap.set(subsubcatName, (subsubcatMap.get(subsubcatName) || 0) + val);
      });
    }
  });
  const ring2Array = Array.from(subsubcatMap, ([name, value]) => ({name, value, depth: 2}))
    .sort((a, b) => b.value - a.value);

  // Ring 3: Gas Category (collect all unique gas categories)
  const gasCategoryMap = new Map();
  const traverseForGasCategories = (node) => {
    if (node.category === 'gas_category') {
      const val = node.contributionToUSEEIOSectorScope1Percent || node.value || 0;
      gasCategoryMap.set(node.name, (gasCategoryMap.get(node.name) || 0) + val);
    }
    if (node.children) {
      node.children.forEach(traverseForGasCategories);
    }
  };
  sectorNode.children.forEach(traverseForGasCategories);
  
  const ring3Array = Array.from(gasCategoryMap, ([name, value]) => ({name, value, depth: 3}))
    .sort((a, b) => b.value - a.value);

  // Create table for each ring
  const rings = [
    {title: "Inner Ring: Activity Category", data: ring1Array, showColor: true, depth: 1},
    {title: "Middle Ring: Activity Type", data: ring2Array, showColor: false, depth: 2},
    {title: "Outer Ring: Gas Category", data: ring3Array, showColor: false, depth: 3}
  ];

  rings.forEach(ring => {
    const div = container.append('div').attr('class', 'ring-table');
    div.append('h3').text(ring.title);
    
    const table = div.append('table');
    const thead = table.append('thead').append('tr');
    thead.append('th').text('Name');
    thead.append('th').attr('class', 'value').text('Contribution');

    const tbody = table.append('tbody');
    ring.data.forEach(item => {
      const tr = tbody.append('tr')
        .datum(item)
        .attr('data-name', item.name)
        .attr('data-depth', ring.depth)
        .on('mouseenter', function(event, d) {
          if (persistentSelection) return; // Don't override persistent selection
          const path = getPathForItem(d.name, ring.depth);
          updateBreadcrumb(path);
          centerLabel.text(formatPct(d.value));
          highlightPath(d.name, ring.depth);
          highlightTableRowsForName(d.name, ring.depth);
        })
        .on('mouseleave', function(event, d) {
          if (persistentSelection) return; // Don't clear persistent selection
          breadcrumb.html("");
          centerLabel.text("");
          clearHighlight();
          clearTableHighlights();
        })
        .on('click', function(event, d) {
          event.stopPropagation();
          // Toggle persistent selection
          const currentlyHighlighted = d3.select(this).classed('highlighted');
          if (persistentSelection && persistentSelection.name === d.name && persistentSelection.depth === ring.depth) {
            // Clicking the same row - deselect
            persistentSelection = null;
            breadcrumb.html("");
            centerLabel.text("");
            clearHighlight();
            clearTableHighlights();
          } else {
            // New selection
            const path = getPathForItem(d.name, ring.depth);
            persistentSelection = { name: d.name, depth: ring.depth, type: 'table' };
            updateBreadcrumb(path);
            centerLabel.text(formatPct(d.value));
            highlightPath(d.name, ring.depth);
            highlightTableRowsForName(d.name, ring.depth);
          }
        });
      
      const tdName = tr.append('td');
      
      if (ring.showColor && categoryColors[item.name]) {
        tdName.append('span')
          .attr('class', 'color-swatch')
          .style('background-color', categoryColors[item.name]);
      }
      
      tdName.append('span').text(item.name);
      tr.append('td')
        .attr('class', 'value')
        .text(formatPct(item.value));
    });
  });
}

function updateBreadcrumb(pathArray) {
  if (!pathArray || pathArray.length === 0) {
    breadcrumb.html("");
    return;
  }
  
  // If pathArray is an array of arrays (multiple paths), display them grouped by category
  if (Array.isArray(pathArray[0])) {
    const paths = pathArray;
    
    // Group paths by their first element (Activity Category)
    const groupedByCategory = new Map();
    paths.forEach(path => {
      if (path.length > 0) {
        const category = path[0];
        if (!groupedByCategory.has(category)) {
          groupedByCategory.set(category, []);
        }
        groupedByCategory.get(category).push(path);
      }
    });
    
    // Build display grouped by category
    let html = '';
    let firstCategory = true;
    
    groupedByCategory.forEach((categoryPaths, category) => {
      // Add spacing between categories
      if (!firstCategory) {
        html += '<br/>';
      }
      firstCategory = false;
      
      // Category header
      html += `<span class="path">${category}</span><br/>`;
      
      // Show each path under this category
      categoryPaths.forEach(path => {
        // Skip the category itself (first element) since it's in the header
        const subPath = path.slice(1);
        if (subPath.length > 0) {
          html += '<span class="path-indent">├─ ' + subPath.join(' ▸ ') + '</span><br/>';
        }
      });
    });
    
    breadcrumb.html(html);
    return;
  }
  
  // Single path - display normally
  const parts = pathArray.map((name, i) => {
    if (i === 0) return `<span class="path">${name}</span>`;
    return `<span class="separator">▸</span><span class="path">${name}</span>`;
  });
  
  breadcrumb.html(parts.join(''));
}

function getPathForItem(name, depth) {
  // For table items, we need to find ALL matching paths
  if (!window.currentSunburstRoot) return [name];
  
  const matchingNodes = window.currentSunburstRoot.descendants().filter(d => 
    d.depth === depth && d.data.name === name
  );
  
  if (matchingNodes.length === 0) return [name];
  
  // If only one path, return it as a simple array
  if (matchingNodes.length === 1) {
    return matchingNodes[0].ancestors().map(n => n.data.name).reverse().slice(1);
  }
  
  // Multiple paths - return array of path arrays
  return matchingNodes.map(node => 
    node.ancestors().map(n => n.data.name).reverse().slice(1)
  );
}

function highlightPathFromNode(node) {
  if (!node) return;
  
  // Get all nodes to highlight (the node + its descendants + its ancestors)
  const highlightSet = new Set();
  highlightSet.add(node);
  node.descendants().forEach(d => highlightSet.add(d));
  node.ancestors().forEach(d => highlightSet.add(d));
  
  // Dim non-matching arcs
  d3.selectAll('.arc-segment')
    .transition()
    .duration(200)
    .attr('fill-opacity', d => highlightSet.has(d) ? 0.9 : 0.3);
}

function highlightTableRowsForNode(node) {
  // Highlight the corresponding table row(s) for a given node
  if (!node) return;
  
  clearTableHighlights();
  
  // Get the full path
  const ancestors = node.ancestors().reverse().slice(1); // [category, subsubcategory, gas]
  
  // Highlight rows at each depth that match
  ancestors.forEach(ancestor => {
    const name = ancestor.data.name;
    const depth = ancestor.depth;
    
    d3.selectAll('.ring-table tbody tr')
      .filter(function() {
        return d3.select(this).attr('data-name') === name && 
               +d3.select(this).attr('data-depth') === depth;
      })
      .classed('highlighted', true);
  });
}

function highlightTableRowsForName(name, depth) {
  // Highlight table rows for a name at a specific depth, including all ancestor paths
  if (!window.currentSunburstRoot) return;
  
  clearTableHighlights();
  
  // Find all nodes that match the name at the given depth
  const matchingNodes = window.currentSunburstRoot.descendants().filter(d => 
    d.depth === depth && d.data.name === name
  );
  
  if (matchingNodes.length === 0) return;
  
  // For each matching node, highlight its full path in the tables
  const rowsToHighlight = new Set();
  matchingNodes.forEach(node => {
    const ancestors = node.ancestors().reverse().slice(1);
    ancestors.forEach(ancestor => {
      const key = `${ancestor.data.name}|${ancestor.depth}`;
      rowsToHighlight.add(key);
    });
  });
  
  // Highlight all collected rows
  rowsToHighlight.forEach(key => {
    const [rowName, rowDepth] = key.split('|');
    d3.selectAll('.ring-table tbody tr')
      .filter(function() {
        return d3.select(this).attr('data-name') === rowName && 
               +d3.select(this).attr('data-depth') === +rowDepth;
      })
      .classed('highlighted', true);
  });
}

function clearTableHighlights() {
  d3.selectAll('.ring-table tbody tr').classed('highlighted', false);
}

function highlightPath(name, depth) {
  if (!window.currentSunburstRoot) return;
  
  // Find all nodes that match the name at the given depth
  const matchingNodes = window.currentSunburstRoot.descendants().filter(d => 
    d.depth === depth && d.data.name === name
  );
  
  if (matchingNodes.length === 0) return;
  
  // Get all nodes to highlight (matching nodes + their descendants + their ancestors)
  const highlightSet = new Set();
  matchingNodes.forEach(node => {
    // Add the node itself
    highlightSet.add(node);
    // Add all descendants (children, grandchildren, etc.)
    node.descendants().forEach(d => highlightSet.add(d));
    // Add all ancestors (parent, grandparent, etc.)
    node.ancestors().forEach(d => highlightSet.add(d));
  });
  
  // Dim non-matching arcs
  d3.selectAll('.arc-segment')
    .transition()
    .duration(200)
    .attr('fill-opacity', d => highlightSet.has(d) ? 0.9 : 0.3);
}

function clearHighlight() {
  // Restore all arcs to normal opacity
  d3.selectAll('.arc-segment')
    .transition()
    .duration(200)
    .attr('fill-opacity', 0.9);
}

function setLoading(isLoading){
  const chart = d3.select('#chart');
  let el = chart.select('.loading');
  if (isLoading){
    if (el.empty()){
      el = chart.append('div').attr('class', 'loading').text('Loading...');
    }
  } else {
    el.remove();
  }
}
