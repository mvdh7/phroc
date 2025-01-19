# %%
import numpy as np

from phroc.process.read_raw import read_agilent_pH


measurements = read_agilent_pH("tests/data/2024-04-27-CTD1.TXT")
values = measurements[measurements.order_analysis == 4].pH.values
cutoff = 0.001
minimum_values = 3

# First, sort values, then calculate how many points fall within the `cutoff`
# above each value (`matches`)
values_sorted = np.sort(values)
matches = []
means = []
for i, v in enumerate(values_sorted):
    diff = values_sorted[i + 1 :] - v
    matches.append(np.sum(diff <= cutoff))
    means.append(
        np.mean(values_sorted[(values_sorted >= v) & (values_sorted <= v + cutoff)])
    )
matches = np.array(matches)
means = np.array(means)
# Find which values have the most `matches` - these are candidates for the lower
# bound on the final window - but they have to match at least `minimum_values`
lower_bound = (matches == np.max(matches)) & (matches >= minimum_values - 1)
# If there aren't any suitable lower bounds, the window is all values
if np.sum(lower_bound) == 0:
    print(1)
    window = np.full(values.shape, True)
# If there is only one option for the lower bound, it is the start of the window
elif np.sum(lower_bound) == 1:
    print(2)
    window = (values >= values_sorted[lower_bound]) & (
        values <= values_sorted[lower_bound] + cutoff
    )
# If there are multiple options for the lower bound, take the one that has a
# mean value closest to the population median
else:
    print(3)
    to_median = np.abs(means - np.median(values))
    to_median[~lower_bound] = np.inf
    closest_to_median = to_median == np.min(to_median)
    if sum(closest_to_median) == 1:
        print(4)
        window = (values >= values_sorted[closest_to_median]) & (
            values <= values_sorted[closest_to_median] + cutoff
        )
    # If this still doesn't narrow it down to one option, `window` is all values
    else:
        print(5)
        window = np.full(values.shape, True)
print(window)
