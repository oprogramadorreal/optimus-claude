# Review contract

`average` accepts a finite sequence of numbers. An empty sequence has no average and returns `None`. `first_if_present` already handles empty sequences and is not a requested redesign.

The hand-authored migration converts existing positive invoice amounts with exactly two decimal places to integer cents, preserving their value. The generated schema snapshot is checked in to document the tool output, and contains no monetary conversion logic.

This is a read-only review. Report demonstrable bugs rather than style preferences or hypothetical future inputs outside these contracts.
