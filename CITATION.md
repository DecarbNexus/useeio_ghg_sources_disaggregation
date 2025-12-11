# Citation

## Citing This Dataset

If you use this enriched GHG emissions dataset, please cite:

```bibtex
@dataset{decarbnexus_ghg_emissions_2025,
  author       = {{DecarbNexus}},
  title        = {{U.S. Greenhouse Gas Emissions by USEEIO Sector - 
                   Enriched EPA GHGI Data}},
  year         = 2025,
  publisher    = {DecarbNexus},
  url          = {https://github.com/damienlieber-dnexus/flowsa-ghg-extraction},
  note         = {Derived from EPA GHGI 2022 using FlowSA v2.0.3 and USEEIOR},
  license      = {CC BY 4.0}
}
```

## Required Attributions

When using this dataset, you must also acknowledge the original data sources:

### EPA Greenhouse Gas Inventory

```bibtex
@techreport{epa_ghgi_2024,
  author       = {{U.S. Environmental Protection Agency}},
  title        = {{Inventory of U.S. Greenhouse Gas Emissions and Sinks: 1990-2022}},
  institution  = {U.S. Environmental Protection Agency},
  year         = 2024,
  number       = {EPA 430-R-24-004},
  address      = {Washington, DC},
  url          = {https://www.epa.gov/ghgemissions/inventory-us-greenhouse-gas-emissions-and-sinks}
}
```

### FlowSA

```bibtex
@software{flowsa_2023,
  author       = {Birney, Catherine and Young, Ben and Chambers, Matthew and Ingwersen, Wesley},
  title        = {{FlowSA: Flow-By-Sector Approach for Environmental Data}},
  year         = 2023,
  publisher    = {U.S. Environmental Protection Agency},
  version      = {2.0.3},
  url          = {https://github.com/USEPA/flowsa},
  license      = {MIT}
}
```

### USEEIOR

```bibtex
@article{li_useeior_2022,
  title        = {{useeior: An Open-Source R Package for Building and Using 
                  US Environmentally-Extended Input-Output Models}},
  author       = {Li, Mo and Ingwersen, Wesley and Young, Ben and 
                  Vendries, Jorge and Birney, Catherine},
  journal      = {Applied Sciences},
  volume       = {12},
  number       = {9},
  pages        = {4469},
  year         = {2022},
  publisher    = {MDPI},
  doi          = {10.3390/app12094469},
  url          = {https://doi.org/10.3390/app12094469},
  license      = {MIT}
}
```

## Example Citation Text

> This analysis uses greenhouse gas emissions data from DecarbNexus (2025), which enriches 
> the U.S. EPA Greenhouse Gas Inventory (EPA, 2024) transformed by FlowSA (Birney et al., 2023) and
> USEEIOR (Li et al., 2022).

## License Compliance

This dataset is provided under CC BY 4.0 license. When using it:

✓ **You must:**
- Give appropriate credit (use citations above)
- Provide a link to the license: https://creativecommons.org/licenses/by/4.0/
- Indicate if you made any changes to the dataset

✓ **You are free to:**
- Share — copy and redistribute in any medium or format
- Adapt — remix, transform, and build upon for any purpose, including commercial

✗ **You must not:**
- Remove or obscure attribution information
- Suggest that the licensor endorses your use
- Violate the MIT licenses of FlowSA and USEEIOR (see THIRD_PARTY_LICENSES.txt)

## Data Provenance

This enriched dataset combines:
1. **EPA GHGI 2022** - Emissions data (public domain, U.S. federal government)
2. **FlowSA v2.0.3** - Data processing framework (MIT License)
3. **USEEIOR** - Sector classifications and economic data (MIT License)
4. **BEA I-O Tables 2017** - Economic structure (public domain, U.S. federal government)

All required attributions and license compliance information is maintained in:
- `LICENSE.txt` - This dataset's CC BY 4.0 license
- `THIRD_PARTY_LICENSES.txt` - MIT licenses for FlowSA and USEEIOR
- This `CITATION.md` file - Citation guidance and references
