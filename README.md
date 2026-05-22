# Global Infrastructure–Development Research Pipeline (Template)

This repository contains a starter Python workflow for constructing a long-run country-year infrastructure index and linking it to economic development outcomes (e.g., NTL).

## Scope

- Build a **hybrid transport infrastructure index** for 2000–2022 (WEF + LPI calibration)
- Keep code extensible to earlier periods (e.g., 1992+) if alternative transport proxies are added
- Run baseline relationship tests: `Infrastructure -> NTL`
- Estimate conversion efficiency: `Efficiency = Actual NTL - Predicted NTL`
- Add ML interpretation: feature importance and SHAP

## Files

- `construct_transport_index.py`: end-to-end template pipeline (data placeholders + methods)
- `requirements.txt`: Python dependencies
- `create_data_templates.py`: generate the required `data/*.csv` template files
- `data/README.md`: where to put data and how to bootstrap templates

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python create_data_templates.py  # optional: create template CSV files
python construct_transport_index.py
```

The script will run in **template mode** using synthetic data if no input files are provided.

## Expected Input Data (replace placeholders)

Prepare country-year panel files with consistent country IDs (recommended: ISO3):

1. `data/wef_infra.csv`
   - `iso3`, `year`, `wef_infra`
2. `data/lpi_infra.csv`
   - `iso3`, `year`, `lpi_infra`
3. `data/controls.csv`
   - `iso3`, `year`, `log_gdppc`, `urban`, `trade_open`
4. `data/outcomes.csv`
   - `iso3`, `year`, `ntl`

Optional additional infrastructure proxies for pre-2000 extension:
- road density / paved road share
- rail density
- port container throughput
- air freight

## Method Summary

1. **Calibrate WEF to LPI scale** on overlapping years.
2. **Build hybrid index**:
   - 2000–2006: calibrated WEF
   - 2007–2022: observed LPI where available
3. **Impute missing years** with:
   - Linear interpolation (transparent baseline)
   - Iterative imputation (MICE-like)
   - Random Forest imputation (robustness)
4. **Validation**:
   - Masking test (MAE/RMSE on hidden true LPI)
   - Correlation with objective transport proxies
   - Coefficient stability across imputation versions
5. **Research modules**:
   - Part 1: Infrastructure -> NTL
   - Part 2: Efficiency = actual NTL - predicted NTL
   - Part 3: RF + SHAP explanation

## Notes

- This is a scaffold designed for your paper workflow.
- Replace placeholder columns with your real variables before final estimation.
