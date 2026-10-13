import { expect, test } from 'claude-code/testing'

import { decide, DONE_TEXT, SHIP_CMD } from './decide'

const QUIET = 'Here is the plan for the next step.'
const FINISHED = 'PR #112 is merged and deployed. Nothing left open.'
const fresh = { lastFiredPct: 0, shipped: false, answer: QUIET }

test('no note below 45% even right after shipping', () => {
  expect(decide({ ...fresh, pct: 44, shipped: true }).nudge).toBe(null)
})

test('no note at high context when nothing shipped or finished', () => {
  expect(decide({ ...fresh, pct: 85 }).nudge).toBe(null)
})

test('shipping between 45% and 60% gives the soft note', () => {
  expect(decide({ ...fresh, pct: 50, shipped: true }).nudge?.tier).toBe('soft')
})

test('Claude saying it is done at 60% or more gives the strong note', () => {
  expect(decide({ ...fresh, pct: 65, answer: FINISHED }).nudge?.tier).toBe('strong')
})

test('stays quiet until context grows another 10% after a note', () => {
  expect(decide({ ...fresh, pct: 70, shipped: true, lastFiredPct: 62 }).nudge).toBe(null)
  expect(decide({ ...fresh, pct: 72, shipped: true, lastFiredPct: 62 }).nudge).not.toBe(null)
})

test('crossing 60% fires the strong note even inside the cooldown', () => {
  expect(decide({ ...fresh, pct: 60, shipped: true, lastFiredPct: 55 }).nudge?.tier).toBe('strong')
})

test('a /compact (context drops) starts the cooldown over', () => {
  const after = decide({ ...fresh, pct: 12, lastFiredPct: 80 })
  expect(after.lastFiredPct).toBe(0)
})

test('no reading of context yet means no note', () => {
  expect(decide({ ...fresh, pct: undefined, shipped: true }).nudge).toBe(null)
})

test('ship commands are recognised in the forms used in past sessions', () => {
  for (const cmd of [
    'git -C /Users/dev/code/acme-shop commit -m "fix: x"',
    'git -c user.name=dev commit -am "fix: y"',
    'npm test && git push',
    'git push origin main',
    'git merge feat/cart',
    'gh pr merge 111 --squash',
    'make -C /Users/dev/code/acme-shop deploy',
    'firebase deploy --only hosting',
  ]) expect(SHIP_CMD.test(cmd)).toBe(true)
})

test('paths or reads that only mention deploy or git are not ships', () => {
  for (const cmd of ['cat ~/code/acme-deploy/README.md', 'git log --oneline -5', 'grep deploy Makefile']) {
    expect(SHIP_CMD.test(cmd)).toBe(false)
  }
})

test('git commands that only read, or only pretend, are not ships', () => {
  for (const cmd of [
    'git merge-base HEAD origin/main',
    'git stash push -m wip',
    'git log --grep commit',
    'git show HEAD:docs/push.md',
    'git push --dry-run origin main',
    'git commit --dry-run -m x',
  ]) {
    expect(SHIP_CMD.test(cmd)).toBe(false)
  }
})

test('ordinary mid-task replies do not read as done', () => {
  expect(DONE_TEXT.test('I will deploy once the tests are green.')).toBe(false)
})
