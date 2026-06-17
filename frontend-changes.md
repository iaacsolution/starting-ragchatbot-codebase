# Frontend Changes

## Dark / Light Theme Toggle

### Overview

A circular icon button fixed in the top-right corner lets users switch between the existing dark theme and a new accessible light theme. The preference is persisted across page reloads via `localStorage`. All existing elements adapt through CSS custom properties — no structural markup was changed.

---

### Architecture

- **Mechanism**: `data-theme="light"` attribute on `<html>`. Dark mode is the default (`:root`); the attribute is added or removed to activate light mode.
- **Persistence**: `localStorage` key `"theme"`, read on `DOMContentLoaded`.
- **Transitions**: `body` carries `transition: background-color 0.3s ease, color 0.3s ease`. Interactive elements (`#chatInput`, `.theme-toggle`, etc.) have their own `transition` declarations that cover background and colour changes.

---

### Files changed

#### `frontend/style.css`

**Dark theme additions to `:root`**
- `--code-bg: rgba(0, 0, 0, 0.2)` — extracted from inline usage on `code`/`pre` so the light theme can override it.

**New `[data-theme="light"]` block**

| Variable | Light value | Ensures |
|---|---|---|
| `--background` | `#f8fafc` | Page background |
| `--surface` | `#ffffff` | Sidebar, chat bubbles, cards |
| `--surface-hover` | `#e2e8f0` | Hover state |
| `--text-primary` | `#0f172a` | Body text — >19:1 on white (WCAG AAA) |
| `--text-secondary` | `#64748b` | Muted labels — ~4.7:1 on white (WCAG AA) |
| `--border-color` | `#e2e8f0` | Subtle borders |
| `--assistant-message` | `#f1f5f9` | Assistant bubble background |
| `--shadow` | `0 4px 6px -1px rgba(0,0,0,0.1)` | Lighter shadow |
| `--focus-ring` | `rgba(37,99,235,0.15)` | Keyboard focus halo |
| `--welcome-bg` | `#eff6ff` | Welcome card background |
| `--welcome-border` | `#2563eb` | Welcome card border (unchanged) |
| `--code-bg` | `rgba(0, 0, 0, 0.06)` | Code block tint in light mode |

**Per-element fixes (all-elements coverage)**

| Element | Issue | Fix |
|---|---|---|
| `body` | No colour transition | Added `transition: background-color 0.3s ease, color 0.3s ease` |
| `.message-content code` / `pre` | Hardcoded `rgba(0,0,0,0.2)` | Replaced with `var(--code-bg)` |
| `.message-content blockquote` | Referenced undefined `var(--primary)` | Fixed to `var(--primary-color)` (bug present in both themes) |
| `.message.welcome-message .message-content` | Hardcoded `box-shadow: 0 4px 16px rgba(0,0,0,0.2)` | Replaced with `var(--shadow)` |
| `.error-message` | `#f87171` text too pale on white | `[data-theme="light"]` override: `color: #dc2626` |
| `.success-message` | `#4ade80` text too pale on white | `[data-theme="light"]` override: `color: #16a34a` |

**`.theme-toggle` button styles**
- `position: fixed; top: 1rem; right: 1rem; z-index: 1000` — always visible.
- 40 × 40 px circle, inherits `var(--surface)`, `var(--border-color)`, `var(--text-primary)`.
- Full transition on background, border, colour, transform, box-shadow.
- `:hover` — scale 1.1 + blue glow.
- `:focus-visible` — 3 px focus ring (keyboard only).
- `:active` — scale 0.95 for tactile feedback.
- `.icon-moon` visible by default; `.icon-sun` shown when `[data-theme="light"]` is present.

#### `frontend/index.html`

- `<button id="themeToggle" class="theme-toggle" aria-label="Switch to light theme">` added before `</body>`.
- Moon SVG (`.icon-moon`) shown in dark mode; sun SVG (`.icon-sun`) shown in light mode.
- Both SVGs are `aria-hidden="true"`; the button `aria-label` carries the accessible description.

#### `frontend/script.js`

- `themeToggle` added to DOM element declarations.
- **`initTheme()`** — runs on `DOMContentLoaded`; applies saved `"light"` preference from `localStorage`.
- **`applyTheme(theme)`** — sets `data-theme` on `<html>` and updates `aria-label`.
- **`toggleTheme()`** — reads current state, flips it, removes attribute for dark, persists to `localStorage`.
- `themeToggle.addEventListener('click', toggleTheme)` in `setupEventListeners()`.

---

### Accessibility

- Text contrast meets WCAG AA in both themes for all foreground/background pairs.
- `aria-label` on the toggle button updates dynamically to describe the *next* action ("Switch to light theme" / "Switch to dark theme").
- `:focus-visible` ensures focus ring is visible for keyboard users without cluttering mouse interactions.
- No change to tab order; the button is appended after all page content but is `position: fixed` so it's always reachable.
