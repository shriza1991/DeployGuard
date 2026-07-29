# DeployGuard — Full Page Audit

> **Scope**: all 12 routed pages + sidebar navigation + 5 shared components.
> **Goal**: surface duplicated logic, orphaned files, mock data, and refactoring candidates.

---

## 1. Routing Map

| Route | Component File | Sidebar Label | Status |
|---|---|---|---|
| `/` | `Dashboard.tsx` | Dashboard | ✅ Active |
| `/deployments` | `Deployments.tsx` | Deployments | ✅ Active |
| `/deployments/:id` | `DeploymentDetails.tsx` | *(no sidebar link)* | ✅ Active |
| `/analytics` | `Analytics.tsx` | Analytics | ✅ Active |
| `/agents` | `Agents.tsx` | AI Agents | ✅ Active |
| `/incidents` | `Incidents.tsx` | Incidents | ✅ Active |
| `/system-health` | `SystemHealth.tsx` | System Health | ✅ Active |
| `/simulator` | `WebhookSimulator.tsx` | Simulator | ✅ Active |
| `/reports` | `Reports.tsx` | Reports | ✅ Active |
| `/settings` | `Settings.tsx` | Settings | ✅ Active |
| `/about` | `About.tsx` | *(no sidebar link)* | ⚠️ Hidden |
| `/search` | `SearchRepository.tsx` | Repo Search | ✅ Active |
| *(no route)* | `IncidentHistory.tsx` | *(no sidebar link)* | 🔴 Orphaned |

> **`IncidentHistory.tsx`** is never imported into `App.tsx`. It is a dead file. `Incidents.tsx` is the live route, but both files contain near-identical code (see §9).

---

## 2. Page-by-Page Feature Inventory

---

### `/` — Dashboard (`Dashboard.tsx`)
**Purpose**: Operational overview — "what is happening right now"

| Section | Widget | Data Source | Notes |
|---|---|---|---|
| Header | Title, system online badge, refresh chip, time selector (60m/24h/7d/30d) | `getAggregatorHealth` | Live |
| Executive Summary | 6 KPI cards: Deployments, Success Rate, Avg Risk, Blocked, Under Review, Avg Confidence | `getDeploymentMetrics` | Live |
| Latest Deployments | Deployment table (repo, decision, risk, confidence, branch, time) — max 6, last 60m | `listDeployments` | Live, 60m window |
| Repository Context | Repo name, indexed status, file count, LOC, frameworks, last indexed | `getRepositoryStatus/Manifest/Stats` | Live |
| Pipeline Health | 6 service rows: Kafka, Redis, Qdrant, Gateway, Aggregator, Agents + agent chips | `getAggregatorHealth` + `getAgentStatus` | Live |
| Recent Activity | Live event feed of deployment decisions (seeded + reactive) | Derived from `listDeployments` | Live |
| AI Agent Overview | Per-agent cards: analyses, latency, confidence, last run | `getAgentStatus` | Live |
| Quick Actions | 6 buttons: Run Simulation (→ `/simulator`), Query Repo (→ `/search`), Refresh (calls `.refetch()`), View All Deployments (→ `/deployments`), Open Analytics (→ `/analytics`), Export Snapshot (downloads `.txt`) | Mixed — nav + real action | ✅ Actions work |

**CSS file**: `Dashboard.css` (876 lines, the global design system for 9 pages)

---

### `/deployments` — Deployments (`Deployments.tsx`)
**Purpose**: Full deployment history with filtering and pagination

| Widget | Description | Data |
|---|---|---|
| Header | "Deployment Audits" title + Export JSON button | — |
| Filter bar | Search (by ID/repo), Repository text filter, Decision select (ALL/SAFE/REVIEW/BLOCK), Severity select, Branch select | Client-side filter on paginated backend data |
| Deployments table | Repo, Decision badge, Risk score badge, Confidence (via `ConfidenceDisplay`), Branch, Created Time, Copy ID button, Details button (→ `/deployments/:id`) | `listDeployments` |
| Pagination | Previous / Next, "Page N of M" counter | Backend paginated |
| Empty state | "No deployment analyses found" + Run Simulation button (→ `/simulator`) + Go to Dashboard button | — |
| Toast notification | Inline success toast for copy/export | Local state |

---

### `/deployments/:id` — Deployment Details (`DeploymentDetails.tsx`)
**Purpose**: Deep inspection of a single deployment decision

