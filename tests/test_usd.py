# %%
# import numpy as np
import pandas as pd

from phroc.process.parameters import pH_DSC07, pH_tris_DD98
from phroc.process.read import read_agilent_pH


def _get_samples_from_measurements(sample):
    return pd.Series(
        {
            "sample_name": sample.sample_name.iloc[0],
            "salinity": sample.salinity.mean(),
            "temperature": sample.temperature.mean(),
            "pH": sample.pH.mean(),
            "pH_std": sample.pH[sample.pH_good].std(),
            "pH_count": sample.pH.size,
            "pH_good": sample.pH_good.sum(),
            "type": sample.type.iloc[0],
            "extra_mcp": sample.extra_mcp.all(),
        }
    )


def get_samples_from_measurements(measurements):
    # Get one-per-sample table and repopulate xpos column in measurements
    samples = measurements.groupby("order_analysis").apply(
        _get_samples_from_measurements, include_groups=False
    )
    tris = samples.type == "tris"
    samples["pH_tris_expected"] = pH_tris_DD98(
        temperature=samples[tris].temperature,
        salinity=samples[tris].salinity,
    )
    return samples


class UpdatingSummaryDataset:
    def __init__(self, measurements):
        self.measurements = measurements.copy()
        self.update_samples()

    def update_samples(self):
        self.samples = get_samples_from_measurements(self.measurements)


measurements = read_agilent_pH("tests/data/2024-04-27-CTD1.TXT")
usd = UpdatingSummaryDataset(measurements)
