# Design: Lenny Growth Assistant

## 1. UI/UX principles

1. **Citations before cleverness.** Every answer should make the source episode obvious. If the corpus cannot support the claim, say so in plain language—no fake confidence.
2. **One primary action.** The composer is the product. Skills (essay, artifact) are secondary, labeled, and never hidden behind mystery commands only.
3. **Provider honesty.** Always show **provider and model** from config (read-only badge). Local mode should feel slightly “lab” so quality gaps are expected. There is no control to switch providers in the UI.
4. **Untrusted output stays in a box.** Generated HTML never shares the app’s visual trust (same fonts/chrome as system UI).
5. **Calm density.** Lenny-adjacent: readable type, generous line length in chat, no dashboard chrome. Color is for status (ok / degraded / error), not decoration.
6. **Recoverable errors.** Prefer “Retry” and a one-line cause over a blank screen.

## 2. Information architecture

```
App shell
├── Header
│   ├── Product name: “Lenny Growth Assistant”
│   ├── Provider chip (read-only): “Ollama · qwen2.5:3b” or “Anthropic · {ANTHROPIC_MODEL}”
│   └── Health dot (ok / degraded / down)
├── Sidebar (collapsible)
│   ├── New chat
│   └── Session list (title, relative time)
└── Main
    ├── Chat column (always)
    │   ├── Empty / message thread
    │   ├── Citation drawer (inline chips → expand)
    │   └── Composer + skill shortcuts
    └── Artifact pane (conditional, ~40% width desktop)
        ├── Title + format badge (MD | HTML)
        ├── Render surface
        └── Copy source / close
```

**Routes (minimal):** `/` current or new session; `/s/:sessionId` deep link for the reviewer. No marketing pages, login, settings, or provider-picker screens. Display name, if any, is an optional field in a small “session details” popover (`user_metadata`).

**Skill shortcuts in the composer toolbar:**

- Ask (default)
- Ship 30 essay
- Make artifact

These set `intent` on the next send; the user still types the topic.

## 3. Key interaction states

### Loading

| Surface | Behavior |
|---------|----------|
| App boot | Skeleton sidebar + composer; fetch `/health` + sessions. Do not block the shell on the LLM. |
| Sending | User message pins immediately. Assistant row shows a **streaming cursor** or “Retrieving transcripts…” then tokens. Disable Send; keep Stop if streaming is cancellable (nice-to-have). |
| Essay | Extra status: “Drafting essay (~1,250 words) — this can take a minute.” |
| Ingest | Not a user-facing flow. Runs on API startup; reviewers may call `POST /api/ingest`. Counts belong in structured logs, not a progress modal. |

### Empty

- **No sessions:** Sidebar CTA “New chat”. Main: one-paragraph purpose (“Ask a growth question. Answers cite Lenny’s Podcast episodes.”) + 3 example prompts pulled from real topics (activation, PMF, PLG).
- **Session with no messages:** Same examples, no fake history.
- **Empty retrieval (not an error):** Assistant message, distinct from a crash: “The transcripts I have don’t support an answer to this. Try a product, growth, or career topic from Lenny’s Podcast.” No citation chips.

### Error

Map `error_class` to copy + action:

| Class | Banner / inline | Action |
|-------|-----------------|--------|
| `provider_unconfigured` | Friendly, non-technical: “Cloud answers are turned on, but no Anthropic API key is set. You can still browse chats. To talk to the assistant, add `ANTHROPIC_API_KEY` in `.env`, or set `MODEL_PROVIDER=ollama` and use the model on this machine.” | Keep sidebar and history; disable Send; no stack traces. |
| `provider_down` | “Can’t reach Ollama on this machine (`qwen2.5:3b` at port 11434). Start Ollama on Windows, then retry.” | Retry; keep history visible. |
| `timeout` | Message-level: “The model timed out.” | Retry this turn. |
| `db_down` | Full-page-lite: “Cannot load chats (database).” | Retry load; composer disabled. |
| `empty_retrieval` | Handled as a **successful** abstain message, not a red error. | Suggest examples. |
| `unknown` | “Something went wrong.” | Retry; request id in details for logs. |

Failed assistant turns stay in the thread as an error card so the user can retry without losing the question.

## 4. Responsive behavior

- **≥ 1024px:** Sidebar + chat + optional artifact pane. Artifact open splits the main area; chat remains readable (~min 360px).
- **768–1023px:** Sidebar as overlay. Artifact becomes a **bottom sheet / full-width panel** with a back-to-chat control—do not squeeze iframe + composer into two unusable columns.
- **< 768px:** Single column. Header compresses to icon + provider chip. Sessions via a drawer. Artifact is a full-screen overlay. Composer stays above the mobile keyboard (`visualViewport` if needed).
- Touch: citation chips and skill buttons ≥ 44px height. Do not rely on hover for citations (use tap-to-expand).

## 5. Accessibility

- Semantic landmarks: `banner`, `navigation` (sessions), `main`, `form` for composer.
- Provider chip and health are text, not color-only (`Ollama · qwen2.5:3b · healthy`).
- Focus order: skip link → composer after load if empty, else session title then messages.
- Streaming: `aria-live="polite"` on the assistant region; avoid announcing every token.
- Iframe: `title="Generated artifact (untrusted)"`; parent instructions that content is untrusted.
- Keyboard: `Enter` send, `Shift+Enter` newline; `Esc` closes artifact overlay and sidebar drawer.
- Contrast: WCAG 2.2 AA for text and error banners. Reduced-motion: no streaming caret animation.
- Markdown in chat: headings in assistant output should not skip to `h1` of the app; render essay headings starting at `h2` inside the message article.

## 6. Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Visual tone | Neutral light UI, single accent (ink/blue), system-ui or a restrained sans | Take-home readability; not a Lenny brand clone. |
| Citations | Chips under the answer (guest · title), expand for date + YouTube | Scanable; matches “cite every answer.” |
| Skill entry | Visible toolbar, not slash-commands-only | Reviewers should find the essay without reading the PRD. |
| Artifact vs chat | Separate pane, not inline HTML | Security (iframe) and so a long essay/HTML does not bury the thread. |
| Markdown vs HTML | Markdown in chat; HTML only in iframe | Chat stays in-app styled; HTML cannot inherit cookies/DOM. |
| Provider control | Read-only chip with **provider + model** | Config-only toggle; missing Anthropic key uses a friendly banner, not a settings form. |
| Session titles | First 60 chars of first user message | Zero extra UI; editable later if time. |
| Examples on empty | Three corpus-grounded prompts | Teaches the product better than a blank box. |
| Local model framing | Chip label includes `qwen2.5:3b` | Sets quality expectations without a disclaimer modal. |

Out of scope for UI: dark mode (unless cheap via `prefers-color-scheme` later), onboarding carousel, episode browser, login, in-app provider switch, ingest progress UI.

This document is the UX contract for implementation; no application code lands in this phase.
