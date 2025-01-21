import numpy as np
import pandas as pd

from .parameters import pH_equations
from .qc import find_windows


def get_order_analysis(measurements):
    measurements["order_analysis"] = (
        measurements.sample_name.shift() != measurements.sample_name
    ).cumsum()
    return measurements


def enforce_ts(measurements):
    # Make all temperature and salinity values constant for each sample's measurements
    for s, sample in measurements.groupby("order_analysis"):
        M = measurements.order_analysis == s
        for col in ["temperature", "salinity"]:
            measurements.loc[M, col] = measurements.loc[M, col].median()
    return measurements


def enforce_comments(measurements):
    # Apply the majority comment across each sample
    # If there's no majority, take the earlier comment
    for s, sample in measurements.groupby("order_analysis"):
        M = measurements.order_analysis == s
        s_comments = measurements[M].comments.unique()
        if len(s_comments) > 1:
            measurements.loc[M, "comments"] = s_comments[
                np.argmax(
                    [
                        (measurements[M].comments == s_comment).sum()
                        for s_comment in s_comments
                    ]
                )
            ]
    return measurements


def read_agilent_pH(
    filename: str,
    dye_intercept: float = 0,
    dye_slope: float = 0,
    find_windows_auto: bool = False,
    pH_equation: str = "NIOZ",
) -> pd.DataFrame:
    """Import raw pH data from the spectrophotometer.

    Parameters
    ----------
    filename : str
        The raw pH data file.  There must also exist a Comments file from the
        instrument with the same name plus "-COMMENTS" directly before the
        ".TXT" extension.
    dye_intercept : float, optional
        Intercept of the dye correction (SOP 6b eq. 9), by default 0.
    dye_slope : float, optional
        Slope of the dye correction (SOP 6b eq. 9), by default 0.
    find_windows_auto : bool, optional
        Whether to automatically find windows containing good measurements, by
        default False.
    pH_equation : str, optional
        Which pH equation to use, either `"NIOZ"` (default) or `"DSC07"`.

    Returns
    -------
    pd.DataFrame
        The imported dataset.  Each row corresponds to a separate measurement
        with the spectrophotometer, which is not necessarily a different
        sample.
            Index:
                order : int
                    The order of the rows in the raw pH data file, starting
                    from 1.
            Columns:
                sample_name : str
                    The name of the sample, taken from the Comments file
                    (because the standard data file truncates long sample
                    names).
                dilution_factor : float
                    The dilution factor that was input to the instrument.
                temperature : float
                    The analysis temperature that was input to the instrument.
                salinity : float
                    The sample salinity that was input to the instrument.
                pH_instrument : float
                    The pH as calculated internally by the instrument.
                absorbance_578 : float
                    The measured absorbance at 578 nm.
                absorbance_434 : float
                    The measured absorbance at 434 nm.
                absorbance_730 : float
                    The measured absorbance at 730 nm.
                order_analysis : int
                    A sample counter.  Starts at 1 and increments by 1 each
                    time the `sample_name` changes.
                pH_good : bool
                    Whether this pH measurement is valid and should be used
                    for futher calculations, initially all set to `True`.
                is_tris : bool
                    Whether the sample is tris or not.
                extra_mcp : bool
                    Whether an additional mCP indicator shot was added for
                    this measurement.  `True` where the `sample_name` ends with
                    `"+20"`.
                comments : str
                    Comments to be filled in by the analyst, empty to begin.
    """
    assert pH_equation in pH_equations, (
        '`pH_equation` must be one of `"NIOZ"` or `"DSC07"`.'
    )
    with open(filename, "rb") as f:
        lines = f.read().decode("utf-16").splitlines()
    # Get positions of data tables in the data file
    is_table = False
    table_start = []
    table_end = []
    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            table_start.append(i)
            is_table = True
        if is_table and line.strip() == "":
            table_end.append(i)
            is_table = False
    # Import the data tables
    pH_renamer = {
        "#": "order",
        "Name": "sample_name",
        "Dilut. Factor": "dilution_factor",
        "Weight(25)": "temperature",
        "Volume(35)": "salinity",
        "pH": "pH_instrument",
        "Abs<578nm>": "absorbance_578",
        "Abs<434nm>": "absorbance_434",
        "Abs<730nm>": "absorbance_730",
    }
    ts = table_start[0]
    te = table_end[0]
    measurements = (
        pd.read_fwf(
            filename,
            encoding="utf-16",
            engine="python",
            skiprows=[*range(ts), ts + 1],
            skipfooter=len(lines) - te,
            widths=[11, 17, 15, 13, 13, 13, 14],
        )
        .rename(columns=pH_renamer)
        .set_index("order")
    )
    measurements["sample_name"] = measurements.sample_name.where(
        measurements.sample_name.notnull(), ""
    )
    ts = table_start[1]
    te = table_end[1]
    pH_b = (
        pd.read_fwf(
            filename,
            encoding="utf-16",
            engine="python",
            skiprows=[*range(ts), ts + 1],
            skipfooter=len(lines) - te,
            widths=[11, 17, 15, 14],
        )
        .rename(columns=pH_renamer)
        .set_index("order")
    )
    pH_b["sample_name"] = pH_b.sample_name.where(pH_b.sample_name.notnull(), "")
    for k, v in pH_b.items():
        if k == "sample_name":
            assert (measurements.sample_name == v).all()
        else:
            measurements[k] = v
    #  Import Comments file to get non-truncated sample_name
    with open(filename.replace(".TXT", "-COMMENTS.TXT"), "rb") as f:
        lines = f.read().decode("utf-16").splitlines()
    # Get positions of data tables in Comments file
    is_table = False
    table_start = []
    table_end = []
    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            table_start.append(i)
            is_table = True
        if is_table and line.strip() == "":
            table_end.append(i)
            is_table = False

    # Import middle table
    ts = table_start[1]
    te = table_end[1]
    pH_c = (
        pd.read_fwf(
            filename.replace(".TXT", "-COMMENTS.TXT"),
            encoding="utf-16",
            engine="python",
            skiprows=[*range(ts), ts + 1],
            skipfooter=len(lines) - te,
            widths=[11, 23],
        )
        .rename(columns=pH_renamer)
        .set_index("order")
    )
    pH_c["sample_name"] = pH_c.sample_name.where(pH_c.sample_name.notnull(), "")
    # Update sample_name and append
    for i, row in measurements.iterrows():
        assert pH_c.sample_name.loc[i].startswith(row.sample_name)
    measurements["sample_name"] = pH_c.sample_name
    # Set up additional columns
    measurements = get_order_analysis(measurements)
    sns = measurements.sample_name.str.upper().str
    measurements["is_tris"] = sns.startswith("TRIS") | sns.startswith("NT")
    measurements["extra_mcp"] = sns.endswith("-+20")
    pH_kwargs = {}
    if pH_equation == "DSC07":
        pH_kwargs.update(
            {
                "dye_intercept": dye_intercept,
                "dye_slope": dye_slope,
            }
        )
    measurements["pH"] = pH_equations[pH_equation](
        measurements.absorbance_578,
        measurements.absorbance_434,
        measurements.absorbance_730,
        temperature=measurements.temperature,
        salinity=measurements.salinity,
        **pH_kwargs,
    )
    measurements["pH_good"] = True
    if find_windows_auto:
        measurements.pipe(find_windows)
    measurements["comments"] = ""
    # Enforce single temperature and salinity values for each sample
    measurements = enforce_ts(measurements)
    return measurements