| Section | Content | Data |
|---|---|---|
| Back navigation | "← Back to Deployments" button | — |
| Decision banner | SAFE / BLOCK / REVIEW with risk score bar | `getDeployment` |
| Summary cards | Repository, Branch, Author, Commit SHA, Severity badge, Overall Confidence (`ConfidenceDisplay`) | `getDeployment` |
| AI Summary | Free-text AI narrative, if present | `getDeployment` |
| Agent results | Expandable card per agent (Code Risk, Infra Risk, Incident History): score, confidence, reasoning, similar incidents table | `getDeployment` |
| Audit timeline | Pipeline stage timestamps | `getDeployment` |
| Raw JSON viewer | Collapsible raw decision JSON | `getDeployment` |
| Actions | Copy Correlation ID, Export JSON | Local actions |

---

### `/analytics` — Analytics (`Analytics.tsx`)
**Purpose**: Historical trend analysis with charts and filtered drill-down

| Section | Content | Data |
|---|---|---|
| Header | "Security Analytics" title + time range selector (7d/14d/30d/90d) + search + severity filter dropdown + CSV export | Mixed |
| KPI summary row | Total scans, Safe %, Blocked %, Avg confidence | `getAnalyticsSummary` |
| Volume chart | Bar chart — daily deployment volume over time period | `getAnalyticsVolume` |
| Decision distribution | Pie chart — SAFE/REVIEW/BLOCK proportions | `getAnalyticsDecisions` |
| Area chart | Risk score trend over time | `getAnalyticsVolume` |
| Blocked deployments table | List of blocked events with severity, score, reasoning — clickable to expand | `getAnalyticsBlocks` |
| Block detail modal | Full detail panel for a selected block | Local state from table |
| Run new scan modal | "New Deployment Scan" form — repo, branch, commit, message — triggers webhook | `triggerDeployment` |

> **Note**: The "Run New Scan" modal in Analytics is essentially a stripped-down version of the Webhook Simulator page. This is **functional duplication**.

---

### `/agents` — AI Agents (`Agents.tsx`)
**Purpose**: Monitor individual AI agent workers

| Section | Content | Data |
|---|---|---|
| Header | "Distributed AI Agents" title | — |
| Fleet overview bar | Total Evaluations, Fleet Confidence Mean, Last Scan Run, Active Workers count | `listDeployments` + `getAgentStatus` |
| Agent cards (×3) | Per agent: name, region, status badge, 8 stat fields (last run, latency, analysis count, confidence, version, uptime, CPU, memory), console log terminal | `getAgentStatus` |

> **Mock data**: Console logs (`MOCK_AGENT_LOGS`) are hardcoded static strings — not fetched from any agent. They never update.

> **Duplication with Dashboard**: Both pages call `getAgentStatus` and `listDeployments` to display very similar per-agent stats (analyses, latency, confidence, last run). Dashboard's AI Agent Overview cards are a compact version of what Agents page renders in full.

---

### `/incidents` — Incidents (`Incidents.tsx`)
**Purpose**: Historical Incident Intelligence — browse incidents + semantic similarity search

| Section | Content | Data |
|---|---|---|
| Header | "Outages & Incidents Archive" | — |
| Left pane: Incident database | Search bar + scrollable incident card list (ID, severity badge, title, description, service, environment, expand for root cause/summary/resolution/rollback) | `listIncidents` → aggregator |
| Right pane: Similarity search | Textarea input + "Perform Intelligence Search" button + results list (incident ID, title, similarity score, root cause, RISK MATCH / Below Threshold verdict) | `searchSimilarIncidents` → aggregator → Qdrant |

---

### `/system-health` — System Health (`SystemHealth.tsx`)
**Purpose**: Service status overview for platform infrastructure

| Section | Content | Data |
|---|---|---|
| Header | "Infrastructure System Health" | — |
| Service cards (×5) | API Gateway, Aggregator Backend, Kafka, Redis, Qdrant — each shows: name, role, endpoint URI, latency, uptime, load | Partially live: Aggregator status from `getAggregatorHealth`; all others are **hardcoded static mock values** |
| Network Orchestration Map | Clusters count, Internal Ping, Tolerable Late Time | **Hardcoded static values** |

> **Mock data**: Latency (`14ms`, `8ms`, `2ms`, `35ms`), uptime percentages, CPU/RAM figures are all hardcoded constants. Only the Aggregator's `active/offline` status reflects real backend data.

---

### `/simulator` — Webhook Simulator (`WebhookSimulator.tsx`)
**Purpose**: Manually trigger a deployment risk scan

| Section | Content | Data |
|---|---|---|
| Header | "Deployment Webhook Simulator" | — |
| Preset buttons | Load Safe / Warning / Critical preset templates (pre-fills the form) | Local state |
| Form | Repository, Branch, Commit SHA, Author, PR Title, PR Description, Commit Message — "Send GitHub Webhook Push Event" submit button | `triggerDeployment` |
| Pipeline progress tracker | Appears after submit — shows stages: Webhook Ingress ✓, Gateway ✓, Kafka ✓, Code Risk Agent (live), Infra Agent (live), Incident Agent (live), Aggregator (live) | Polls `getDecision` every 2s, auto-navigates to `/deployments/:id` on completion |

