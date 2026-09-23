# Scenario style

How to write the **Scenarios** section of a spec when the task is stakeholder-facing or names explicit acceptance criteria. Scenarios are plain markdown using Given/When/Then phrasing — no `.feature` files, no Cucumber/Gherkin tooling.

## Format

Each scenario is a `### Scenario:` heading followed by Given/When/Then lines. 3–7 scenarios per feature is the typical range; if you need more, the feature is too large and should be split.

```markdown
## Scenarios

### Scenario: Shopper applies a valid coupon at checkout
**Given** a shopper has a $100 cart and a valid 10% coupon
**When** they apply the coupon at checkout
**Then** the order total drops to $90 and the discount line shows "10% off"

### Scenario: Coupon has expired
**Given** a shopper has a coupon that expired yesterday
**When** they apply the coupon at checkout
**Then** the cart total is unchanged and an "expired coupon" message is shown
```

`And` / `But` are allowed to chain conditions in Given or outcomes in Then.

## Discipline

- **One observable behavior per scenario.** A scenario describes one user-visible outcome. If the Then has two unrelated outcomes, split into two scenarios.
- **Declarative, not imperative.** Describe *what* the user does and observes, not *how* the UI gets them there. Not "click the Apply button, then wait for the spinner to stop" — instead "they apply the coupon."
- **Business language, not implementation language.** "Total drops to $90" is good; "PriceCalculator returns 9000 cents" is not. Scenarios survive refactoring; implementation details don't.
- **Concrete examples.** Real numbers, real strings. "A $100 cart" beats "a non-empty cart"; "yesterday" beats "in the past."
- **Independent.** Each scenario stands alone — no "continuing from the previous scenario" chains.

## Anti-patterns

- **Multi-When chains.** `When ... When ... When ...` is a workflow, not a behavior. Keep one When per scenario; if a setup action is needed, put it in Given.
- **Scenario-Outline overuse.** Don't parameterize 12 rows of inputs to test arithmetic — that's a unit-test concern, not an acceptance criterion. Reserve the scenarios for distinct user-observable cases.
- **Scenarios for refactors or internals.** Internal refactors, infrastructure changes (e.g. switching a cache backend from Redis to an in-process LRU), and developer-only tooling have no stakeholder-facing behavior change — omit the Scenarios section entirely.
- **Vague Given.** "Given the user is on the checkout page" without state is a setup line, not a precondition. State *what is true* in the world, not which page is loaded.
