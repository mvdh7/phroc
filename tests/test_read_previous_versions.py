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


def test_phroc_v0_3():
    usd_phroc_v0_3 = read_phroc(
        "tests/data/previous_versions/2024-04-27-CTD1__v0_3.phroc"
    )
    assert isinstance(usd_phroc_v0_3, UpdatingSummaryDataset)


def test_excel_v0_3():
    usd_excel_v0_3 = read_excel(
        "tests/data/previous_versions/2024-04-27-CTD1__v0_3.xlsx"
    )
    assert isinstance(usd_excel_v0_3, UpdatingSummaryDataset)


def test_phroc_v0_4():
    usd_phroc_v0_4 = read_phroc(
        "tests/data/previous_versions/2024-04-27-CTD1__v0_4.phroc"
    )
    assert isinstance(usd_phroc_v0_4, UpdatingSummaryDataset)


def test_excel_v0_4():
    usd_excel_v0_4 = read_excel(
        "tests/data/previous_versions/2024-04-27-CTD1__v0_4.xlsx"
    )
    assert isinstance(usd_excel_v0_4, UpdatingSummaryDataset)


# test_phroc_v0_2()
# test_excel_v0_2()
# test_phroc_v0_3()
# test_excel_v0_3()
# test_phroc_v0_4()
# test_excel_v0_4()
