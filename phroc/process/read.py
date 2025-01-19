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
        settings = pd.read_parquet(os.path.join(tdir, "settings.parquet"))
    return UpdatingSummaryDataset(
        measurements, **{s: settings[s].iloc[0] for s in settings.columns}
    )


def read_excel(filename: str) -> UpdatingSummaryDataset:
    measurements = pd.read_excel(filename, sheet_name="Measurements").set_index("order")
    measurements["comments"] = measurements.comments.fillna("")
    settings = pd.read_excel(filename, sheet_name="Settings")
    return UpdatingSummaryDataset(
        measurements, **{s: settings[s].iloc[0] for s in settings.columns}
    )
