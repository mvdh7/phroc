# %%
from phroc.process.usd import UpdatingSummaryDataset


# measurements = read_agilent_pH("tests/data/2024-04-27-CTD1.TXT")
usd = UpdatingSummaryDataset("tests/data/2024-04-27-CTD1.TXT")
usd.set_measurement(1, pH_good=False, sample_name="okay")
usd.set_measurement(2, sample_name="test")
usd.set_sample(3, salinity=3, temperature=5, is_tris=True)
usd.set_measurement(8, sample_name="testerr")
usd.set_sample(5, is_tris=False, sample_name="BETTER")
usd.set_sample(3, sample_name="test")
usd.set_measurement(5, sample_name="??")
usd.samples
