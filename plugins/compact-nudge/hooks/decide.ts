// Pure rules for when a turn end is a clean break. Thresholds come from a replay
// of 48 past sessions: (shipped or Claude says done) at >= 60% context was
// followed by a break within 3 prompts 32% of the time, against an 11% base rate.
// 45-60% is earlier than people usually broke in those sessions, so it gets the softer note.
// To tune them on your own sessions, see replay/README.md.
import type { Nudge } from '../types'

export const SOFT_PCT = 45
export const STRONG_PCT = 60
export const COOLDOWN_PCT = 10

// git, any options it takes before the subcommand (-C dir, -c key=value,
// --no-pager), then commit, push or merge itself: not merge-base, not
// `stash push`, and not a --dry-run
export const SHIP_CMD =
  /\bgit(\s+(-[cC]\s+\S+|--?[\w-]+(=\S+)?))*\s+(commit|push|merge)(?![\w-])(?![^\n;|&]*--dry-run)|\bgh pr (create|merge)\b|\bmake\b(\s+-C\s+\S+)?(\s+\S+=\S+)*\s+deploy\b|\bfirebase deploy\b/

export const DONE_TEXT =
  /\b(merged|deployed|shipped|all green|is live|nothing (left|outstanding|open)|all done|done\.|landed|wrapped up)/i

export type TurnEnd = {
  pct: number | undefined
  shipped: boolean
  answer: string
  lastFiredPct: number
}

export function decide({ pct, shipped, answer, lastFiredPct }: TurnEnd): {
  nudge: Nudge | null
  lastFiredPct: number
} {
  if (pct === undefined) return { nudge: null, lastFiredPct }
  // Context only shrinks on /compact or /clear: start the cooldown over.
  const last = pct < lastFiredPct ? 0 : lastFiredPct

  const done = DONE_TEXT.test(answer.slice(-600))
  if (pct < SOFT_PCT || !(shipped || done)) return { nudge: null, lastFiredPct: last }

  const crossedStrong = last < STRONG_PCT && pct >= STRONG_PCT
  const cooled = last === 0 || pct >= last + COOLDOWN_PCT
  if (!cooled && !crossedStrong) return { nudge: null, lastFiredPct: last }

  return {
    nudge: {
      tier: pct >= STRONG_PCT ? 'strong' : 'soft',
      pct,
      why: shipped ? 'work just shipped' : 'Claude says it is done',
    },
    lastFiredPct: pct,
  }
}

export function message({ tier, pct, why }: Nudge): string {
  return tier === 'strong'
    ? `Good time to break: ${why}, context ${pct}%. /compact or hand over before the next task.`
    : `Clean point: ${why}, context ${pct}%. Fine to keep going, cheap to /compact now.`
}
