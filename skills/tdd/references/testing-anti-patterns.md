# Testing Anti-Patterns

Load this reference when writing or reviewing tests — especially before adding mocks.

## Core Principle

**Test what the code does, not what the mocks do.** Mocks are a means to isolate; they are never the thing being tested.

## The Three Iron Laws of Mocking

1. **Never assert on mock behavior** — assert on the code under test. If your assertion checks that a mock exists or was called, you're testing the mock, not your code.
2. **Never add test-only methods to production classes** — if a method only exists for tests (e.g., `destroy()`, `reset()`), move it to test utilities instead. Test-only methods pollute the production API and are dangerous if called accidentally.
3. **Never mock without understanding the dependency** — before mocking, ask: "What side effects does the real method have? Does this test depend on any of them?" If yes, mock at a lower level or use the real implementation.

## Anti-Pattern 1: Testing Mock Behavior Instead of Real Behavior

**Bad** — asserting on the mock, not the component:
```
test('renders sidebar', () => {
  render(<Page />)
  expect(screen.getByTestId('sidebar-mock')).toBeInTheDocument()
  // ^ Testing that the mock exists, not that the page works
})
```

**Good** — asserting on real behavior:
```
test('renders sidebar', () => {
  render(<Page />)  // Don't mock sidebar
  expect(screen.getByRole('navigation')).toBeInTheDocument()
})
```

**Gate question:** "Am I asserting on the mock or on the actual code under test?"

## Anti-Pattern 2: Mocking Without Understanding Dependencies

**Bad** — over-mocking breaks the test:
```
test('detects duplicate server', async () => {
  vi.mock('ConfigManager', () => ({
    saveConfig: vi.fn()  // Mock prevents config write that test depends on!
  }))
  await addServer(config)
  await addServer(config)  // Should throw duplicate error, but won't
})
```

**Good** — mock only the slow/external part, preserve behavior the test needs:
```
test('detects duplicate server', async () => {
  vi.mock('NetworkClient')  // Only mock the slow network call
  await addServer(config)   // Config write happens for real
  await addServer(config)   // Duplicate detected correctly
})
```

**Gate question:** "Do I know what side effects the real method has? Does this test depend on any of them?"

## Anti-Pattern 3: Over-Mocking When Real Code Works

**Symptoms:**
- Mock setup is longer than the test logic
- Test breaks when mock structure changes but real code is fine
- You're mocking internal modules, not external services

**The rule:** Only mock what you must — external services (APIs, databases), non-deterministic behavior (time, randomness), and slow I/O. If the real implementation is fast and deterministic, use it.

**Gate question:** "Can this test use the real implementation? Am I mocking for isolation or out of habit?"

## Quick Reference

| Anti-Pattern | Gate Question | Fix |
|---|---|---|
| Asserting on mock elements | "Am I testing the mock or the code?" | Test real behavior or unmock it |
| Mocking without understanding deps | "Does this test depend on mocked side effects?" | Mock at lower level, preserve needed behavior |
| Over-mocking | "Can this test use real code?" | Only mock external services and non-deterministic deps |
| Test-only methods in production | "Is this method only called from tests?" | Move to test utilities |
| Incomplete mock data | "Does my mock mirror the real data structure?" | Include all fields the real API returns |

## Red Flags — Stop and Reconsider

- Assertion checks for `*-mock` test IDs
- Mock setup is >50% of the test
- Test fails when you remove the mock (but real code works)
- You're mocking "just to be safe"
- Can't explain why the mock is needed
