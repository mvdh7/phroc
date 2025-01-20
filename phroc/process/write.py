import os
import tempfile
import zipfile

import pandas as pd

from ..meta import __version__


def make_settings(usd):
    return pd.DataFrame(
        {
            "phroc_version": __version__,
            "dye_slope": [usd.dye_slope],
            "dye_intercept": [usd.dye_intercept],
        }
    )


def write_phroc(filename, usd):
    # filename needs to include the **absolute** path to the .phroc file to be saved!
    # Using a relative path will mean it gets saved in the TemporaryDirectory instead
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tdir:
        os.chdir(tdir)
        usd.measurements.to_parquet("measurements.parquet")
        usd.samples.to_parquet("samples.parquet")
        make_settings(usd).to_parquet("settings.parquet")
        if not filename.endswith(".phroc"):
            filename += ".phroc"
        with zipfile.ZipFile(filename, compression=zipfile.ZIP_LZMA, mode="w") as z:
            z.write("measurements.parquet")
            z.write("samples.parquet")
            z.write("settings.parquet")
    os.chdir(cwd)


def write_excel(filename, usd):
    if not filename.endswith(".xlsx"):
        filename += ".xlsx"
    settings = make_settings(usd)
    with pd.ExcelWriter(filename, engine="openpyxl") as w:
        usd.samples.to_excel(w, sheet_name="Samples")
        usd.measurements.to_excel(w, sheet_name="Measurements")
        settings.to_excel(w, index=False, sheet_name="Settings")
