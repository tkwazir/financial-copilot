# Anomaly Detection Evaluation

Generated: 2026-09-20T06:16:35.393940+00:00

Model: Isolation Forest (Snowpark Python stored procedure, trained + scored inside Snowflake compute).

Total transactions scored: 20137

True anomalies (ground truth): 162

Model-flagged transactions: 157


## Overall Metrics

- **Precision:** 0.389 (61/157)
- **Recall:** 0.377 (61/162)
- **F1:** 0.382
- **PR-AUC (average precision):** 0.353

## Recall by Injected Anomaly Type

| Anomaly Type | Caught | Total | Recall |
|---|---|---|---|
| AMOUNT_OUTLIER | 25 | 25 | 1.000 |
| IMPOSSIBLE_TRAVEL | 0 | 15 | 0.000 |
| VELOCITY_BURST | 36 | 122 | 0.295 |

## Methodology Notes

- This is an unsupervised model evaluated against ground truth it never saw during training (features don't include anomaly_type), but `contamination=0.008` was set to match the known synthetic injection rate — a real deployment without ground truth would tune this via a validation set or cost-based thresholding instead. Flagging as a real limitation, not hiding it.
- IMPOSSIBLE_TRAVEL recall is 0% despite `distance_from_home_km` being a clean, large, correctly-computed signal for those rows (verified directly: 1000-4400km vs. 0km for all normal transactions). The actual cause: Isolation Forest's per-tree anomaly score is an average across all 3 features jointly, and with only 15 IMPOSSIBLE_TRAVEL rows against 122 VELOCITY_BURST and 25 AMOUNT_OUTLIER rows competing for the same top-157 score-rank cutoff, this category's scores (max 0.59) fell just below the flagging threshold (0.70) — AMOUNT_OUTLIER (0.76-0.79) and much of VELOCITY_BURST (up to 0.73) ranked higher. The signal is present in the data; the model's combined ranking just doesn't surface it at this contamination level. Worth trying next: a per-feature threshold rule as a second detector alongside the model, or separate models per anomaly-shape rather than one joint model.
