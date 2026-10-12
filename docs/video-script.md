# 2-3 Minute Demo Video Script — The Lenny Growth Assistant

> **Evaluation Criteria Addressed**: Problem framing, product walkthrough, live local Ollama demonstration, and discussion of one key technical trade-off. Camera ON required.

---

## ⏱️ Video Breakdown (Total Time: ~2:30)

| Timestamp | Section | Key Talking Points & Actions |
|---|---|---|
| **0:00 – 0:35** | **1. Problem & Customer Judgment** | The overwhelming volume of podcast content (300+ episodes); difficulty finding specific actionable growth playbooks; need for zero hallucinations. |
| **0:35 – 1:20** | **2. Live Local Ollama Demo** | Show the app running via Docker Compose (`http://localhost:5173`); show read-only provider badge (`Ollama qwen2.5:3b`); ask a growth question; show streaming, citations, and YouTube deep link. |
| **1:20 – 1:55** | **3. Skills & Artifacts (Ship 30 & Sandboxed HTML)** | Demonstrate Ship 30 for 30 essay skill; show side-by-side Claude-style Artifact viewer; show sandboxed HTML execution and explain security isolation. |
| **1:55 – 2:30** | **4. Technical Trade-off & Engineering Judgment** | Explain PostgreSQL Full-Text Search (weighted tsvector) vs Vector Embeddings; performance, latency (5.5ms), exact quote traceability, zero vector DB bloat. |

---

## 🎙️ Spoken Script

### [0:00 – 0:35] Problem & The Product
*(Camera on you, smiling, confident)*

> "Hi everyone, I'm presenting **The Lenny Growth Assistant** — a production-grade full-stack AI web app built on over 300 episodes of Lenny's Podcast.
> 
> Growth leaders, founders, and product managers love Lenny's podcast, but listening to hundreds of hours of interviews to find specific retention benchmarks or pricing strategies is impossible. Standard LLMs hallucinate generic advice. 
> 
> The Lenny Growth Assistant solves this by strictly grounding every response in verbatim podcast transcripts, complete with exact speaker citations and clickable YouTube timestamp deep links."

---

### [0:35 – 1:20] Live Product Walkthrough (Local Ollama)
*(Switch to screen share with camera bubble in corner)*

> "Let's see it in action. The entire stack runs with a single command via Docker Compose.
> 
> Notice the top-right badge: our app is running completely on **local Ollama** using `qwen2.5:3b` on my Windows laptop without needing an NVIDIA GPU or external API keys. It also supports Anthropic Claude without code changes.
> 
> Let's ask: *'How should startups think about pricing and packaging?'*
> 
> As you can see, tokens stream back immediately via Server-Sent Events. The assistant answers using insights directly from Madhavan Ramanujam and Patrick Campbell.
> 
> Notice these citations: `[S1]`, `[S2]`. If I click on citation `[S1]`, the Grounded Sources drawer opens, showing the exact transcript excerpt and a deep link that jumps straight to the exact second in the YouTube interview."

---

### [1:20 – 1:55] Ship 30 for 30 Skill & Sandboxed Artifacts
*(Show intent selector and side pane)*

> "We also built dedicated agentic skills into the backend:
> 
> First, the **Ship 30 for 30 Essay Skill**: encoded with clear hooks, narrative progression, headings, and bold takeaways.
> 
> When I ask for a Ship 30 essay on onboarding loops, the assistant generates the essay and automatically opens our Claude Artifacts-style side pane.
> 
> For interactive tools, like this HTML churn and growth calculator, the generated code runs inside a locked iframe sandbox with `sandbox=""` and a strict Content-Security-Policy header. Combined with server-side sanitization using Rust's `nh3`, untrusted HTML is completely isolated from accessing parent cookies, local storage, or network endpoints."

---

### [1:55 – 2:30] Key Technical Trade-off
*(Back to camera or architecture slide)*

> "Finally, let's talk about our biggest technical trade-off: **PostgreSQL Full-Text Search versus Vector DB Embeddings**.
> 
> We deliberately chose native PostgreSQL weighted full-text search (`tsvector`) over vector embeddings. 
> 
> Here's why: Vector models frequently suffer from semantic drift and hallucinated citations. By placing weighted search vectors directly on chunks with PostgreSQL GIN indexes, we achieved **5.5-millisecond query latency**, exact keyword and guest name precision, zero cold-start embedding generation overhead, and 100% deterministic citation traceability — all within the existing database without adding vector DB operational complexity.
> 
> All code, tests, and documentation are public on GitHub. Thank you!"

---

## 📋 Tips for Recording
1. **Camera position**: Position camera at eye level with decent lighting.
2. **Resolution**: Record at 1080p using OBS Studio or Windows Clipchamp / Loom.
3. **Audio**: Use headphones with microphone to prevent laptop fan noise.
4. **YouTube Settings**: Upload as "Unlisted" or "Public", title it *"The Lenny Growth Assistant Demo — [Your Name]"*, and paste the YouTube link into the submission form.
