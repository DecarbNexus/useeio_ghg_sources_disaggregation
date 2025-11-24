# Documentation Index

Welcome to the FlowSA GHG Sources Extraction documentation!

## 📚 Core Documentation

### For Users
- **[User Guide](USER_GUIDE.md)** - Comprehensive guide for researchers and analysts
  - Installation and setup
  - Running the extraction
  - Understanding the output
  - Common workflows
  - Troubleshooting

### For Developers
- **[Technical Reference](TECHNICAL_REFERENCE.md)** - Developer documentation
  - Code architecture
  - Function reference
  - Enrichment algorithms
  - Performance optimization
  - Extending the pipeline

## 🔧 Setup & Troubleshooting

- **[Python Version Fix](PYTHON_VERSION_FIX.md)** - How to install Python 3.9-3.11 if you have Python 3.12+

## 📊 Advanced Features

- **[Event-Based Outputs](EVENT_BASED_OUTPUTS.md)** - Using event-based JSON-LD for semantic queries and knowledge graphs
- **[Commodity Transformation](COMMODITY_TRANSFORMATION.md)** - Industry-to-commodity emission allocation using USEEIO data
- **[Visualization Setup](VISUALIZATION_SETUP.md)** - Interactive D3.js sunburst chart setup and customization
- **[Development Guide](DEVELOPMENT.md)** - Quick reference for AI assistants and visualization developers

## 🎨 Interactive Visualization

The **[Interactive Sunburst Visualization](visualization/)** allows you to explore emissions data interactively.

To use:
1. Run the enrichment pipeline to generate data
2. Open `docs/visualization/index.html` in a web browser
3. The visualization automatically loads the latest data

See **[Visualization README](visualization/README.md)** for technical details.

## 🤝 Contributing

See **[CONTRIBUTING.md](../CONTRIBUTING.md)** (root folder) for contribution guidelines.

## 📖 Main README

For getting started, installation, and quick reference, see the **[main README.md](../README.md)** in the root folder.

---

## Quick Navigation

**By Task:**
- 🚀 **New user?** → [Main README](../README.md) → [User Guide](USER_GUIDE.md)
- 💻 **Developer?** → [Technical Reference](TECHNICAL_REFERENCE.md)
- 🐛 **Having issues?** → [User Guide - Troubleshooting](USER_GUIDE.md#troubleshooting)
- 🔍 **Want to explore data?** → [Visualization Setup](VISUALIZATION_SETUP.md)
- 🏗️ **Extending the tool?** → [Technical Reference - Extending the Pipeline](TECHNICAL_REFERENCE.md#extending-the-pipeline)

**By Output Format:**
- **Excel/CSV/Parquet** → [User Guide - Output Formats](USER_GUIDE.md#output-formats)
- **JSON-LD (semantic web)** → [Event-Based Outputs](EVENT_BASED_OUTPUTS.md)
- **Commodity form** → [Commodity Transformation](COMMODITY_TRANSFORMATION.md)

---

**Documentation Structure:**
```
docs/
├── README.md                      # This file (index)
├── USER_GUIDE.md                  # For non-technical users
├── TECHNICAL_REFERENCE.md         # For developers
├── PYTHON_VERSION_FIX.md          # Installation troubleshooting
├── EVENT_BASED_OUTPUTS.md         # Semantic web features
├── COMMODITY_TRANSFORMATION.md    # Economic modeling features
├── VISUALIZATION_SETUP.md         # D3.js setup
├── DEVELOPMENT.md                 # Quick reference for devs
└── visualization/                 # Interactive visualization
    ├── README.md                  # Visualization docs
    ├── index.html
    ├── sunburst.js
    ├── styles.css
    └── data/
```

---

**Last Updated:** November 24, 2025
