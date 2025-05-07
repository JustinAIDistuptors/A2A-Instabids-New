# InstaBids Frontend Build Plan
*(High‑level roadmap & phase checklist)*

## 📚 Contents
1. Architecture snapshot
2. Phase roadmap
3. Core UI deliverables per role
4. Tech stack recap
5. Milestone exit criteria
------------------------------------------------------------------------

## 1 Architecture snapshot
Backend → FastAPI + Supabase (Postgres 15, pgvector)  
Agents → Google A2A protocol (HomeownerAgent, ContractorAgent, MatchingAgent, MessagingAgent)  
MCP tools → Serena (code nav/edit), GitHub MCP, Supabase MCP, Context7 docs  
Auth & RBAC → Supabase Auth (JWT) with row‑level policies  
CI/CD → GitHub Actions

Frontend target stack  
| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework       | **Next.js 13 (App Router)** | SSR/SSG + RPC routes |
| Styling         | **Tailwind CSS** | utility‑first, matches Shadcn |
| UI components   | **Shadcn UI** (Radix primitives) | copy‑paste ownership, accessible |
| AI streaming    | **Vercel AI SDK** | `useChat`, SSE helpers |
| State mgmt      | *small* — React Context (+ Zustand if needed) | lightweight for first release |
| DB client       | **@supabase/supabase-js** | realtime tables + Auth |

## 2 Phase roadmap
| Phase | Goal | Key Issues/PRs | Exit Criteria |
|-------|------|---------------|---------------|
| P‑1   | 🏗 Project scaffold | `init-next-app`, Tailwind, Shadcn init | app boots locally |
| P‑2   | 💬 Core agent chat | AgentChat component w/ `useChat` stream | messages stream token‑by‑token |
| P‑3   | 📑 Role dashboards | Homeowner & Contractor layouts | auth redirect + dummy data |
| P‑4   | 🔔 Realtime bids / notif. | SSE or Supabase realtime tables | new bid toast appears live |
| P‑5   | 🧑‍💼 Admin console | admin view of agents / tasks | RLS enforced, queries succeed |
| P‑6   | 🚀 Prod deploy | Vercel preview <-> FastAPI | green CI, URLs shareable |

*(Add / remove phases as scope evolves.)*

## 3 Core UI deliverables per role
```txt
Homeowner
 ├─ Dashboard (active projects, status widgets)
 ├─ AgentChat (project Q&A)
 ├─ BidList (live BidCard stream)
 └─ Notifications tray

Contractor
 ├─ OpportunityFeed
 ├─ BidComposer (form + streaming price helper)
 └─ Awarded / History tabs

Admin
 ├─ Global Agent Monitor
 ├─ Users table
 ├─ Task audit log
 └─ System settings