---

### `/reports` — Reports (`Reports.tsx`)
**Purpose**: Generate and download report files

| Section | Content | Data |
|---|---|---|
| Header | "Compliance & Export Reports" | — |
| Report template cards (×3) | Executive DevSecOps Summary (CSV), Agent Reliability & Latency Audit (CSV), Complete Raw Pipeline Registry (JSON) — selectable | Static template definitions |
| Time range selector | 7d / 14d / 30d / 90d | Local state |
| Generate & Download button | Triggers backend export, downloads file | `exportAnalytics` |
| Last generated timestamp | Shows when last report was generated | Local state |
| Preview panel | Shows what the report will include (static descriptions) | Static |
| Toast notification | Success/failure after download | Local state |

---

### `/settings` — Settings (`Settings.tsx`)
**Purpose**: Configure risk thresholds and notifications

| Section | Content | Data |
|---|---|---|
| Header | "Settings & Policies" | — |
| Risk Thresholds | Block threshold slider (50–90), Review threshold slider (20–45), Agent timeout number input | Local state only |
| Notifications Routing | Slack toggle + webhook URL field (conditional), Email weekly reports toggle | Local state only |
| Preferences | Theme mode dropdown (3 options) | Local state only |
| Save button | Shows "Saving..." spinner, then success message after 1s timeout | **Fake — no API call** |

> **Not wired to backend**: All settings exist only in local React state. Nothing is persisted. The "Save" button is purely cosmetic.

---

### `/search` — Semantic Code Search (`SearchRepository.tsx`)
**Purpose**: Vector search over the indexed codebase

| Section | Content | Data |
|---|---|---|
| Header | "Semantic Code Search" | — |
| Search form | Text input + Search button | `searchRepository` → repository-context service |
| Error state | Displays error message if search fails (e.g., repo not indexed) | React Query error |
| Empty state | "No results found" message | — |
| Results (grouped by file) | File path header + per-chunk cards: file icon, chunk text, similarity score badge, copy button | `searchRepository` |

---

### `/about` — Architecture Documentation (`About.tsx`)
**Purpose**: Static documentation page

| Section | Content |
|---|---|
| Platform Concept | Text description of DeployGuard |
| Pipeline Workflow | ASCII diagram of the distributed pipeline |
| AI Agent Profiles | 3 agent descriptions (Code Risk, Infra Risk, Incident History) |
| Tech Stack | Redis, Qdrant, Kafka, Gemini API descriptions |

> **Not in sidebar navigation**. Only reachable if you know the `/about` URL.

---

## 3. Shared Components Audit

| Component | Used By | Purpose | Notes |
|---|---|---|---|
| `StatusBadge.tsx` | Dashboard, Deployments, Agents | Renders SAFE/BLOCK/REVIEW/PENDING/ONLINE/etc. badges | ✅ Well-used |
| `MetricCard.tsx` | Dashboard only | KPI card with title, value, subtitle, progress bar | ⚠️ Only used in 1 page — could be inlined |
| `HealthIndicator.tsx` | Dashboard only | Online/Offline/Degraded chip or badge | ⚠️ Only used in 1 page |
| `ConfidenceDisplay.tsx` | Deployments, DeploymentDetails | Rich confidence display with color, label, progress | ✅ Good extraction |
| `QuickActionCard.tsx` | *(no longer used)* | Was used by old Dashboard | 🔴 **Dead component** — removed from Dashboard, not used anywhere |
| `AgentStat.tsx` | Agents only | Key-value stat display for agent cards | ⚠️ Only used in 1 page — could be inlined |

---

## 4. CSS Architecture

| File | Owned By | Actually Imported By |
|---|---|---|
| `Dashboard.css` | Dashboard | Dashboard, Agents, WebhookSimulator, SystemHealth, Settings, SearchRepository, Reports, About (9 pages share it) |
| `Deployments.css` | Deployments | Deployments only |
| `Analytics.css` | Analytics | Analytics only |
| `IncidentHistory.css` | IncidentHistory | Incidents, IncidentHistory |

> `Dashboard.css` is the de-facto **global design system** — it contains design tokens, `glass-panel`, `btn-primary-stitch`, `btn-secondary-stitch`, `toast-notification`, `dashboard-container`, etc. This is fine but should be acknowledged and potentially renamed to `design-system.css` or extracted into a proper globals file.

---

## 5. Code Duplication Map

### A. `formatRelativeTime` — Duplicated in 2 files

| File | Line |
|---|---|
| `Dashboard.tsx` | L91 |
| `Agents.tsx` | L31 |

