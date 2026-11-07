"""Invented rates in m3/s; no files, station records or model output."""
from toshkan_workflow.evaluation import compute_accuracy_metrics


if __name__ == "__main__":
    observed = [1., 2., 3., 4.]
    simulated = [2 * value for value in observed]
    scores = compute_accuracy_metrics(observed, simulated)
    print("Synthetic pairs:", scores["paired_count"])
    print("Mean absolute error (m3/s):", scores["MAE_m3s"])
    print("Bias (%):", scores["PBIAS_percent"])
