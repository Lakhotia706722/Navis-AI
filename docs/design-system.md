# Navis AI — Design System

## Direction: Deep Water / Navigation Instruments

Dark steel base, amber instrument readouts, chart-blue accent.
Every colour earns its place by function — no decoration.

---

## Colour Tokens

| Token              | Hex       | Role |
|--------------------|-----------|------|
| `--clr-depth`      | `#0B1829` | App shell background |
| `--clr-hull`       | `#132238` | Card surfaces |
| `--clr-bulkhead`   | `#1E3352` | Borders, dividers, input tracks |
| `--clr-chart`      | `#2D9CDB` | Links, focus rings, progress fill |
| `--clr-amber`      | `#F5A623` | CTA buttons, active render indicator |
| `--clr-surface`    | `#F0F4F8` | Body text, input backgrounds |

**Semantic (not stored as CSS vars — use directly):**
- Success / done: `#22C55E`
- Failure / error: `#EF4444`
- Neutral / queued: `#64748B`
- Warning / cost alert: `#F59E0B`

**Rules:**
- `--clr-amber` is allowed only on: primary CTA button, active-render depth column, render-in-progress badge
- `--clr-chart` is never used for warnings — that's amber's job
- No gradients in the nav or background; gradients only in the progress fill

---

## Typography

| Role | Face | Weights | When |
|------|------|---------|------|
| Display | Barlow Condensed | 500, 700 | Page titles, project titles, pipeline stage label. Max 2 per screen. |
| Body | Inter | 400, 500, 600 | All prose, labels, nav, buttons |
| Data | JetBrains Mono | 400, 500 | Percentages, costs, timestamps, token counts, file paths |

**Scale:**
```
--text-xs:      11px   // timestamps, secondary metadata
--text-sm:      13px   // tags, badges, helper text
--text-base:    15px   // body copy, form labels
--text-lg:      18px   // card titles, section headings
--text-xl:      24px   // page headings
--text-2xl:     36px   // detail page project name
--text-display: 48px   // login screen title only
```

---

## Spacing (8-point grid)

```
--space-1:  4px
--space-2:  8px
--space-3: 12px
--space-4: 16px
--space-5: 20px
--space-6: 24px
--space-8: 32px
--space-10: 40px
--space-12: 48px
--space-16: 64px
```

---

## Corner Radius

```
--radius-sm:  4px   // badges, tags
--radius-md:  8px   // cards, inputs, buttons
--radius-lg: 16px   // modals, login panel
```

---

## Shadows (dark-surface adapted)

```
--shadow-card:  0 1px 3px rgba(0,0,0,.4), 0 1px 2px rgba(0,0,0,.3)
--shadow-raise: 0 4px 16px rgba(0,0,0,.5)
--shadow-inset: inset 0 1px 3px rgba(0,0,0,.3)
```

---

## Signature Element — Pipeline Depth Sounder

The render pipeline's 7 stages (queued → planning → composing → rendering → assembling → done | failed)
are shown as a vertical depth column on the left edge of the render status card.

Amber fill rises from bottom as stages complete. Current active stage pulses.
Reads like a vessel's draught marks or a sonar depth gauge.

- Horizontal progress bar = `progress_percent` (0–100)
- Depth column = which pipeline stage (categorical, not linear %)
- Both visible simultaneously; neither replaces the other

Mini version (6px wide strip) appears on project cards in the dashboard.

---

## Motion

- Transitions: `150ms ease` for hover/focus colour changes
- Progress bar fill: `300ms ease` width change
- Depth sounder pulse: `2s ease-in-out infinite` opacity on active stage dot
- Page entrance: `fadeUp 200ms ease` (opacity 0→1, translateY 8px→0)
- `prefers-reduced-motion`: all animations off except instant state changes

---

## Accessibility

- All interactive elements have visible `:focus-visible` ring: `2px solid var(--clr-chart)` offset 2px
- Colour is never the sole signal — status badges use icon + text + colour
- Minimum contrast: text on `--clr-hull` meets WCAG AA (F0F4F8 on 132238 = 8.4:1)
- Keyboard tab order follows visual reading order

---

## Empty States Voice

Not "No data". Invitation to act, in plain declarative language.
Example: "No renders yet — pick a quality and hit Start Render."

## Error State Voice

Not "Something went wrong". Specific cause + fix path.
Example: "Render failed at the composing stage — check scene JSON in the project prompt."
