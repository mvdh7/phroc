# %%
from phroc import UpdatingSummaryDataset, read_excel, read_phroc


def test_phroc_v0_2():
    usd_phroc_v0_2 = read_phroc(
        "tests/data/previous_versions/2024-04-27-CTD1__v0_2.phroc"
    )
    assert isinstance(usd_phroc_v0_2, UpdatingSummaryDataset)


def test_excel_v0_2():
    usd_excel_v0_2 = read_excel(
        "tests/data/previous_versions/2024-04-27-CTD1__v0_2.xlsx"
    )
    assert isinstance(usd_excel_v0_2, UpdatingSummaryDataset)
