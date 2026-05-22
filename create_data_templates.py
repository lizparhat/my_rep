"""Create required input CSV templates under ./data.

This helper removes ambiguity for first-time users by creating the expected files
with header rows and a few placeholder examples.
"""

from pathlib import Path
import pandas as pd

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def write_if_missing(path: Path, df: pd.DataFrame) -> None:
    if path.exists():
        print(f"[SKIP] {path} already exists")
        return
    df.to_csv(path, index=False)
    print(f"[OK] created {path}")


def main() -> None:
    wef = pd.DataFrame(
        {
            "iso3": ["CHN", "USA"],
            "year": [2000, 2000],
            "wef_infra": [4.2, 5.8],
        }
    )

    lpi = pd.DataFrame(
        {
            "iso3": ["CHN", "USA"],
            "year": [2007, 2007],
            "lpi_infra": [3.5, 4.1],
        }
    )

    controls = pd.DataFrame(
        {
            "iso3": ["CHN", "USA"],
            "year": [2007, 2007],
            "log_gdppc": [8.5, 10.7],
            "urban": [45.0, 81.0],
            "trade_open": [65.0, 28.0],
        }
    )

    outcomes = pd.DataFrame(
        {
            "iso3": ["CHN", "USA"],
            "year": [2007, 2007],
            "ntl": [12.3, 18.7],
        }
    )

    write_if_missing(DATA_DIR / "wef_infra.csv", wef)
    write_if_missing(DATA_DIR / "lpi_infra.csv", lpi)
    write_if_missing(DATA_DIR / "controls.csv", controls)
    write_if_missing(DATA_DIR / "outcomes.csv", outcomes)

    print("[DONE] data templates ready.")


if __name__ == "__main__":
    main()
