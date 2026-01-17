import tempfile
import zipfile
from pathlib import Path

import pandas as pd

from ..meta import __version__


def make_settings(usd):
    return pd.DataFrame(
        {
            "pHroc_version": [__version__],
            "pH_equation": [usd.pH_equation],
            "dye_slope": [usd.dye_slope],
            "dye_intercept": [usd.dye_intercept],
        }
    )


def write_phroc(filename, usd):
    with tempfile.TemporaryDirectory() as tdir:
        usd.measurements.to_parquet(Path(f"{tdir}/measurements.parquet"))
        usd.samples.to_parquet(Path(f"{tdir}/samples.parquet"))
        make_settings(usd).to_parquet(Path(f"{tdir}/settings.parquet"))
        if not filename.endswith(".phroc"):
            filename += ".phroc"
        with zipfile.ZipFile(filename, compression=zipfile.ZIP_LZMA, mode="w") as z:
            z.write(
                Path(f"{tdir}/measurements.parquet"),
                arcname="measurements.parquet",
            )
            z.write(
                Path(f"{tdir}/samples.parquet"),
                arcname="samples.parquet",
            )
            z.write(
                Path(f"{tdir}/settings.parquet"),
                arcname="settings.parquet",
            )


def write_excel(filename, usd):
    if not filename.endswith(".xlsx"):
        filename += ".xlsx"
    settings = make_settings(usd)
    with pd.ExcelWriter(filename, engine="openpyxl") as w:
        usd.samples.to_excel(w, sheet_name="Samples")
        usd.measurements.to_excel(w, sheet_name="Measurements")
        settings.to_excel(w, index=False, sheet_name="Settings")
