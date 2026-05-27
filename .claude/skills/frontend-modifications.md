---
name: Frontend Modifications Guide
description: Guidelines for modifying the web interface
type: skill
---

# Frontend Modifications Skill

Guidance for working with the HTML/CSS/JavaScript frontend.

## Frontend Files

| File | Purpose |
|------|---------|
| `frontend/index.html` | DOM structure, sidebar, chat interface |
| `frontend/style.css` | All styling (colors, layout, responsive design) |
| `frontend/script.js` | API calls, event handlers, session management |

## Common Modifications

### 1. Adding Suggested Questions
**File**: `frontend/index.html` (lines ~44-50)

```html
<button class="suggested-item" data-question="What is the course about?">
  Course Overview
</button>
```

- `data-question`: The actual question sent to API
- Button text: What users see

### 2. Changing UI Colors/Styling
**File**: `frontend/style.css`

Key CSS classes:
- `.container`: Main wrapper
- `.header`: Title section
- `.sidebar`: Left panel with stats
- `.chat-message`: Message bubbles (`.user` vs `.assistant`)
- `.chat-input`: Input box styling

Example: Change primary color
```css
.header {
  background-color: #your-color;
}
```

### 3. Modifying Chat Display
**File**: `frontend/script.js`

Key functions:
- `addMessage(text, role)`: Display message in chat
- `createLoadingMessage()`: Loading state
- `sendMessage()`: Handle form submission
- `loadCourseStats()`: Fetch course list

### 4. Updating API Endpoint Calls
**File**: `frontend/script.js`

All API calls use relative URL `/api`:
```javascript
const response = await fetch(`${API_URL}/query`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query, session_id: currentSessionId })
});
```

To add new endpoint call:
1. Use same `/api` prefix
2. Parse response JSON
3. Update DOM with results
4. Handle errors gracefully

### 5. Changing Page Title & Headers
**File**: `frontend/index.html`

```html
<title>Your New Title</title>
<h1>Your New Header</h1>
<p class="subtitle">Your subtitle</p>
```

## Testing Frontend Changes

1. **Hot reload**: Changes auto-reflect when server running (no restart needed)
2. **Browser cache**: Use Ctrl+Shift+R (hard refresh) if changes don't appear
3. **Session persistence**: Clear `currentSessionId` in browser console to reset
4. **Mobile view**: Use Firefox/Chrome DevTools (F12) to test responsive design

## Layout Structure

```
┌─ HEADER ─────────────────────────────┐
│ Course Materials Assistant           │
├──────────┬──────────────────────────┤
│ SIDEBAR  │   MAIN CONTENT           │
│ • Stats  │ • Chat messages display  │
│ • Tips   │ • Input box + send btn   │
│          │                          │
└──────────┴──────────────────────────┘
```

## Accessibility Notes

- All buttons have accessible labels
- Input validation: Don't submit empty queries
- Session ID persists across page reloads
- Loading state prevents duplicate submissions

## Debugging Frontend

In browser console (F12):
```javascript
// Check current session
console.log(currentSessionId)

// Manually call API
fetch('/api/courses').then(r => r.json()).then(console.log)

// View last query
console.log(chatMessages.lastChild)
```
