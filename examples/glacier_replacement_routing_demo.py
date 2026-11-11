"""Artificial pulse, split equally between immediate and next-day arrivals."""
from math import log
import pandas as pd
from toshkan_workflow.routing_loss import route_replacement


def main():
    baseline = pd.DataFrame({"A": [100.]}, index=pd.date_range("2000-01-01", periods=1))
    delta = baseline * 0 + (20 - 30)  # External release minus displaced contribution.
    weights = pd.DataFrame({"A": [0.5, 0.5]})
    print(route_replacement(baseline, delta, weights, loss_per_day=log(2)))


if __name__ == "__main__":
    main()
