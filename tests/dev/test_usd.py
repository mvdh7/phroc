# %%
from phroc.process.usd import UpdatingSummaryDataset


# measurements = read_agilent_pH("tests/data/2024-04-27-CTD1.TXT")
usd = UpdatingSummaryDataset("tests/data/2024-04-27-CTD1.TXT")
# usd.set_measurement(1, pH_good=False, sample_name="okay")
# usd.set_measurement(2, sample_name="test")
# usd.set_sample(3, salinity=3, temperature=5, is_tris=True)
# usd.set_measurement(8, sample_name="testerr")
# usd.set_sample(5, is_tris=False, sample_name="BETTER")
# usd.set_sample(3, sample_name="test")
# usd.set_measurement(5, sample_name="??")
usd.set_measurements(
    usd.measurements.sample_name.isin(["JUNK-240427-1", "64PE534-1-4"]), pH_good=False
)

usd.set_sample(2, sample_name="test", comments="comment")
usd.samples
# %%
usd.set_measurement(5, sample_name="test")
usd.samples