**Fix**: Extract to `src/utils/time.ts` and import in both.

---

### B. `Incidents.tsx` vs `IncidentHistory.tsx` — Near-identical pages

Both files:
- Import from `../api/incidents`
- Define identical `filteredIncidents` filter logic
- Render the same left pane incident list
- Render the same right pane similarity playground
- Share `IncidentHistory.css`

**`IncidentHistory.tsx` has one extra feature**: `expandedId` state for expanding incident cards (which was added during our earlier work). `Incidents.tsx` does **not** have this expand feature — it shows a simplified version.

The router uses `Incidents.tsx` (via `/incidents`). `IncidentHistory.tsx` is unreachable (never imported in `App.tsx`).

**Fix**: Delete `IncidentHistory.tsx`. Port its `expandedId` expand feature into `Incidents.tsx` if it hasn't been already — then `Incidents.tsx` becomes the canonical implementation.

---

### C. Agent Stats — Dashboard AI Agent Overview vs Agents page

Dashboard renders compact per-agent cards (analyses, latency, confidence, last run).  
Agents page renders the same 4 fields plus 4 more (version, uptime, CPU, memory) in full cards with mock console logs.

These are the same data from the same endpoint. There is no need for both; the Dashboard version is the summary, Agents is the detail view. This is **acceptable** — not a bug, just worth noting.

---

### D. "Run Simulation" button — In 3 places

| File | Purpose |
|---|---|
| `Dashboard.tsx` (empty state) | Secondary CTA when no recent deployments |
| `Dashboard.tsx` (Quick Actions) | Primary action button |
| `Deployments.tsx` (empty state) | CTA when deployment list is empty |

This is appropriate. Empty states should offer a way forward. Not a problem.

---

### E. Analytics "Run New Scan" modal — Duplicates Simulator

The Analytics page has a "New Deployment Scan" modal with a form (repo, branch, commit, message). This is functionally identical to `/simulator` but embedded in a modal. It calls the same `triggerDeployment` API.

**This is the most significant duplication**. If Analytics is for historical data, it shouldn't also be a scan launcher. The modal should be removed and replaced with a "→ Run Simulation" link to `/simulator`.

---

## 6. Mock / Fake Data Summary

| Page | What is Mocked | Impact |
|---|---|---|
| `Agents.tsx` | Console logs (`MOCK_AGENT_LOGS`) are static strings — never update | Users see fake terminal output on a "live monitoring" page |
| `SystemHealth.tsx` | All service metrics (latency, uptime, CPU, RAM, network ping) except Aggregator online/offline | Page looks live but is 90% hardcoded |
| `Settings.tsx` | Save button — no backend persistence | Settings appear to save but reset on reload |

---

## 7. Dead / Unreachable Code

| File | Problem |
|---|---|
| `IncidentHistory.tsx` | Never imported in `App.tsx`. Unreachable. Duplicates `Incidents.tsx`. **Delete it.** |
| `QuickActionCard.tsx` | No longer used anywhere after Dashboard refactor. **Delete it or keep for future use.** |
| `About.tsx` | Has no sidebar nav link. Reachable only by direct URL. Consider adding to sidebar or removing. |

---

## 8. Prioritized Refactoring Recommendations

| Priority | Item | Effort | Impact |
|---|---|---|---|
| 🔴 High | Delete `IncidentHistory.tsx` — it's a dead duplicate | Trivial | Removes confusion |
| 🔴 High | Remove "Run New Scan" modal from `Analytics.tsx` — replace with link to Simulator | Small | Eliminates functional duplication |
| 🟡 Medium | Extract `formatRelativeTime` to `src/utils/time.ts` | Trivial | DRY, single source of truth |
| 🟡 Medium | Delete `QuickActionCard.tsx` — it's unused | Trivial | Dead component |
| 🟡 Medium | Wire `Settings.tsx` to a real config API or add a clear "preview only" disclaimer | Medium | Removes deceptive UX |
| 🟡 Medium | Replace `SystemHealth.tsx` hardcoded metrics with real health endpoints (or add a disclaimer) | Medium | Removes misleading static data |
| 🟡 Medium | Replace `MOCK_AGENT_LOGS` in `Agents.tsx` with a real log stream or remove the terminal | Medium | Removes fake "live" output |
| 🟢 Low | Add `/about` to the sidebar under Configuration | Trivial | Makes the page discoverable |
| 🟢 Low | Rename `Dashboard.css` → `design-system.css` or create a proper `globals.css` | Small | Clarifies the CSS architecture |
| 🟢 Low | Delete `MetricCard.tsx`, `HealthIndicator.tsx`, `AgentStat.tsx` if they remain single-page use | Trivial | Simplify component tree |
