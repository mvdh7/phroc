import numpy as np


def pH_NIOZ(
    absorbance_578: float,
    absorbance_434: float,
    absorbance_730: float,
    temperature: float = 25,
    salinity: float = 35,
) -> float:
    """Calculate pH from NIOZ spectrophotometer absorbances.

    Parameters
    ----------
    absorbance_578 : float
        Absorbance at 578 nm.
    absorbance_434 : float
        Absorbance at 434 nm.
    absorbance_730 : float
        Absorbance at 730 nm.
    temperature : float, optional
        Temperature in °C, by default 25.
    salinity : float, optional
        Practical salinity, by default 35.

    Returns
    -------
    float
        pH on the total scale.
    """
    WL1 = absorbance_578
    WL2 = absorbance_434
    WL3 = absorbance_730
    pH_total = (
        np.log10(
            (((WL1 - WL3) / (WL2 - WL3) - 0.00815 * WL1) - 0.00691)
            / (2.222 - ((WL1 - WL3) / (WL2 - WL3) - 0.00815 * WL1) * 0.1331)
        )
        + 1245.69 / (temperature + 273.15)
        + 3.8275
        + 0.00211 * (35 - salinity)
    )
    return pH_total


def pH_DSC07(
    absorbance_578: float,
    absorbance_434: float,
    absorbance_730: float,
    temperature: float = 25,
    salinity: float = 35,
    dye_intercept: float = 0,
    dye_slope: float = 0,
) -> float:
    """Calculate pH following SOP 6b, including dye addition correction if
    known.

    Parameters
    ----------
    absorbance_578 : float
        Absorbance at 578 nm.
    absorbance_434 : float
        Absorbance at 434 nm.
    absorbance_730 : float
        Absorbance at 730 nm.
    temperature : float, optional
        Temperature in °C, by default 25.
    salinity : float, optional
        Practical salinity, by default 35.
    dye_intercept : float, optional
        Intercept of the dye correction (SOP 6b eq. 9), by default 0.
    dye_slope : float, optional
        Slope of the dye correction (SOP 6b eq. 9), by default 0.

    Returns
    -------
    float
        pH on the total scale.
    """
    WL1 = absorbance_578
    WL2 = absorbance_434
    WL3 = absorbance_730
    ratio_raw = (WL1 - WL3) / (WL2 - WL3)
    ratio = ratio_raw - (dye_intercept + dye_slope * ratio_raw)
    pH_total = (
        np.log10((ratio - 0.00691) / (2.222 - ratio * 0.1331))
        + 1245.69 / (temperature + 273.15)
        + 3.8275
        + 0.00211 * (35 - salinity)
    )
    return pH_total


def pH_tris_DD98(
    temperature: float = 25,
    salinity: float = 35,
) -> float:
    """Calculate pH of tris buffer following DelValls and Dickson (1998),
    equation 18.

    Parameters
    ----------
    temperature : float, optional
        Temperature in °C, by default 25.
    salinity : float, optional
        Practical salinity, by default 35.

    Returns
    -------
    float
        pH on the total scale.
    """
    T = temperature + 273.15
    S = salinity
    pH = (
        (11911.08 - 18.2499 * S - 0.039336 * S**2) / T
        - 366.27059
        + 0.53993607 * S
        + 0.00016329 * S**2
        + (64.52243 - 0.084041 * S) * np.log(T)
        - 0.11149858 * T
    )
    return pH
