// Display only: nothing here writes to the transcript or the model's context.
// The note shows above the prompt when a turn ends at a clean point and goes
// away when the next prompt is sent.
import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Nudge } from '../types'
import { decide, message, SHIP_CMD } from './decide'

const nudge = atom({ plugin: 'compact-nudge', key: 'nudge' } as const, null as Nudge | null)
const lastFiredPct = atom({ plugin: 'compact-nudge', key: 'lastFiredPct' } as const, 0)

export const register: Register = on => {
  let shipped = false

  on('prompt.submit', async ($, e, next) => {
    shipped = false
    await update($, nudge, () => null)
    return next(e)
  }).catch(($, e, next) => next(e))

  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && ran.isError !== true && SHIP_CMD.test(e.command)) {
      shipped = true
    }
    return ran
  }).catch(($, e, next) => next(e))

  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId !== undefined || e.isAborted) return done

    const usage = await $.session.usage()
    const decision = decide({
      pct: usage.context.percent,
      shipped,
      answer: e.answer,
      lastFiredPct: await read($, lastFiredPct),
    })
    await update($, lastFiredPct, () => decision.lastFiredPct)
    if (decision.nudge) {
      await update($, nudge, () => decision.nudge)
      if (decision.nudge.tier === 'strong') {
        $.ui.toast(message(decision.nudge), { timeoutMs: 15000 })
      }
    }
    return done
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const shown = await read($, nudge)
    if (shown === null || e.props.hasSurvey) return next(e)

    const { Box, Text } = $.ui.resolve(e)
    return (
      <Box>
        <Text color={shown.tier === 'strong' ? 'yellow' : 'cyan'} bold={shown.tier === 'strong'}>
          ▸ {message(shown)}
        </Text>
      </Box>
    )
  })
}
