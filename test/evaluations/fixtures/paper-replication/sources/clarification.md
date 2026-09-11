# Clarification for revision 1 (fictional author addendum)

The phrase "half-step" in E1 means rate 0.5 for the proposed method; it does not
mean half of the baseline's 0.25 rate. The E1 table is correct.

The E2 table's spread is the **sample standard deviation of per-seed MSEs**.
It is not standard error and not a confidence interval. Seeds are fixed by the
protocol; selecting a more favorable seed changes the experiment.

Source-code reuse is permitted if provenance is recorded. No implementation is
supplied in this fixture. Reusing the numerical result table as runtime output
does not reproduce the experiment. The private E3 dataset remains unavailable.
