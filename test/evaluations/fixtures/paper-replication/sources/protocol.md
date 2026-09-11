# Half-step and split protocol (fictional supplement, revision 1)

The half-step convention sets E1's proposed rate to **0.5**, irrespective of the
baseline rate. Preserve the order of CSV rows. Convert every `raw_value` to model
units by dividing by 10 before computing means, sampling or scoring.

Fit the training mean from rows whose `split` is exactly `train`. Evaluate on rows
whose split is `test`. Exclude `calibration` rows from fitting and evaluation. Do
not randomly split, fit on the test examples, include the calibration outlier, or
aggregate all rows together.

For each integer seed independently, create Python `random.Random(seed)`, call
`randrange(number_of_training_rows)` once, and select that training row. Do not
share generator state across seeds, sort samples, draw once per condition, or
replace this procedure with a random generator from a different library. Apply
the proposed, baseline and ablation formulas to this one shared sample.

The experimental matrix comprises all three conditions and all three seeds.
Sample SD divides the sum of squared deviations from the seed-score mean by
`number_of_seeds - 1` before taking the square root.
