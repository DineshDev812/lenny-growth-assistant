# Lenny Growth Assistant — Manual UI Test Plan

This document outlines the step-by-step manual test plan to verify all user flows, UI components, session isolation, streaming, citations, Ship 30 essays, and sandboxed artifact rendering for **The Lenny Growth Assistant**.

---

## 1. Prerequisites & Environment Check

1. **Host Ollama**: Ensure Ollama is running on your Windows host with model `qwen2.5:3b` pulled:
   ```cmd
   ollama list
   ```
2. **Docker Compose Stack**: Run from project root:
   ```cmd
   docker compose up -d
   ```
3. **Verify Containers**: Check that `web`, `backend`, and `postgres` are healthy:
   ```cmd
   docker compose ps
   ```
4. **Open Application**: Navigate to `http://localhost:5173` in Google Chrome or Microsoft Edge.

---

## 2. Test Cases

### Test Case 1: Header & Provider Status Badge
- **Goal**: Verify read-only provider configuration and health visibility.
- **Steps**:
  1. Observe the top-right corner of the application header.
  2. Verify the badge displays: `Ollama (Local) · qwen2.5:3b` with a green indicator dot.
  3. Hover over the badge to inspect the tooltip.
- **Expected Result**: Read-only badge is clearly visible. No user input or runtime dropdown allows changing the provider (strictly governed by `.env`).

---

### Test Case 2: Session Management & Anonymous Cookies
- **Goal**: Verify independent session contexts and session renaming.
- **Steps**:
  1. Click **"+ New Chat"** in the left sidebar.
  2. In your browser DevTools (Application > Cookies), verify that a signed `client_id` cookie is stored with `HttpOnly` and `SameSite=Lax`.
  3. Send a message: `"What is product-market fit?"`.
  4. Notice the sidebar updates the session title to match the question topic.
  5. Hover over the session in the sidebar and click the **Pencil (Rename)** icon.
  6. Change title to `"PMF Discussion"` and click the Checkmark.
  7. Click **"+ New Chat"** to open a second session.
  8. Ask: `"What is a good activation rate?"`.
  9. Click back to `"PMF Discussion"` in the sidebar.
- **Expected Result**: Each session maintains its own distinct message history without crosstalk. Renaming updates immediately in the UI.

---

### Test Case 3: Grounded Q&A Streaming & Citation Drawer
- **Goal**: Verify real-time token streaming, transcript citations, and YouTube deep links.
- **Steps**:
  1. In a chat session, ask:
     > `"How should startups approach pricing and packaging?"`
  2. Observe the response generation.
  3. Look for inline citation tags like `[S1]`, `[S2]`.
  4. Look for the citation chips at the bottom of the assistant message (e.g. `[S1] Madhavan Ramanujam`).
  5. Click on `[S1]`.
  6. The **Grounded Sources Drawer** modal should open.
  7. Verify:
     - Guest name and episode title are accurate.
     - Timestamp is displayed.
     - Verbatim excerpt from the transcript is shown in a quotation block.
     - A red button **"Watch on YouTube at mm:ss"** is displayed.
  8. Click the YouTube button and verify it opens YouTube in a new tab with the timestamp parameter (`&t=SECONDS`).
- **Expected Result**: Streaming is smooth. All factual claims cite specific transcript segments. Deep links accurately point to the spoken segment.

---

### Test Case 4: Ship 30 for 30 Essay Skill & Artifact Viewer
- **Goal**: Verify the Ship 30 for 30 essay skill prompt and the side-by-side artifact viewer.
- **Steps**:
  1. In the intent bar above the input, click **"Ship 30 Essay"**.
  2. Enter: `"Write a Ship 30 for 30 essay on onboarding retention loops"`.
  3. Click **Send**.
  4. Observe the assistant generating a structured essay following Ship 30 principles:
     - Clear hook and headline.
     - Clear narrative progression.
     - Actionable bullet points and bold takeaways.
     - Citations referencing Lenny's guests (e.g. Lauryn Isford, Elena Verna).
  5. When complete, notice the **Artifact Viewer** pane opens on the right side of the screen (Claude Artifacts style).
  6. Click the **"Preview"** tab to see formatted Markdown typography.
  7. Click the **"Source"** tab to see the raw Markdown text.
  8. Click the **Copy** icon and verify the essay is copied to your clipboard.
  9. Click the **"X"** button to close the artifact pane. Notice a **"View Artifact"** card remains inside the chat bubble to re-open it at any time.
- **Expected Result**: Essay adheres to Ship 30 framework, grounded in real episodes. Side-by-side artifact viewer provides clean reading and copying.

---

### Test Case 5: Interactive HTML Artifact & Sandbox Isolation
- **Goal**: Verify interactive HTML artifact generation and iframe security isolation.
- **Steps**:
  1. In the intent bar, select **"Interactive HTML"**.
  2. Enter: `"Build an interactive HTML unit economics and churn calculator tool"`.
  3. Click **Send**.
  4. The assistant generates complete HTML/CSS/JS code for the interactive calculator.
  5. The Artifact Viewer opens on the right side with **"Preview"** selected.
  6. Verify the security callout badge appears:
     > `Isolated Sandbox: Sanitized server-side with nh3 and isolated in a sandboxed iframe.`
  7. Interact with the calculator (adjust sliders or inputs) inside the preview pane.
  8. Inspect the DOM in DevTools: verify the iframe has `sandbox=""` and does **NOT** have `allow-same-origin`.
- **Expected Result**: Interactive widget runs smoothly inside the iframe. Iframe cannot access host cookies, parent DOM, or localStorage.

---

### Test Case 6: Out-of-Corpus Refusal (Strict Grounding)
- **Goal**: Verify that questions not covered by Lenny's podcast are cleanly refused without hallucination.
- **Steps**:
  1. Ask: `"What is the optimal aerodynamic wing design for a Boeing 777 aircraft?"`.
  2. Observe the assistant's reply.
  3. Ask: `"What is the traditional recipe for Neapolitan sourdough pizza dough?"`.
  4. Observe the assistant's reply.
- **Expected Result**: The assistant refuses cleanly with:
  > *"The transcripts I have don't support an answer to this. Try asking about a product, growth, or career topic covered on Lenny's Podcast."*
  No fake citations or hallucinations are generated.

---

### Test Case 7: Resiliency & Provider Offline Graceful Degradation
- **Goal**: Verify the system behaves gracefully when the LLM provider is offline.
- **Steps**:
  1. Open a command prompt and temporarily stop Ollama:
     ```cmd
     taskkill /F /IM ollama.exe
     ```
  2. Refresh `http://localhost:5173`.
  3. Observe the header badge: it transitions to **"Ollama (Local) · Host Unreachable"** with an amber/red dot.
  4. Check `http://localhost:8000/health`: status code is still `200 OK` (database is healthy, `provider_status: "unavailable"`).
  5. Send a chat message.
  6. The UI displays a friendly error banner explaining that Ollama is unreachable.
  7. Restart Ollama (`ollama serve`).
  8. Send the message again — generation resumes normally.
- **Expected Result**: System never crashes or presents 500 stack traces when the LLM host is down.
