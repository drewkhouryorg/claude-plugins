import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

const PLUGIN = 'compact-nudge'
const BAND = {
  plugin: PLUGIN,
  surface: 'terminal',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isWorking: false,
    maxRows: 10,
    bodyColumns: 80,
    scroll: { offset: 0, bodyRows: 10 },
    view: {},
  },
} as const

const COMMIT = 'git commit -m "fix: cart totals"'
const QUIET = 'Here is the plan for the next step.'
const FINISHED = 'PR #112 is merged and deployed. Nothing left open.'
const BELOW = 'what the engine draws when no plugin does'

// The session beneath the plugin: context at `pct`, Bash answering as git
// would, the band's own drawing, and every toast recorded.
function session(on: On, opts: { pct: number; commitFails?: boolean }) {
  const toasts: string[] = []
  on('session.usage', () => ({
    value: { startedAt: 0, context: { window: 200_000, percent: opts.pct }, rateLimits: [] },
  }))
  on('tool.call', { tool: 'Bash' }, () =>
    opts.commitFails
      ? { isError: true, result: undefined, text: 'nothing to commit, working tree clean' }
      : { result: { stdout: '[main 3f2a1c9] fix: cart totals', stderr: '', interrupted: false }, text: '[main 3f2a1c9] fix: cart totals' },
  )
  on('turn.complete', (_, e) => ({ text: e.answer }))
  on('prompt.submit', (_, e) => ({ text: e.text, context: e.context }))
  on('ui.toast', (_, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.render', { component: 'AbovePrompt' }, ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>{BELOW}</Text>
  })
  return { toasts }
}

function turnEnd(answer: string, extra: { agentId?: string; isAborted?: boolean; reason?: 'aborted' } = {}) {
  return { answer, durationMs: 4000, isAborted: false, turnId: 'turn-1', reason: 'answer', ...extra } as const
}

const nextPrompt = { text: 'now the checkout page', wait: false, origin: { kind: 'composer' } } as const

test('a commit then a turn end at 65% shows the strong note', async ($, on) => {
  session(on, { pct: 65 })
  await $.tool.call({ tool: 'Bash', command: COMMIT })
  await $.turn.complete(turnEnd(QUIET))
  const ui = await $.ui.mount(BAND)
  const note = await ui.find({ type: 'Text', text: /Good time to break/ })
  expect(note?.text).toContain('65%')
  expect(note?.props.color).toBe('yellow')
})

test('the strong note also raises a toast', async ($, on) => {
  const { toasts } = session(on, { pct: 65 })
  await $.tool.call({ tool: 'Bash', command: COMMIT })
  await $.turn.complete(turnEnd(QUIET))
  expect(toasts).toHaveLength(1)
  expect(toasts[0]).toContain('Good time to break')
})

test('a commit at 50% shows the soft note and no toast', async ($, on) => {
  const { toasts } = session(on, { pct: 50 })
  await $.tool.call({ tool: 'Bash', command: COMMIT })
  await $.turn.complete(turnEnd(QUIET))
  const ui = await $.ui.mount(BAND)
  expect((await ui.find({ type: 'Text', text: /Clean point/ }))?.text).toContain('50%')
  expect(toasts).toHaveLength(0)
})

test('Claude saying it is done counts without a commit', async ($, on) => {
  session(on, { pct: 65 })
  await $.turn.complete(turnEnd(FINISHED))
  const ui = await $.ui.mount(BAND)
  expect(await ui.find({ type: 'Text', text: /Claude says it is done/ })).toBeDefined()
})

test('below 45% the band falls through even after a commit', async ($, on) => {
  session(on, { pct: 40 })
  await $.tool.call({ tool: 'Bash', command: COMMIT })
  await $.turn.complete(turnEnd(FINISHED))
  const ui = await $.ui.mount(BAND)
  expect(await ui.find({ text: BELOW })).toBeDefined()
})

test('no commit and no done answer leaves the band alone at high context', async ($, on) => {
  session(on, { pct: 85 })
  await $.tool.call({ tool: 'Bash', command: 'git status' })
  await $.turn.complete(turnEnd(QUIET))
  const ui = await $.ui.mount(BAND)
  expect(await ui.find({ text: BELOW })).toBeDefined()
})

test('the next prompt clears the note', async ($, on) => {
  session(on, { pct: 65 })
  const ui = await $.ui.mount(BAND)
  await $.tool.call({ tool: 'Bash', command: COMMIT })
  await $.turn.complete(turnEnd(QUIET))
  expect(await ui.find({ type: 'Text', text: /Good time to break/ })).toBeDefined()
  await $.prompt.submit(nextPrompt)
  expect(await ui.find({ type: 'Text', text: /Good time to break/ })).toBeUndefined()
  expect(await ui.find({ text: BELOW })).toBeDefined()
})

test('a subagent finishing its turn draws nothing', async ($, on) => {
  const { toasts } = session(on, { pct: 65 })
  await $.tool.call({ tool: 'Bash', command: COMMIT })
  await $.turn.complete(turnEnd(FINISHED, { agentId: 'agent-7' }))
  const ui = await $.ui.mount(BAND)
  expect(await ui.find({ text: BELOW })).toBeDefined()
  expect(toasts).toHaveLength(0)
})

test('an interrupted turn draws nothing', async ($, on) => {
  session(on, { pct: 65 })
  await $.tool.call({ tool: 'Bash', command: COMMIT })
  await $.turn.complete(turnEnd(QUIET, { isAborted: true, reason: 'aborted' }))
  const ui = await $.ui.mount(BAND)
  expect(await ui.find({ text: BELOW })).toBeDefined()
})

test('a survey in the band keeps the note out of its way', async ($, on) => {
  session(on, { pct: 65 })
  await $.tool.call({ tool: 'Bash', command: COMMIT })
  await $.turn.complete(turnEnd(QUIET))
  const ui = await $.ui.mount({ ...BAND, props: { ...BAND.props, hasSurvey: true } })
  expect(await ui.find({ text: BELOW })).toBeDefined()
})

test('a failed commit does not count as shipping', async ($, on) => {
  session(on, { pct: 65, commitFails: true })
  await $.tool.call({ tool: 'Bash', command: COMMIT })
  await $.turn.complete(turnEnd(QUIET))
  const ui = await $.ui.mount(BAND)
  expect(await ui.find({ text: BELOW })).toBeDefined()
})

test('nothing reaches the model or the transcript across a full nudge', async ($, on) => {
  session(on, { pct: 65 })
  const transcript = mock.session(on)
  on('prompt.context', (_, e) => ({ blocks: e.blocks }))
  on('prompt.section', (_, e) => ({ text: e.text }))

  const ran = await $.tool.call({ tool: 'Bash', command: COMMIT })
  expect(ran.context).toBeUndefined()
  const done = await $.turn.complete(turnEnd(QUIET))
  expect(done).toEqual({ text: QUIET })
  const ui = await $.ui.mount(BAND)
  expect(await ui.find({ type: 'Text', text: /Good time to break/ })).toBeDefined()

  const blocks = [{ name: 'currentDate', text: '2026-10-12' }]
  expect(await $.prompt.context({ blocks })).toEqual({ blocks })
  expect(await $.prompt.section({ name: 'memory', text: 'memory as core built it' })).toEqual({
    text: 'memory as core built it',
  })
  const sent = await $.prompt.submit(nextPrompt)
  expect(sent).toEqual({ text: nextPrompt.text })
  expect(transcript.appended()).toHaveLength(0)
})
