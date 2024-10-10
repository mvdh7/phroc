import koolstof as ks

data = ks.spectro.read_agilent_pH("2024-04-27-CTD1.TXT")
data["pH"] = ks.spectro.pH_NIOZ(
    data.abs578,
    data.abs434,
    data.abs730,
    temperature=data.temperature,
    salinity=data.salinity,
)
samples = data[["sample_name", "pH"]].groupby("sample_name").mean()
