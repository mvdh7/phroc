import os
import tempfile
import zipfile

import pandas as pd

from .usd import UpdatingSummaryDataset


def read_phroc(filename: str) -> UpdatingSummaryDataset:
    with tempfile.TemporaryDirectory() as tdir:
        with zipfile.ZipFile(filename, "r") as z:
            z.extractall(tdir)
        measurements = pd.read_parquet(os.path.join(tdir, "measurements.parquet"))
        try:
            settings = pd.read_parquet(os.path.join(tdir, "settings.parquet"))
        except FileNotFoundError:
            # If there isn't a settings file, it's v0.2
            settings = pd.DataFrame({"pH_equation": ["NIOZ"]})
            measurements["comments"] = ""
    return UpdatingSummaryDataset(
        measurements,
        **{s: settings[s].iloc[0] for s in settings.columns if s != "pHroc_version"},
    )


def read_excel(filename: str) -> UpdatingSummaryDataset:
    measurements = pd.read_excel(filename, sheet_name="Measurements").set_index("order")
    try:
        settings = pd.read_excel(filename, sheet_name="Settings")
        measurements["comments"] = measurements.comments.fillna("")
    except ValueError:
        # If there isn't a settings sheet, it's v0.2
        settings = pd.DataFrame({"pH_equation": ["NIOZ"]})
        measurements["comments"] = ""
    return UpdatingSummaryDataset(
        measurements,
        **{s: settings[s].iloc[0] for s in settings.columns if s != "pHroc_version"},
    )
