import tempfile
import os
import phroc
import pandas as pd
import numpy as np


filename = "tests/data/2024-04-27-CTD1"
measurements, samples = phroc.funcs.read_measurements_create_samples(
    "{}.TXT".format(filename)
)


def test_read():
    assert isinstance(measurements, pd.DataFrame)
    assert isinstance(samples, pd.DataFrame)


def test_write_read_phroc():
    fname = "test_funcs"
    with tempfile.TemporaryDirectory() as tdir:
        phroc.funcs.write_phroc(os.path.join(tdir, fname), measurements, samples)
        assert "{}.phroc".format(fname) in os.listdir(tdir)
        measurements_p, samples_p = phroc.funcs.read_phroc(
            os.path.join(tdir, "{}.phroc".format(fname))
        )
    assert (measurements_p == measurements).all().all()
    assert (
        ((samples_p == samples) | (samples_p.isnull() & samples.isnull())).all().all()
    )


def test_write_read_excel():
    fname = "test_funcs"
    with tempfile.TemporaryDirectory() as tdir:
        phroc.funcs.write_excel(os.path.join(tdir, fname), measurements, samples)
        assert "{}.xlsx".format(fname) in os.listdir(tdir)
        measurements_p, samples_p = phroc.funcs.read_excel(
            os.path.join(tdir, "{}.xlsx".format(fname))
        )
    for c in measurements_p.columns:
        if measurements[c].dtype == float:
            assert np.all(np.isclose(measurements_p[c], measurements[c]))
        else:
            assert (measurements_p[c] == measurements[c]).all()
    for c in samples_p.columns:
        if samples[c].dtype == float:
            assert np.all(
                np.isclose(samples_p[c], samples[c])
                | (samples_p[c].isnull() & samples[c].isnull())
            )
        else:
            assert (samples_p[c] == samples[c]).all()


# test_read()
# test_write_read_phroc()
# test_write_read_excel()
