import koolstof as ks
import pandas as pd
import numpy as np

data = ks.spectro.read_agilent_pH("2024-04-27-CTD1.TXT")
data["pH"] = ks.spectro.pH_NIOZ(
    data.abs578,
    data.abs434,
    data.abs730,
    temperature=data.temperature,
    salinity=data.salinity,
)
samples = data[["sample_name", "pH"]].groupby("sample_name").mean()


def _get_samples(sample):
    return pd.Series(
        {
            "salinity": sample.salinity.mean(),
            "temperature": sample.temperature.mean(),
            "pH": sample.pH.mean(),
            "pH_count": sample.pH.size,
        }
    )


samples = data.groupby("sample_name").apply(_get_samples, include_groups=False)
samples["number"] = np.arange(samples.shape[0]).astype(float)
data["number"] = samples.number[data.sample_name].values
for s, row in samples.iterrows():
    L = data.sample_name == s
    data.loc[L, "number"] += (1 + np.arange(row.pH_count)) * 0.1
