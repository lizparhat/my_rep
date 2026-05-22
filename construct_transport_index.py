"""Template pipeline for constructing a hybrid transport infrastructure index.

Research target:
- Long panel infrastructure quality index (2000–2022 baseline)
- Infrastructure -> NTL relationship
- Infrastructure conversion efficiency
- RF + SHAP interpretability module

This script runs with synthetic data if no real files are found.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
import statsmodels.formula.api as smf


DATA_DIR = Path("data")
OUT_DIR = Path("outputs")
OUT_DIR.mkdir(exist_ok=True)


@dataclass
class Config:
    start_year: int = 2000
    end_year: int = 2022
    random_state: int = 42


CFG = Config()


def make_template_data() -> pd.DataFrame:
    """Create synthetic country-year panel for template execution."""
    rng = np.random.default_rng(CFG.random_state)
    iso3_list = [f"C{i:03d}" for i in range(1, 31)]
    years = np.arange(CFG.start_year, CFG.end_year + 1)
    idx = pd.MultiIndex.from_product([iso3_list, years], names=["iso3", "year"])
    df = idx.to_frame(index=False)

    base = rng.normal(0, 1, len(df))
    df["wef_infra"] = 3 + 0.5 * base + 0.01 * (df["year"] - CFG.start_year)
    df["log_gdppc"] = 8 + 0.2 * base + 0.015 * (df["year"] - CFG.start_year)
    df["urban"] = np.clip(40 + 5 * base + 0.3 * (df["year"] - CFG.start_year), 15, 95)
    df["trade_open"] = np.clip(60 + 10 * base, 10, 200)

    # Simulated LPI available from 2007 with missing survey years
    lpi = 2 + 0.6 * df["wef_infra"] + rng.normal(0, 0.15, len(df))
    df["lpi_infra"] = np.where(df["year"] >= 2007, lpi, np.nan)
    sparse_years = {2008, 2009, 2011, 2013, 2015, 2017, 2019, 2021}
    df.loc[df["year"].isin(sparse_years), "lpi_infra"] = np.nan

    # Simulated NTL outcome
    df["ntl"] = 0.5 * df["wef_infra"] + 0.3 * df["log_gdppc"] + rng.normal(0, 0.5, len(df))
    return df


def load_or_template() -> pd.DataFrame:
    """Load real files if found, otherwise return synthetic template data."""
    req_files = ["wef_infra.csv", "lpi_infra.csv", "controls.csv", "outcomes.csv"]
    if all((DATA_DIR / f).exists() for f in req_files):
        wef = pd.read_csv(DATA_DIR / "wef_infra.csv")
        lpi = pd.read_csv(DATA_DIR / "lpi_infra.csv")
        ctl = pd.read_csv(DATA_DIR / "controls.csv")
        out = pd.read_csv(DATA_DIR / "outcomes.csv")
        df = wef.merge(lpi, on=["iso3", "year"], how="outer")
        df = df.merge(ctl, on=["iso3", "year"], how="left")
        df = df.merge(out, on=["iso3", "year"], how="left")
        return df
    print("[INFO] Real data files not found. Running in synthetic template mode.")
    return make_template_data()


def calibrate_wef_to_lpi(df: pd.DataFrame) -> Tuple[pd.DataFrame, object]:
    """Estimate mapping from WEF to LPI scale on overlapping years."""
    overlap = df.dropna(subset=["wef_infra", "lpi_infra", "log_gdppc", "urban", "trade_open"]).copy()
    if overlap.empty:
        raise ValueError("No overlap sample for calibration.")

    model = smf.ols(
        "lpi_infra ~ wef_infra + log_gdppc + urban + trade_open + C(year)",
        data=overlap,
    ).fit()

    df = df.copy()
    df["wef_calibrated_to_lpi"] = model.predict(df)
    return df, model


def build_hybrid_series(df: pd.DataFrame) -> pd.DataFrame:
    """Build base hybrid index before filling annual gaps."""
    df = df.copy()
    cond_pre2007 = df["year"].between(2000, 2006)
    cond_2007on = df["year"] >= 2007

    df["hybrid_raw"] = np.nan
    df.loc[cond_pre2007, "hybrid_raw"] = df.loc[cond_pre2007, "wef_calibrated_to_lpi"]
    df.loc[cond_2007on, "hybrid_raw"] = df.loc[cond_2007on, "lpi_infra"]
    return df


def impute_versions(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Create A/B/C versions: linear, MICE-like, RandomForest."""
    base = df.copy().sort_values(["iso3", "year"])

    # Version A: linear interpolation within country
    va = base.copy()
    va["infra_index"] = va.groupby("iso3")["hybrid_raw"].transform(lambda s: s.interpolate(limit_direction="both"))

    # Version B: IterativeImputer (MICE-like)
    vb = base.copy()
    imp_cols = ["hybrid_raw", "wef_infra", "log_gdppc", "urban", "trade_open", "year"]
    imp = IterativeImputer(random_state=CFG.random_state, max_iter=20)
    vb_imp = imp.fit_transform(vb[imp_cols])
    vb["infra_index"] = vb_imp[:, 0]

    # Version C: RF imputation for missing hybrid_raw
    vc = base.copy()
    train = vc.dropna(subset=["hybrid_raw", "wef_infra", "log_gdppc", "urban", "trade_open"])
    pred = vc[vc["hybrid_raw"].isna()].dropna(subset=["wef_infra", "log_gdppc", "urban", "trade_open"])

    rf = RandomForestRegressor(n_estimators=300, random_state=CFG.random_state)
    feats = ["wef_infra", "log_gdppc", "urban", "trade_open", "year"]

    vc["infra_index"] = vc["hybrid_raw"]
    if not train.empty and not pred.empty:
        rf.fit(train[feats], train["hybrid_raw"])
        vc.loc[pred.index, "infra_index"] = rf.predict(pred[feats])
        vc["infra_index"] = vc.groupby("iso3")["infra_index"].transform(lambda s: s.interpolate(limit_direction="both"))

    return {"linear": va, "mice": vb, "rf": vc}


