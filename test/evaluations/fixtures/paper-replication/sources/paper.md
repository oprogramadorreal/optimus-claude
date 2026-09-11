# Centered Iterative Estimation (fictional fixture, revision 1)

## Scope and claims

This deliberately small fictional study has three experiments. It provides exact
finite calculations so reproduction can be assessed without a GPU. E1 tests
iterative convergence, E2 studies a randomized estimator, and E3 reports a private
data extension. E1/E2 success does not establish E3. References below are part of
the method, not optional background reading.

## E1: finite iterative convergence

Initialize x at 0 and repeat `x <- x + rate * (target - x)` exactly three times,
with target 8. Evaluate squared error `(x - target)^2` after the third update.
The proposed rate follows the half-step convention in [1]. Use rate 0.25 for the
baseline and rate 0 for the no-update ablation. There is no early stopping,
hyperparameter search, training dataset or random seed in E1.

| Condition | Final prediction | Squared error |
|---|---:|---:|
| Proposed | 7 | 1 |
| Baseline | 4.625 | 11.390625 |
| No-update ablation | 0 | 64 |

Exact real arithmetic defines these targets; floating-point error up to 1e-10 is
an acceptable implementation tolerance. Scientific improvement is unnecessary.

## E2: repeated centered estimation

Use `observations.csv` with the unit conversion, split and sampling procedure in
[1]. The proposed estimate is `(sample + training_mean) / 2`. The raw-sample
baseline predicts `sample`. The no-centering ablation predicts `sample / 2`.
Each predicts a constant on the evaluation split. Its score is mean squared error
over all evaluation examples, with lower values better.

Use seeds 3, 7 and 11, one sample for each seed. Report the arithmetic mean of the
three per-seed scores and their sample standard deviation, not the standard error
or the best seed. Every condition uses the same sampled training value per seed.

| Condition | Mean MSE | Sample SD |
|---|---:|---:|
| Proposed | 59/12 | sqrt(4/3) |
| Raw-sample baseline | 20/3 | sqrt(16/3) |
| No-centering ablation | 41/3 | sqrt(109/3) |

This is a randomized algorithm evaluated on a fixed finite seed set. Reproducing
these enumerated results uses numerical tolerance 1e-10, not an inferred population
equivalence margin. Report raw seed measurements as well as the aggregate.

## E3: private extension

The same proposed E2 estimator achieved mean MSE 0.75 on the private cohort
`private-cohort-v1`, using the same three seeds and split/preprocessing procedure.
The authors cannot distribute this cohort. No public surrogate or statistics
sufficient to recreate it are supplied. E3 therefore requires unavailable data;
claiming reproduction from E1/E2, a synthetic replacement, or this reported number
would be unsupported. The paper does not report E3 variability.

## References and corrections

1. [Half-step and split protocol](protocol.md), fictional technical supplement.
2. [Author clarification](clarification.md), issued after revision 1 and applicable
   to this source version.

The experiments need only tiny in-memory arrays and three short repeats; no
package installation or hardware discovery is necessary for these fixture facts.
