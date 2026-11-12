# Evaluating paired discharge

The formal paper analysis calls this metric function for daily pairs, complete-month mean flows and subsets grouped by flow. This public module extracts the calculation only. It does not read observations, choose evaluation periods, build monthly series, fit a correction model or publish performance results.

Supply two aligned one-dimensional sequences of discharge in m3/s, observed first. Check dates, station, units and interval lengths before calling: matching array shapes do not prove matching dates. When both inputs are pandas Series, their index labels must be present, unique and match in order. If either input is unlabeled, pairing is positional. The function discards a pair if either value is not finite and reports the retained count. It does not interpolate or automatically remove extreme flows. Fewer than three valid pairs yield undefined metrics (NaN).

Modified KGE (2012) uses the correlation, mean ratio and coefficient-of-variation ratio. KGE (2009) uses the standard-deviation ratio instead. NSE measures error relative to the observed mean baseline; RMSE and MAE retain the discharge units. Positive percent bias means overestimation. Volume bias uses the same sums as percent bias and represents a volume comparison only for equally weighted time steps; it does not integrate unequal-length months. Undefined ratios and correlations must not be interpreted as zero. The inherited function returns no KGE when either series is constant or has zero mean.

Use the same predeclared period and paired samples for comparisons. Keep calibration and independent evaluation separate. The numerical example is invented, not derived from station observations. From the repository root, with Python 3.10+ and NumPy:

```bash
PYTHONPATH=src python examples/discharge_metrics_demo.py
PYTHONPATH=src python -m unittest discover -s tests -p 'test_discharge_metrics.py'
```