def masking_validation(df: pd.DataFrame, version_name: str) -> pd.DataFrame:
    """Simple masking test on observed LPI values."""
    obs = df.dropna(subset=["lpi_infra", "infra_index"])
    if len(obs) < 30:
        return pd.DataFrame({"version": [version_name], "mae": [np.nan], "rmse": [np.nan], "n": [len(obs)]})

    y_true = obs["lpi_infra"].values
    y_pred = obs["infra_index"].values
    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred, squared=False)
    return pd.DataFrame({"version": [version_name], "mae": [mae], "rmse": [rmse], "n": [len(obs)]})


def run_part1_regression(df: pd.DataFrame) -> str:
    """Part 1: Infrastructure -> NTL baseline regression."""
    reg_df = df.dropna(subset=["ntl", "infra_index", "log_gdppc", "urban", "trade_open"]).copy()
    res = smf.ols("ntl ~ infra_index + log_gdppc + urban + trade_open + C(year)", data=reg_df).fit()
    return res.summary().as_text()


def run_part2_efficiency(df: pd.DataFrame) -> pd.DataFrame:
    """Part 2: Efficiency = Actual NTL - Predicted NTL."""
    reg_df = df.dropna(subset=["ntl", "infra_index", "log_gdppc", "urban", "trade_open"]).copy()
    model = smf.ols("ntl ~ infra_index + log_gdppc + urban + trade_open + C(year)", data=reg_df).fit()
    reg_df["ntl_predicted"] = model.predict(reg_df)
    reg_df["efficiency_index"] = reg_df["ntl"] - reg_df["ntl_predicted"]
    return reg_df[["iso3", "year", "ntl", "ntl_predicted", "efficiency_index"]]


def run_part3_rf_importance(df: pd.DataFrame) -> pd.DataFrame:
    """Part 3: RF feature importance for NTL prediction."""
    ml_df = df.dropna(subset=["ntl", "infra_index", "log_gdppc", "urban", "trade_open"]).copy()
    feats = ["infra_index", "log_gdppc", "urban", "trade_open", "year"]
    X = ml_df[feats]
    y = ml_df["ntl"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=CFG.random_state)
    rf = RandomForestRegressor(n_estimators=300, random_state=CFG.random_state)
    rf.fit(X_train, y_train)

    pred = rf.predict(X_test)
    rmse = mean_squared_error(y_test, pred, squared=False)

    imp = pd.DataFrame({"feature": feats, "importance": rf.feature_importances_}).sort_values("importance", ascending=False)
    imp["test_rmse"] = rmse
    return imp


def main() -> None:
    df = load_or_template()
    df, cal_model = calibrate_wef_to_lpi(df)
    base = build_hybrid_series(df)
    versions = impute_versions(base)

    val_frames = []
    for name, vdf in versions.items():
        val_frames.append(masking_validation(vdf, name))
        vdf.to_csv(OUT_DIR / f"panel_{name}.csv", index=False)

    val = pd.concat(val_frames, ignore_index=True)
    val.to_csv(OUT_DIR / "validation_summary.csv", index=False)

    # Use linear as transparent baseline for example outputs
    baseline = versions["linear"]
    part1_txt = run_part1_regression(baseline)
    (OUT_DIR / "part1_regression.txt").write_text(part1_txt)

    eff = run_part2_efficiency(baseline)
    eff.to_csv(OUT_DIR / "part2_efficiency.csv", index=False)

    imp = run_part3_rf_importance(baseline)
    imp.to_csv(OUT_DIR / "part3_rf_importance.csv", index=False)

    (OUT_DIR / "calibration_summary.txt").write_text(cal_model.summary().as_text())
    print("[DONE] Pipeline executed. See outputs/ directory.")


if __name__ == "__main__":
    main()
