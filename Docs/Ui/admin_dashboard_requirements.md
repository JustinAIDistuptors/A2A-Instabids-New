# Admin Dashboard – Functional Spec

## Goals
- View all active agents & their task queues  
- Inspect user base (homeowners, contractors, managers)  
- Monitor error logs & long‑running jobs  
- Trigger maintenance tasks (cache purge, vector re‑index)

## Key Screens
| Screen             | Core Data                                | Actions                |
|--------------------|------------------------------------------|------------------------|
| **Agents Overview** | agent id, type, owner, status, last ping | suspend, reactivate    |
| **Task Auditor**    | task id, state, agent, started, duration | force‑cancel           |
| **User Browser**    | user id, role, created, active projects  | impersonate, reset password |
| **System Health**   | queue depth, db connections, API latency | clear cache, restart worker |

## Tech Hooks
- Use Supabase RLS to allow only `role = admin`  
- Live updates via Supabase Realtime on `agent_status` table  
- Charts: `<BarChart>` with [Recharts] if needed  

## Acceptance Criteria
- 100 % of tasks visible, filterable, paginated  
- Live counter of agents online vs offline  
- Audit actions logged to `admin_actions` table  
- Responsive layout down to 768 px (mobile)
