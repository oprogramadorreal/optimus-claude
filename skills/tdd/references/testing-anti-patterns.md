# Testing Anti-Patterns

Read when writing or reviewing tests — especially before adding mocks.

## Core principle

**Test what the code does, not what the mocks do.** Mocks are a means to isolate; they are never the thing being tested.

## The three iron laws of mocking

1. **Never assert on mock behavior** — assert on the code under test. If an assertion checks that a mock exists or was called, it tests the mock, not the code.
2. **Never add test-only methods to production classes** — a method only tests call (e.g., `destroy()`, `reset()`) belongs in test utilities; it pollutes the production API and is dangerous if called accidentally.
3. **Never mock without understanding the dependency** — before mocking, ask what side effects the real method has and whether the test depends on any of them. If yes, mock at a lower level or use the real implementation.

## Four gate questions

### 1. "Am I asserting on the mock or on the code under test?"

- Bad: `expect(screen.getByTestId('sidebar-mock')).toBeInTheDocument()` — proves the mock renders, not that the page works.
- Good: don't mock the sidebar — `expect(screen.getByRole('navigation')).toBeInTheDocument()`.

### 2. "Does this test depend on side effects I've mocked away?"

- Bad: mocking `ConfigManager.saveConfig` in a duplicate-server test — the duplicate check reads the config the mock never wrote, so the expected error never fires.
- Good: mock only the slow network client; let the config write happen for real.

### 3. "Can this test use the real implementation?"

Only mock what you must: external services (APIs, databases), non-deterministic behavior (time, randomness), and slow I/O. If the real code is fast and deterministic, use it. Over-mocking symptoms: mock setup longer than the test logic, tests that break when the mock changes while the real code is fine, mocks of internal modules rather than external services.

### 4. "Am I verifying through the public interface or a backdoor?"

- Bad: `db.query('SELECT * FROM users WHERE name = ?', ['Alice'])` to check that `createUser` saved — couples the test to a storage decision; a schema change breaks it while the code still works.
- Good: `getUser(user.id)` — read the result back through the API the system exposes. If no interface exists to read it back, that is a design gap.

## Red flags — stop and reconsider

- An assertion checks for `*-mock` test IDs
- Mock setup is >50% of the test
- The test fails when you remove the mock, but the real code works
- Mocking "just to be safe", or you can't explain why the mock is needed
- Mock data missing fields the real API returns
