import phroc


filename = "tests/data/2024-04-27-CTD1"
measurements, samples = phroc.funcs.read_measurements_create_samples(
    "{}.TXT".format(filename)
)
# phroc.funcs.write_phroc(filename, measurements, samples)
