import os
import tempfile

import numpy as np
import pandas as pd

import phroc


filename = "tests/data/2024-04-27-CTD1"
data = phroc.UpdatingSummaryDataset(
    "{}.TXT".format(filename), dye_intercept=0.5, dye_slope=0.5
)


def test_read():
    assert isinstance(data.measurements, pd.DataFrame)
    assert isinstance(data.samples, pd.DataFrame)


def test_write_read_phroc():
    fname = "test_funcs"
    with tempfile.TemporaryDirectory() as tdir:
        data.to_phroc(os.path.join(tdir, fname))
        assert "{}.phroc".format(fname) in os.listdir(tdir)
        data_p = phroc.read_phroc(os.path.join(tdir, "{}.phroc".format(fname)))
    assert (data_p.measurements == data.measurements).all().all()
    assert (
        (
            (data_p.samples == data.samples)
            | (data_p.samples.isnull() & data.samples.isnull())
        )
        .all()
        .all()
    )
    assert data.dye_intercept == data_p.dye_intercept
    assert data.dye_slope == data_p.dye_slope


def test_write_read_excel():
    fname = "test_funcs"
    with tempfile.TemporaryDirectory() as tdir:
        data.to_excel(os.path.join(tdir, fname))
        assert "{}.xlsx".format(fname) in os.listdir(tdir)
        data_p = phroc.read_excel(os.path.join(tdir, "{}.xlsx".format(fname)))
    for c in data_p.measurements.columns:
        if data.measurements[c].dtype == float:
            assert np.all(np.isclose(data_p.measurements[c], data.measurements[c]))
        else:
            assert (data_p.measurements[c] == data.measurements[c]).all()
    for c in data_p.samples.columns:
        if data.samples[c].dtype == float:
            assert np.all(
                np.isclose(data_p.samples[c], data.samples[c])
                | (data_p.samples[c].isnull() & data.samples[c].isnull())
            )
        else:
            assert (data_p.samples[c] == data.samples[c]).all()
    assert data.dye_intercept == data_p.dye_intercept
    assert data.dye_slope == data_p.dye_slope


test_read()
test_write_read_phroc()
test_write_read_excel()
