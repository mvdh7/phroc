import phroc


filename = "/Users/matthew/github/pyside-learn/2024-04-27-CTD1"
measurements, samples = phroc.funcs.read_measurements_create_samples(
    "{}.TXT".format(filename)
)
phroc.funcs.write_phroc(filename, measurements, samples)

# %%
import os
import tempfile
import zipfile
import pandas as pd

# with tempfile.TemporaryDirectory() as tdir:
#     with zipfile.ZipFile(filename + ".phroc", 'r') as z:
#         z.extractall(tdir)
#     print(tdir)
#     print(os.listdir(tdir))

# measurements_z = pd.read_parquet(os.path.join(tdir, tdir, "measurements.parquet"))

# tdir = tempfile.TemporaryDirectory()
# with zipfile.ZipFile(filename + ".phroc", 'r') as z:
#     z.extractall(tdir.name)
# print(tdir.name)
# print(os.listdir(tdir.name))
# print(type(tdir.name))
# tdir.cleanup()


# with tempfile.TemporaryDirectory() as tdir:
#     print(os.listdir(tdir))
#     samples.to_parquet(os.path.join(tdir, "samples.parquet"))
#     print(os.listdir(tdir))
#     samples_x = pd.read_parquet(os.path.join(tdir, "samples.parquet"))


# with tempfile.TemporaryDirectory() as tdir:
tdir = "testex"
cwd = os.getcwd()
os.chdir(tdir)
measurements.to_parquet("measurements.parquet")
samples.to_parquet("samples.parquet")
if not filename.endswith(".phroc"):
    filename += ".phroc"
with zipfile.ZipFile(
    os.path.join(cwd, filename), compression=zipfile.ZIP_LZMA, mode="w"
) as z:
    z.write("measurements.parquet")
    z.write("samples.parquet")
os.chdir(cwd)

with tempfile.TemporaryDirectory() as tdir:
    with zipfile.ZipFile("test_exports/2024-04-27-CTD1.phroc", "r") as z:
        z.extractall(tdir)
    measurements_p = pd.read_parquet(os.path.join(tdir, "measurements.parquet"))
    samples_p = pd.read_parquet(os.path.join(tdir, "samples.parquet"))


# %%
