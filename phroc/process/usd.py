import numpy as np
import pandas as pd

from .parameters import pH_DSC07, pH_tris_DD98
from .read_raw import enforce_comments, enforce_ts, get_order_analysis, read_agilent_pH
from .write import write_excel, write_phroc


def _get_samples_from_measurements(sample):
    return pd.Series(
        {
            "sample_name": sample.sample_name.iloc[0],
            "salinity": sample.salinity.mean(),
            "temperature": sample.temperature.mean(),
            "pH": sample.pH[sample.pH_good].mean(),
            "pH_std": sample.pH[sample.pH_good].std(),
            "pH_count": sample.pH.size,
            "pH_good": sample.pH_good.sum(),
            "is_tris": sample.is_tris.all(),
            "extra_mcp": sample.extra_mcp.all(),
            "comments": sample.comments.iloc[0],
        }
    )


def get_samples_from_measurements(measurements):
    # Get one-per-sample table in measurements
    samples = measurements.groupby("order_analysis").apply(
        _get_samples_from_measurements, include_groups=False
    )
    samples["pH_tris_expected"] = pH_tris_DD98(
        temperature=samples[samples.is_tris].temperature,
        salinity=samples[samples.is_tris].salinity,
    )
    return samples


def get_xpos(measurements, samples):
    measurements["xpos"] = measurements.order_analysis.astype(float)
    for s, sample in samples.iterrows():
        M = measurements.order_analysis == s
        measurements.loc[M, "xpos"] += (
            0.5 + np.arange(sample.pH_count) - sample.pH_count / 2
        ) * 0.05


class UpdatingSummaryDataset:
    def __init__(self, measurements, dye_intercept=0, dye_slope=0):
        if isinstance(measurements, str):
            self.measurements = read_agilent_pH(
                measurements,
                dye_intercept=dye_intercept,
                dye_slope=dye_slope,
            )
        else:
            self.measurements = measurements.copy()
        self.get_samples()
        self.dye_intercept = dye_intercept
        self.dye_slope = dye_slope

    def get_samples(self):
        (
            self.measurements.pipe(get_order_analysis)
            .pipe(enforce_ts)
            .pipe(enforce_comments)
        )
        self.samples = get_samples_from_measurements(self.measurements)
        get_xpos(self.measurements, self.samples)

    def set_measurement(self, order, **kwargs):
        assert order in self.measurements.index
        # Use this to update individual measurements
        for col, value in kwargs.items():
            assert col in ["sample_name", "pH_good"], (
                f"`{col}` cannot be set on a per-measurement basis."
            )
            # Update measurements df
            self.measurements.loc[order, col] = value
            # Update samples df
            sm = self.measurements
            s = sm.loc[order].order_analysis
            M = sm.order_analysis == s
            if col == "pH_good":
                self.samples.loc[s, "pH_good"] = sm.loc[M, "pH_good"].sum()
                # If a measurements is flagged as (not) good then we also need to update
                # the mean and standard deviation of pH in samples
                Mg = M & sm.pH_good
                self.samples.loc[s, "pH"] = sm.loc[Mg, "pH"].mean()
                self.samples.loc[s, "pH_std"] = sm.loc[Mg, "pH"].std()
            elif col == "sample_name":
                # This one would be too fiddly to make all the changes manually, so it's
                # safer to stick with recreating the samples table from scratch
                self.get_samples()

    def set_measurements(self, order_logic, **kwargs):
        # Use this to update a series of measurements
        for col, value in kwargs.items():
            assert col in ["sample_name", "pH_good"], (
                f"`{col}` cannot be set on a per-measurement basis."
            )
            # Update measurements df
            self.measurements.loc[order_logic, col] = value
            # Update samples df
            sm = self.measurements
            ss = sm.loc[order_logic].order_analysis.unique()
            for s in ss:
                M = sm.order_analysis == s
                if col == "pH_good":
                    self.samples.loc[s, "pH_good"] = sm.loc[M, "pH_good"].sum()
                    # If a measurements is flagged as (not) good then we also need to
                    # update the mean and standard deviation of pH in samples
                    Mg = M & sm.pH_good
                    self.samples.loc[s, "pH"] = sm.loc[Mg, "pH"].mean()
                    self.samples.loc[s, "pH_std"] = sm.loc[Mg, "pH"].std()
                elif col == "sample_name":
                    # This one would be too fiddly to make all the changes manually, so
                    # it's safer to stick with recreating the samples table from scratch
                    self.get_samples()

    def set_sample(self, order_analysis, **kwargs):
        assert order_analysis in self.samples.index
        # Use this to update entire samples
        # (i.e., measurements with the same order_analysis)
        cols = list(kwargs.keys())
        if "is_tris" in cols:
            # If is_tris is to be changed, this needs to happen first, so that
            # pH_tris_expected is correctly updated if temperature or salinity change
            cols.remove("is_tris")
            cols = ["is_tris", *cols]
        if "sample_name" in cols:
            # If sample_name is to be changed, this needs to happen last, else it might
            # mess up the other changes because the df indices could change
            cols.remove("sample_name")
            cols.append("sample_name")
        if "comments" in cols:
            # If comments are to be changed, this needs to happen after sample_name, so
            # the comments are carried over to the next sample if merged
            cols.remove("comments")
            cols.append("comments")
        for col in cols:
            assert col in [
                "salinity",
                "temperature",
                "is_tris",
                "extra_mcp",
                "sample_name",
                "comments",
            ], f"`{col}` cannot be set on a per-sample basis."
            value = kwargs[col]
            self.samples.loc[order_analysis, col] = value
            sm = self.measurements
            M = sm.order_analysis == order_analysis
            sm.loc[M, col] = value
            if col in ["salinity", "temperature"]:
                Mg = M & sm.pH_good
                # After updating salinity and/or temperature, we need to recalculate pH
                sm.loc[M, "pH"] = pH_DSC07(
                    sm[M].absorbance_578.values,
                    sm[M].absorbance_434.values,
                    sm[M].absorbance_730.values,
                    temperature=sm[M].temperature.values,
                    salinity=sm[M].salinity.values,
                    dye_intercept=self.dye_intercept,
                    dye_slope=self.dye_slope,
                )
                self.samples.loc[order_analysis, "pH"] = sm.loc[Mg, "pH"].mean()
                self.samples.loc[order_analysis, "pH_std"] = sm.loc[Mg, "pH"].std()
                if self.samples.loc[order_analysis, "is_tris"]:
                    self.samples.loc[order_analysis, "pH_tris_expected"] = pH_tris_DD98(
                        temperature=self.samples.loc[order_analysis].temperature,
                        salinity=self.samples.loc[order_analysis].salinity,
                    )
            elif col == "is_tris":
                if value:
                    self.samples.loc[order_analysis, "pH_tris_expected"] = pH_tris_DD98(
                        temperature=self.samples.loc[order_analysis].temperature,
                        salinity=self.samples.loc[order_analysis].salinity,
                    )
                else:
                    self.samples.loc[order_analysis, "pH_tris_expected"] = np.nan
            elif col == "sample_name":
                # Recreate samples table if a sample_name is changed, to be safe.
                # This means that if a sample is given the same name as an adjacent
                # sample, they will be merged.
                self.get_samples()

    def to_excel(self, filename):
        write_excel(filename, self)

    def to_phroc(self, filename):
        write_phroc(filename, self)
