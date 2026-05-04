# Scenario style

How to write the **Scenarios** section of a design doc when the task is stakeholder-facing or names explicit acceptance criteria. Scenarios are plain markdown using Given/When/Then phrasing — no `.feature` files, no Cucumber/Gherkin tooling.

## When to include

Include a Scenarios section when the work is **stakeholder-facing or acceptance-criteria-driven**. Concretely, include when **any** of these signals apply:
- The task references a JIRA task file with explicit Acceptance Criteria
- The user's intent names a user-visible flow (end-user, cross-team, or regulatory)
- The answers to clarifying questions describe observable outcomes rather than internal mechanics

Omit for internal refactors, infrastructure changes, and developer-only tooling.

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

`And` / `But` are allowed to chain conditions in Given or outcomes in Then. Multiple `When` clauses in a single scenario are an anti-pattern — see below.

## Discipline

- **One observable behavior per scenario.** A scenario describes one user-visible outcome. If the Then has two unrelated outcomes, split into two scenarios.
- **Declarative, not imperative.** Describe *what* the user does and observes, not *how* the UI gets them there. Not "click the Apply button, then wait for the spinner to stop" — instead "they apply the coupon."
- **Business language, not implementation language.** "Total drops to $90" is good; "PriceCalculator returns 9000 cents" is not. Scenarios survive refactoring; implementation details don't.
- **Concrete examples.** Real numbers, real strings. "A $100 cart" beats "a non-empty cart"; "yesterday" beats "in the past."
- **Independent.** Each scenario stands alone — no "continuing from the previous scenario" chains.

## Anti-patterns

- **Multi-When chains.** `When ... When ... When ...` is a workflow, not a behavior. Keep one When per scenario; if a setup action is needed, put it in Given.
- **Scenario-Outline overuse.** Don't parameterize 12 rows of inputs to test arithmetic — that's a unit-test concern, not an acceptance criterion. Reserve the scenarios for distinct user-observable cases.
- **Leaky implementation details.** "Then the `coupons.apply` endpoint returns 200" is a technical assertion, not a behavior. Phrase it as the user-observable outcome ("the discount appears on the order summary").
- **Scenarios for refactors or internals.** If the work is "switch cache backend from Redis to in-process LRU," there is no stakeholder-facing behavior change — omit the Scenarios section entirely. The Components / Approach sections of the design doc cover internal work.
- **Vague Given.** "Given the user is on the checkout page" without state is a setup line, not a precondition. State *what is true* in the world, not which page is loaded.

## Boundary with TDD

The Scenarios section is the **specification**. It belongs in the design doc, alongside Goal/Approach/Components/Interfaces.

`/optimus:tdd` reads the Scenarios section and maps each scenario to one Red-Green-Refactor cycle. Brainstorm does not write tests, does not generate step definitions, and does not run a test framework — those are TDD's job.

If a scenario implies multiple sub-behaviors (e.g., "Then the order total drops AND a confirmation email is sent"), TDD may further decompose it during Step 3 — that's expected. Scenarios are the stakeholder-facing contract; behaviors are the test-driven implementation units.
