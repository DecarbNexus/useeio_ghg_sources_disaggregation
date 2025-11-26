# Licensing Summary

This document explains the licensing structure of this project and ensures compliance with all upstream dependencies.

## Overview

This project combines:
1. **Original work** (code for extraction and enrichment)
2. **EPA public domain data** (EPA GHGI emissions)
3. **MIT-licensed software** (FlowSA and USEEIOR)

All licensing requirements are fully satisfied.

## License Structure

```
┌─────────────────────────────────────────────────────────┐
│ THIS PROJECT                                            │
│                                                         │
│ ┌─────────────────┐     ┌──────────────────────────┐  │
│ │ Code            │     │ Output Data               │  │
│ │ (scripts/)      │     │ (outputs/)                │  │
│ │                 │     │                           │  │
│ │ MIT License     │     │ CC BY 4.0                 │  │
│ │ (root LICENSE)  │     │ (outputs/LICENSE.txt)     │  │
│ └─────────────────┘     └──────────────────────────┘  │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐│
│ │ DEPENDENCIES (properly attributed)                  ││
│ │                                                     ││
│ │ • FlowSA v2.0.3 (MIT) - U.S. EPA                   ││
│ │ • USEEIOR (MIT) - U.S. EPA                         ││
│ │ • EPA GHGI Data (Public Domain) - U.S. EPA         ││
│ │ • BEA I-O Data (Public Domain) - U.S. BEA          ││
│ │                                                     ││
│ │ See: outputs/THIRD_PARTY_LICENSES.txt              ││
│ └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

## File-by-File Breakdown

| File/Folder | License | Rationale |
|-------------|---------|-----------|
| `scripts/*.py` | MIT | Original code for data extraction/enrichment |
| `config.py` | MIT | Configuration code |
| `data/*.csv` | MIT | Mapping tables created for this project |
| `outputs/*` | CC BY 4.0 | Derived data requiring attribution |
| `docs/*` | CC BY 4.0 | Documentation of derived data |
| `LICENSE` | N/A | MIT license text for code |
| `outputs/LICENSE.txt` | N/A | CC BY 4.0 license text for data |
| `outputs/THIRD_PARTY_LICENSES.txt` | N/A | MIT licenses from dependencies |
| `outputs/CITATION.md` | N/A | Citation guidance |

## Compliance Checklist

### ✓ MIT License Compliance (FlowSA & USEEIOR)

**Requirements:**
- [x] Include copyright notice
- [x] Include permission notice
- [x] Provide license text

**Implementation:**
- Full MIT license texts in `outputs/THIRD_PARTY_LICENSES.txt`
- Copyright notices preserved: "Copyright (c) 2022 U.S. EPA" (FlowSA), "Copyright (c) 2021 U.S. EPA" (USEEIOR)
- Attribution in README.md, Excel files, and all documentation

### ✓ CC BY 4.0 License (Our Enriched Data)

**Requirements:**
- [x] Give appropriate credit
- [x] Provide link to license
- [x] Indicate if changes were made

**Implementation:**
- Full attribution in `outputs/LICENSE.txt`
- License URL in all materials: https://creativecommons.org/licenses/by/4.0/
- Changes clearly documented (enrichment = adding metadata to EPA GHGI data)
- Citation guidance in `outputs/CITATION.md`

### ✓ Public Domain Attribution (EPA GHGI & BEA)

**Requirements:**
- [x] Acknowledge source
- [x] Provide links to original data

**Implementation:**
- EPA GHGI attribution in all output files
- Source URLs in Model_Specs tab of Excel files
- Complete citations in CITATION.md

## Usage Scenarios

### Scenario 1: Using the enriched data

**What you need to do:**
1. Cite this project: DecarbNexus (2025)
2. Acknowledge EPA GHGI, FlowSA, and USEEIOR (citations in `CITATION.md`)
3. Include CC BY 4.0 license notice
4. Indicate any modifications you make

**What you can do:**
- Use commercially or non-commercially
- Modify and redistribute
- Create derivative works

### Scenario 2: Modifying the code

**What you need to do:**
1. Include the MIT license from root `LICENSE` file
2. Maintain copyright notice: "Copyright (c) 2025 DecarbNexus LLC"
3. Note your modifications

**What you can do:**
- Use, modify, distribute freely
- Commercial or non-commercial use
- Create derivative works

### Scenario 3: Using both code and data

**What you need to do:**
1. Follow requirements for Scenario 1 (data)
2. Follow requirements for Scenario 2 (code)
3. Keep both license files when distributing

## Why Two Licenses?

We use different licenses for code vs. data to align with best practices:

**MIT (Code):**
- Standard for open-source software
- Maximum flexibility for developers
- Compatible with FlowSA and USEEIOR

**CC BY 4.0 (Data):**
- Standard for open data
- Ensures proper attribution of data provenance
- Widely recognized in scientific community
- Aligns with EPA's open data principles

## Questions?

**Q: Can I use this data commercially?**  
A: Yes! Both MIT and CC BY 4.0 allow commercial use with proper attribution.

**Q: Do I need to cite EPA sources separately?**  
A: Yes. You must cite: (1) This project, (2) EPA GHGI, (3) FlowSA, and (4) USEEIOR. See `CITATION.md` for complete citations.

**Q: Can I redistribute modified versions?**  
A: Yes, as long as you:
- Maintain all license notices
- Provide appropriate attribution
- Indicate what you changed
- Include license texts

**Q: What if I only use a small portion of the data?**  
A: Same requirements apply. Attribution is required regardless of how much data you use.

**Q: Are there any restrictions?**  
A: No sublicensing restrictions, but you cannot:
- Remove or obscure attribution
- Suggest that EPA or this project endorses your use
- Use EPA or project names/logos to imply endorsement

## Contact

For licensing questions or concerns:
- DecarbNexus - contact@decarbnexus.com
- GitHub Issues: https://github.com/damienlieber-dnexus/flowsa-ghg-extraction/issues

## References

- MIT License: https://opensource.org/licenses/MIT
- CC BY 4.0: https://creativecommons.org/licenses/by/4.0/
- FlowSA Repository: https://github.com/USEPA/flowsa
- USEEIOR Repository: https://github.com/USEPA/useeior
- EPA GHGI: https://www.epa.gov/ghgemissions/inventory-us-greenhouse-gas-emissions-and-sinks

---

**Last Updated:** November 26, 2025  
**Version:** 1.0
