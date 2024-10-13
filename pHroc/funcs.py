import koolstof as ks
import pandas as pd
import numpy as np


def _get_samples(sample):
    # Used in read_measurements_create_samples()
    return pd.Series(
        {
            "sample_name": sample.sample_name.iloc[0],
            "salinity": sample.salinity.mean(),
            "temperature": sample.temperature.mean(),
            "pH": sample.pH.mean(),
            "pH_std": sample.pH[sample.pH_good].std(),
            "pH_count": sample.pH.size,
            "pH_good": sample.pH_good.sum(),
        }
    )


def read_measurements_create_samples(filename):
    # Import pH measurements file from instrument and recalculate pH
    measurements = ks.spectro.read_agilent_pH(filename)
    measurements["order_analysis"] = (
        measurements.sample_name.shift() != measurements.sample_name
    ).cumsum()
    measurements["pH"] = ks.spectro.pH_NIOZ(
        measurements.abs578,
        measurements.abs434,
        measurements.abs730,
        temperature=measurements.temperature,
        salinity=measurements.salinity,
    )
    measurements["pH_good"] = True
    # Get one-per-sample table
    samples = measurements.groupby("order_analysis").apply(
        _get_samples, include_groups=False
    )
    measurements["xpos"] = measurements.order_analysis.astype(float)
    for s, sample in samples.iterrows():
        L = measurements.sample_name == sample.sample_name
        measurements.loc[L, "xpos"] += (
            0.5 + np.arange(sample.pH_count) - sample.pH_count / 2
        ) * 0.05
    samples["is_tris"] = samples.sample_name.str.upper().str.startswith("TRIS")
    T = samples.is_tris
    samples["pH_tris_expected"] = ks.pH_tris_DD98(
        temperature=samples.temperature[T],
        salinity=samples.salinity[T],
    )
    return measurements, samples


# filename = "2024-04-27-CTD1.TXT"
# measurements, samples = read_measurements_create_samples(filename)
