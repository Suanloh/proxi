# PROXI UI guidelines

The visual direction is a security control surface: show which agent requested what, the exact scope, the backend's decision, and what happened next. Favor explicit states and traceable events over chat bubbles or generic dashboard metrics. This palette is a starting point, not a fixed brand specification.

| Area | Convention |
| --- | --- |
| Primary | Security blue for primary actions and emphasis (`primary`). Do not use it to convey a decision. |
| Secondary | Neutral slate (`secondary`/`muted`) for supporting controls; lightly tinted blue (`accent`) for hover and selection, with a visible selected or pressed state. |
| Surfaces | Cool off-white canvas and white cards in light mode; navy canvas and lighter slate cards in dark mode. Use `background`/`foreground` and `card`/`card-foreground` pairs. |
| Typography | System sans for UI, mono for IDs, timestamps and compact technical labels. Use sentence case, a clear heading hierarchy, and readable wrapping for long values. |
| Spacing | Use Tailwind's 4px base scale: 4/8/12px for related items, 16/24px within surfaces, 32/48px between sections. Allow responsive page gutters. |
| Borders and radii | `border` for separators, `input` for control boundaries. Use 6/8px for small controls and 10/14px for larger surfaces. Reserve pill shapes for compact labels. |
| Icons | Prefer the configured Lucide style when icons are added. Pair decision icons with text; decorative icons stay hidden from assistive tech, and icon-only controls need accessible names. |
| Interaction | Distinguish default, hover, pressed/selected, focus-visible, disabled and pending states. Use a visible focus ring, not hover alone. Reserve destructive styling for destructive actions, not decision labels. |
| Themes | Both palettes follow the OS preference; no theme switcher yet. Validate new combinations in both themes and respect reduced-motion preferences. |

Colors are defined in [tokens.css](../../frontend/src/styles/tokens.css) and mapped to semantic Tailwind utilities in [globals.css](../../frontend/src/app/globals.css). Use semantic utilities rather than hex values in components. Spacing, font stacks and type sizes use Tailwind defaults; radius choices are centralized in the global theme.

## Decision and action status

- **ALLOW** (green): backend authorization granted within scope. Execution may still be pending, may fail, or may not occur.
- **HOLD** (amber): the backend is awaiting resolution; the action has not executed. An accepted approval submission is not authorization or execution confirmation.
- **BLOCK** (red): backend denied the action. Show a safe reason when available; never offer an override.
- Unknown or missing decision: render a neutral unavailable state. Never default to ALLOW. Keep decision, approval and execution statuses separate.

Use the `decision-*` background and foreground pairs with a visible text label. Color, risk severity, and trust score are never substitutes for a decision.

## Quality gates for new screens

- Aim for WCAG 2.2 AA, including 4.5:1 for normal text and 3:1 for relevant non-text contrast. Use semantic landmarks, explicit labels and a logical tab order. Verify keyboard-only navigation, visible focus, focus return after dialogs, and mobile/zoom behavior. Keep intentional horizontal scrolling local to dense tables and label the region.
- Provide distinct loading, empty, error and permission-denied states. Mark loading regions busy and announce consequential updates; provide retry when safe. Never replace an error or forbidden response with an empty result. Avoid exposing raw errors or sensitive fields.
- Reuse field-level format and required-field validation, with associated inline errors and focus moved to the first invalid field on submission. Backend validation remains authoritative.
- Confirm sensitive changes with the agent, action, resource and scope clearly shown. Disable duplicate submissions while pending, show acknowledgement separately from execution, and refresh authoritative state after mutations. Do not retry sensitive writes automatically without an explicit idempotency contract.
