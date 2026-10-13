export type Tier = 'soft' | 'strong'
export type Nudge = { tier: Tier; pct: number; why: string }

declare module 'claude-code' {
  interface PluginState {
    'compact-nudge': { nudge: Nudge | null; lastFiredPct: number }
  }
}
