"use client";

import {
  Activity,
  AlertTriangle,
  ArrowDownUp,
  BarChart3,
  Bot,
  CheckCircle2,
  ClipboardList,
  Download,
  FileQuestion,
  FileText,
  Filter,
  History,
  LayoutDashboard,
  ListChecks,
  Loader2,
  MessageSquare,
  RefreshCw,
  Save,
  Search,
  Send,
  ShieldCheck,
  Target,
  Trash2,
  Upload
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8010";

type User = {
  user_id: string;
  email: string;
  name: string;
};

type NextAction = {
  label: string;
  urgency: "high" | "medium" | "low" | "done";
  reason: string;
};

type ScreeningCheck = {
  label: string;
  status: "pass" | "watch" | "fail";
  detail: string;
};

type AnalysisSession = {
  id: string;
  candidate_name: string;
  job_title: string;
  resume_filename: string;
  score: number;
  priority_score: number;
  readiness_score: number;
  readiness_label: string;
  screening_checks: ScreeningCheck[];
  next_action: NextAction;
  matched_skills: string[];
  missing_skills: string[];
  pipeline_stage: string;
  reviewer_notes?: string;
  decision_memo?: {
    recommendation?: string;
    rationale?: string;
    conditions?: string[];
    generated_at?: string;
  };
  created_at: string;
  parsed_resume?: {
    personal_info?: Record<string, string | null>;
    skills?: string[];
    projects?: string[];
    education?: string[];
  };
  parsed_jd?: {
    title?: string;
    must_have_skills?: string[];
    nice_to_have_skills?: string[];
    responsibilities?: string[];
    seniority?: string;
  };
  match_result?: {
    score: number;
    fit_label: string;
    confidence?: number;
    explanation: string;
    matched_skills: string[];
    missing_skills: string[];
    score_breakdown?: Array<{ label: string; earned: number; max: number; detail: string }>;
    coverage?: { must_have?: number; nice_to_have?: number; responsibilities?: number };
    risk_flags?: Array<{ severity: "high" | "medium" | "low"; title: string; detail: string }>;
    evidence: Array<{ source: string; label: string; text: string }>;
  };
  interview_plan?: Record<string, string[]>;
  feedback_report?: {
    strengths: string[];
    weaknesses: string[];
    next_steps: string[];
    tailored_resume_bullets?: string[];
    outreach_message?: string;
    learning_plan?: Array<{ day: number; focus: string; output: string }>;
    role_fit_summary: string;
  };
};

type Answer = {
  answer: string;
  citations: Array<{ source: string; ordinal: number; text: string }>;
};

type DashboardMetrics = {
  total_sessions: number;
  average_score: number;
  strong_fit_count: number;
  ready_to_interview_count: number;
  open_action_count: number;
  needs_review_count: number;
  stage_counts: Record<string, number>;
  top_missing_skills: Array<{ skill: string; count: number }>;
  top_candidates: Array<{
    session_id: string;
    candidate_name: string;
    job_title: string;
    score: number;
    priority_score: number;
    readiness_score: number;
    pipeline_stage: string;
  }>;
  action_queue: Array<{
    session_id: string;
    candidate_name: string;
    job_title: string;
    priority_score: number;
    pipeline_stage: string;
    next_action: NextAction;
  }>;
  quality_watchlist: Array<{
    session_id: string;
    candidate_name: string;
    job_title: string;
    readiness_score: number;
    readiness_label: string;
    blocking_checks: ScreeningCheck[];
  }>;
  recent_risk_flags: Array<{ session_id: string; job_title: string; severity: "high" | "medium" | "low"; title: string; detail: string }>;
  product_health: Array<{ label: string; status: string; detail: string }>;
};

type ActivityEvent = {
  id: number;
  session_id: string;
  event_type: string;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

const pipelineStages = [
  { value: "new", label: "New" },
  { value: "review", label: "Review" },
  { value: "shortlisted", label: "Shortlisted" },
  { value: "interview", label: "Interview" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" }
];

const sampleJd = `Role: AI Application Engineer
Required skills: Python, FastAPI, React, SQL, RAG, vector search, REST APIs.
Preferred: PostgreSQL, Docker, testing.
Build, deploy, and maintain LLM-powered recruiter workflows with citations and feedback reports.`;

function cx(...classes: Array<string | false | undefined>) {
  return classes.filter(Boolean).join(" ");
}

function Pill({ children, tone = "default" }: { children: React.ReactNode; tone?: "default" | "good" | "gap" }) {
  return (
    <span
      className={cx(
        "inline-flex min-h-7 items-center rounded-md border px-2.5 text-sm",
        tone === "good" && "border-teal/25 bg-teal/10 text-teal",
        tone === "gap" && "border-berry/25 bg-berry/10 text-berry",
        tone === "default" && "border-line bg-white text-ink"
      )}
    >
      {children}
    </span>
  );
}

function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return <section className={cx("rounded-lg border border-line bg-white/90 shadow-soft", className)}>{children}</section>;
}

function riskClasses(severity: "high" | "medium" | "low") {
  if (severity === "high") return "border-berry/30 bg-berry/10 text-berry";
  if (severity === "medium") return "border-gold/35 bg-gold/10 text-gold";
  return "border-teal/25 bg-teal/10 text-teal";
}

function urgencyClasses(urgency: NextAction["urgency"]) {
  if (urgency === "high") return "border-berry/30 bg-berry/10 text-berry";
  if (urgency === "medium") return "border-gold/35 bg-gold/10 text-gold";
  if (urgency === "done") return "border-teal/25 bg-teal/10 text-teal";
  return "border-line bg-paper/70 text-ink";
}

function checkClasses(status: ScreeningCheck["status"]) {
  if (status === "pass") return "border-teal/25 bg-teal/10 text-teal";
  if (status === "watch") return "border-gold/35 bg-gold/10 text-gold";
  return "border-berry/30 bg-berry/10 text-berry";
}

function readinessText(value: string) {
  return value.replaceAll("_", " ");
}

function stageLabel(value: string) {
  return pipelineStages.find((stage) => stage.value === value)?.label ?? value;
}

function eventLabel(value: string) {
  return value.replaceAll("_", " ");
}

function timeValue(value: string) {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatDateTime(value: string) {
  const parsed = timeValue(value);
  if (!parsed) return "";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(parsed));
}

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [sessions, setSessions] = useState<AnalysisSession[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [active, setActive] = useState<AnalysisSession | null>(null);
  const [activityEvents, setActivityEvents] = useState<ActivityEvent[]>([]);
  const [resume, setResume] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState(sampleJd);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [stageDraft, setStageDraft] = useState("new");
  const [notesDraft, setNotesDraft] = useState("");
  const [stageFilter, setStageFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortMode, setSortMode] = useState<"priority" | "score" | "newest">("priority");
  const [busy, setBusy] = useState(false);
  const [asking, setAsking] = useState(false);
  const [savingWorkflow, setSavingWorkflow] = useState(false);
  const [status, setStatus] = useState("Connecting");

  const scoreTone = useMemo(() => {
    const score = active?.score ?? 0;
    if (score >= 75) return "text-teal";
    if (score >= 55) return "text-gold";
    return "text-berry";
  }, [active]);

  const filteredSessions = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return [...sessions]
      .filter((session) => stageFilter === "all" || session.pipeline_stage === stageFilter)
      .filter((session) => {
        if (!query) return true;
        return [session.candidate_name, session.job_title, session.resume_filename].join(" ").toLowerCase().includes(query);
      })
      .sort((a, b) => {
        const newest = timeValue(b.created_at) - timeValue(a.created_at);
        if (sortMode === "score") return b.score - a.score || b.priority_score - a.priority_score || newest;
        if (sortMode === "newest") return newest;
        return b.priority_score - a.priority_score || b.score - a.score || newest;
      });
  }, [sessions, searchQuery, sortMode, stageFilter]);

  async function loadSessions(userId: string) {
    const response = await fetch(`${API_BASE}/api/sessions?user_id=${userId}`);
    if (!response.ok) throw new Error("Could not load sessions");
    const data: AnalysisSession[] = await response.json();
    setSessions(data);
    if (!active && data[0]) {
      await loadSession(data[0].id);
    }
  }

  async function loadDashboard(userId: string) {
    const response = await fetch(`${API_BASE}/api/dashboard?user_id=${userId}`);
    if (!response.ok) throw new Error("Could not load dashboard");
    const data: DashboardMetrics = await response.json();
    setMetrics(data);
  }

  async function loadActivity(id: string) {
    const response = await fetch(`${API_BASE}/api/sessions/${id}/activity`);
    if (!response.ok) throw new Error("Could not load activity");
    const data: ActivityEvent[] = await response.json();
    setActivityEvents(data);
  }

  async function loadSession(id: string) {
    const response = await fetch(`${API_BASE}/api/sessions/${id}`);
    if (!response.ok) throw new Error("Could not load session");
    const data: AnalysisSession = await response.json();
    setActive(data);
    setStageDraft(data.pipeline_stage);
    setNotesDraft(data.reviewer_notes ?? "");
    setAnswer(null);
    await loadActivity(id);
  }

  useEffect(() => {
    async function boot() {
      try {
        const response = await fetch(`${API_BASE}/api/auth/demo-login`, { method: "POST" });
        if (!response.ok) throw new Error("Backend is unavailable");
        const data: User = await response.json();
        setUser(data);
        setStatus("Ready");
        await loadSessions(data.user_id);
        await loadDashboard(data.user_id);
      } catch (error) {
        setStatus(error instanceof Error ? error.message : "Backend is unavailable");
      }
    }
    boot();
  }, []);

  async function submitAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!resume || !user) return;

    const formData = new FormData();
    formData.append("resume", resume);
    formData.append("job_description", jobDescription);
    formData.append("user_id", user.user_id);

    setBusy(true);
    setStatus("Analyzing");
    try {
      const response = await fetch(`${API_BASE}/api/sessions/analyze`, {
        method: "POST",
        body: formData
      });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail ?? "Analysis failed");
      }
      const data: AnalysisSession = await response.json();
      setActive(data);
      setStageDraft(data.pipeline_stage);
      setNotesDraft(data.reviewer_notes ?? "");
      setSessions((current) => [data, ...current.filter((item) => item.id !== data.id)]);
      await loadActivity(data.id);
      await loadDashboard(user.user_id);
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }

  async function askActiveQuestion(value: string) {
    if (!active || !value.trim()) return;
    setQuestion(value);
    setAsking(true);
    try {
      const response = await fetch(`${API_BASE}/api/sessions/${active.id}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: value })
      });
      if (!response.ok) throw new Error("Question failed");
      const data: Answer = await response.json();
      setAnswer(data);
    } finally {
      setAsking(false);
    }
  }

  async function askQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await askActiveQuestion(question);
  }

  async function deleteSession(id: string) {
    const response = await fetch(`${API_BASE}/api/sessions/${id}`, { method: "DELETE" });
    if (!response.ok) return;
    setSessions((current) => current.filter((item) => item.id !== id));
    if (user) await loadDashboard(user.user_id);
    if (active?.id === id) {
      setActive(null);
      setAnswer(null);
      setActivityEvents([]);
    }
  }

  async function saveWorkflow() {
    if (!active || !user) return;
    setSavingWorkflow(true);
    try {
      const response = await fetch(`${API_BASE}/api/sessions/${active.id}/workflow`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pipeline_stage: stageDraft, reviewer_notes: notesDraft })
      });
      if (!response.ok) throw new Error("Could not save workflow");
      const data: AnalysisSession = await response.json();
      setActive(data);
      setStageDraft(data.pipeline_stage);
      setNotesDraft(data.reviewer_notes ?? "");
      setSessions((current) => current.map((item) => (item.id === data.id ? data : item)));
      await loadActivity(data.id);
      await loadDashboard(user.user_id);
    } finally {
      setSavingWorkflow(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[1500px] flex-col gap-4 px-4 py-4 lg:px-6">
      <header className="flex flex-col gap-3 border-b border-line pb-4 md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid size-11 shrink-0 place-items-center rounded-lg bg-ink text-white">
            <Bot size={24} aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-2xl font-semibold tracking-normal">AI Recruiter Interview Assistant</h1>
            <p className="truncate text-sm text-ink/65">{user ? `${user.name} | ${user.email}` : status}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Pill>
            <ShieldCheck className="mr-2" size={16} aria-hidden="true" />
            {status}
          </Pill>
          <button
            className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium hover:bg-paper"
            onClick={async () => {
              if (!user) return;
              await loadSessions(user.user_id);
              await loadDashboard(user.user_id);
              if (active) await loadActivity(active.id);
            }}
            title="Refresh sessions"
          >
            <RefreshCw size={16} aria-hidden="true" />
            Refresh
          </button>
        </div>
      </header>

      {metrics && (
        <Panel className="p-4">
          <div className="mb-3 flex items-center gap-2">
            <LayoutDashboard size={18} aria-hidden="true" />
            <h2 className="text-base font-semibold">Workspace Command Center</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <div className="rounded-md border border-line bg-paper/70 p-3">
              <div className="text-xs font-semibold uppercase text-ink/55">Analyses</div>
              <div className="text-2xl font-semibold">{metrics.total_sessions}</div>
            </div>
            <div className="rounded-md border border-line bg-paper/70 p-3">
              <div className="text-xs font-semibold uppercase text-ink/55">Avg Score</div>
              <div className="text-2xl font-semibold">{metrics.average_score}%</div>
            </div>
            <div className="rounded-md border border-line bg-paper/70 p-3">
              <div className="text-xs font-semibold uppercase text-ink/55">Strong Fits</div>
              <div className="text-2xl font-semibold text-teal">{metrics.strong_fit_count}</div>
            </div>
            <div className="rounded-md border border-line bg-paper/70 p-3">
              <div className="text-xs font-semibold uppercase text-ink/55">Ready Now</div>
              <div className="text-2xl font-semibold text-teal">{metrics.ready_to_interview_count}</div>
            </div>
            <div className="rounded-md border border-line bg-paper/70 p-3">
              <div className="text-xs font-semibold uppercase text-ink/55">Open Actions</div>
              <div className="text-2xl font-semibold text-berry">{metrics.open_action_count}</div>
            </div>
            <div className="rounded-md border border-line bg-paper/70 p-3">
              <div className="text-xs font-semibold uppercase text-ink/55">Needs Review</div>
              <div className="text-2xl font-semibold text-gold">{metrics.needs_review_count}</div>
            </div>
          </div>
          <div className="mt-3 rounded-md border border-line p-3">
            <div className="mb-2 flex items-center gap-2">
              <ListChecks size={16} aria-hidden="true" />
              <h3 className="text-sm font-semibold">Action Queue</h3>
            </div>
            <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {metrics.action_queue.length ? (
                metrics.action_queue.map((item) => (
                  <button
                    key={item.session_id}
                    className="grid gap-2 rounded-md border border-line bg-paper/70 p-3 text-left text-sm hover:bg-white"
                    onClick={() => loadSession(item.session_id)}
                  >
                    <span className="flex items-start justify-between gap-3">
                      <span className="min-w-0">
                        <span className="block truncate font-semibold">{item.candidate_name}</span>
                        <span className="block truncate text-xs text-ink/60">
                          {stageLabel(item.pipeline_stage)} | Priority {item.priority_score}
                        </span>
                      </span>
                      <span className={cx("shrink-0 rounded-md border px-2 py-1 text-xs font-semibold capitalize", urgencyClasses(item.next_action.urgency))}>
                        {item.next_action.urgency}
                      </span>
                    </span>
                    <span className="font-medium">{item.next_action.label}</span>
                    <span className="line-clamp-2 text-xs leading-5 text-ink/65">{item.next_action.reason}</span>
                  </button>
                ))
              ) : (
                <p className="text-sm text-ink/60">No open actions.</p>
              )}
            </div>
          </div>
          <div className="mt-3 rounded-md border border-line p-3">
            <div className="mb-2 flex items-center gap-2">
              <ShieldCheck size={16} aria-hidden="true" />
              <h3 className="text-sm font-semibold">Quality Watchlist</h3>
            </div>
            <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {metrics.quality_watchlist.length ? (
                metrics.quality_watchlist.map((item) => (
                  <button
                    key={item.session_id}
                    className="grid gap-2 rounded-md border border-line bg-paper/70 p-3 text-left text-sm hover:bg-white"
                    onClick={() => loadSession(item.session_id)}
                  >
                    <span className="flex items-start justify-between gap-3">
                      <span className="min-w-0">
                        <span className="block truncate font-semibold">{item.candidate_name}</span>
                        <span className="block truncate text-xs text-ink/60">{item.job_title}</span>
                      </span>
                      <span className="shrink-0 rounded-md border border-gold/35 bg-gold/10 px-2 py-1 text-xs font-semibold text-gold">
                        {item.readiness_score}
                      </span>
                    </span>
                    <span className="capitalize text-xs font-semibold text-ink/60">{readinessText(item.readiness_label)}</span>
                    <span className="grid gap-1">
                      {item.blocking_checks.slice(0, 2).map((check) => (
                        <span key={check.label} className="truncate text-xs text-ink/65">
                          {check.label}: {check.status}
                        </span>
                      ))}
                    </span>
                  </button>
                ))
              ) : (
                <p className="text-sm text-ink/60">No quality blockers.</p>
              )}
            </div>
          </div>
          <div className="mt-3 grid gap-3 lg:grid-cols-4">
            <div className="rounded-md border border-line p-3">
              <h3 className="mb-2 text-sm font-semibold">Pipeline</h3>
              <div className="flex flex-wrap gap-2">
                {pipelineStages.map((stage) => (
                  <Pill key={stage.value}>
                    {stage.label}: {metrics.stage_counts[stage.value] ?? 0}
                  </Pill>
                ))}
              </div>
            </div>
            <div className="rounded-md border border-line p-3">
              <h3 className="mb-2 text-sm font-semibold">Top Candidates</h3>
              <div className="grid gap-2">
                {metrics.top_candidates.length ? (
                  metrics.top_candidates.map((item) => (
                    <button
                      key={item.session_id}
                      className="grid grid-cols-[1fr_auto] gap-2 rounded-md border border-line bg-paper/70 p-2 text-left text-sm hover:bg-white"
                      onClick={() => loadSession(item.session_id)}
                    >
                      <span className="min-w-0">
                        <span className="block truncate font-semibold">{item.candidate_name}</span>
                        <span className="block truncate text-xs text-ink/60">{item.job_title}</span>
                      </span>
                      <span className="text-right">
                        <span className="block font-semibold text-teal">{item.priority_score}</span>
                        <span className="block text-xs text-ink/60">{item.score}%</span>
                      </span>
                    </button>
                  ))
                ) : (
                  <Pill>No candidates yet</Pill>
                )}
              </div>
            </div>
            <div className="rounded-md border border-line p-3">
              <h3 className="mb-2 text-sm font-semibold">Top Gaps</h3>
              <div className="flex flex-wrap gap-2">
                {metrics.top_missing_skills.length ? (
                  metrics.top_missing_skills.map((item) => (
                    <Pill key={item.skill} tone="gap">
                      {item.skill} x{item.count}
                    </Pill>
                  ))
                ) : (
                  <Pill>No repeated gaps</Pill>
                )}
              </div>
            </div>
            <div className="rounded-md border border-line p-3">
              <h3 className="mb-2 text-sm font-semibold">Product Health</h3>
              <div className="grid gap-2">
                {metrics.product_health.slice(0, 4).map((item) => (
                  <div key={item.label} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className="mt-0.5 shrink-0 text-teal" size={16} aria-hidden="true" />
                    <span>
                      <span className="font-semibold">{item.label}:</span> {item.detail}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Panel>
      )}

      <div className="grid flex-1 gap-4 xl:grid-cols-[390px_minmax(0,1fr)]">
        <aside className="flex min-w-0 flex-col gap-4">
          <Panel>
            <form className="flex flex-col gap-4 p-4" onSubmit={submitAnalysis}>
              <div className="flex items-center gap-2">
                <Upload size={18} aria-hidden="true" />
                <h2 className="text-base font-semibold">New Analysis</h2>
              </div>
              <label className="flex min-h-28 cursor-pointer flex-col items-center justify-center rounded-md border border-dashed border-line bg-paper/70 px-4 text-center text-sm hover:bg-white">
                <FileText className="mb-2 text-teal" size={24} aria-hidden="true" />
                <span className="font-medium">{resume ? resume.name : "Choose resume PDF or TXT"}</span>
                <input
                  className="sr-only"
                  type="file"
                  accept=".pdf,.txt"
                  onChange={(event) => setResume(event.target.files?.[0] ?? null)}
                />
              </label>
              <textarea
                className="min-h-52 resize-y rounded-md border border-line bg-white p-3 text-sm leading-6"
                value={jobDescription}
                onChange={(event) => setJobDescription(event.target.value)}
                aria-label="Job description"
              />
              <button
                className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-teal px-4 text-sm font-semibold text-white hover:bg-teal/90 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={!resume || !jobDescription.trim() || busy}
              >
                {busy ? <Loader2 className="animate-spin" size={18} aria-hidden="true" /> : <BarChart3 size={18} aria-hidden="true" />}
                Analyze Fit
              </button>
            </form>
          </Panel>

          <Panel className="min-h-64">
            <div className="flex items-center gap-2 border-b border-line p-4">
              <History size={18} aria-hidden="true" />
              <h2 className="text-base font-semibold">History</h2>
            </div>
            <div className="grid gap-2 border-b border-line p-3">
              <label className="relative">
                <span className="sr-only">Search candidates</span>
                <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink/45" size={16} aria-hidden="true" />
                <input
                  className="h-10 w-full rounded-md border border-line bg-white pl-9 pr-3 text-sm"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Search candidate, role, resume"
                />
              </label>
              <div className="grid grid-cols-2 gap-2">
                <label className="relative">
                  <span className="sr-only">Filter by stage</span>
                  <Filter className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink/45" size={15} aria-hidden="true" />
                  <select
                    className="h-10 w-full rounded-md border border-line bg-white pl-9 pr-3 text-sm"
                    value={stageFilter}
                    onChange={(event) => setStageFilter(event.target.value)}
                  >
                    <option value="all">All stages</option>
                    {pipelineStages.map((stage) => (
                      <option key={stage.value} value={stage.value}>
                        {stage.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="relative">
                  <span className="sr-only">Sort sessions</span>
                  <ArrowDownUp className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink/45" size={15} aria-hidden="true" />
                  <select
                    className="h-10 w-full rounded-md border border-line bg-white pl-9 pr-3 text-sm"
                    value={sortMode}
                    onChange={(event) => setSortMode(event.target.value as "priority" | "score" | "newest")}
                  >
                    <option value="priority">Priority</option>
                    <option value="score">Score</option>
                    <option value="newest">Newest</option>
                  </select>
                </label>
              </div>
            </div>
            <div className="flex max-h-[430px] flex-col overflow-auto p-2">
              {sessions.length === 0 && <p className="p-3 text-sm text-ink/60">No saved sessions.</p>}
              {sessions.length > 0 && filteredSessions.length === 0 && <p className="p-3 text-sm text-ink/60">No sessions match the filters.</p>}
              {filteredSessions.map((session) => (
                <button
                  key={session.id}
                  className={cx(
                    "grid grid-cols-[1fr_auto] gap-3 rounded-md border p-3 text-left hover:bg-paper",
                    active?.id === session.id ? "border-teal bg-teal/10" : "border-transparent"
                  )}
                  onClick={() => loadSession(session.id)}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold">{session.candidate_name}</span>
                    <span className="block truncate text-xs text-ink/60">
                      {session.job_title} | {stageLabel(session.pipeline_stage)}
                    </span>
                  </span>
                  <span className="min-w-14 text-right">
                    <span className="block text-sm font-semibold text-teal">{session.priority_score}</span>
                    <span className="block text-xs text-ink/60">{session.score}%</span>
                  </span>
                </button>
              ))}
            </div>
          </Panel>
        </aside>

        <section className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
          <div className="flex min-w-0 flex-col gap-4">
            <Panel className="min-h-64 p-5">
              {active ? (
                <div className="flex flex-col gap-5">
                  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink/60">
                        {active.candidate_name} | {active.resume_filename}
                      </p>
                      <h2 className="break-words text-2xl font-semibold">{active.job_title}</h2>
                      <p className="mt-2 text-sm leading-6 text-ink/70">{active.match_result?.explanation}</p>
                    </div>
                    <div className="grid h-28 w-28 shrink-0 place-items-center rounded-lg border border-line bg-paper">
                      <div className="text-center">
                        <div className={cx("text-4xl font-bold", scoreTone)}>{active.score}%</div>
                        <div className="text-xs text-ink/60">{active.match_result?.fit_label}</div>
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <h3 className="mb-2 text-sm font-semibold">Matched Skills</h3>
                      <div className="flex flex-wrap gap-2">
                        {(active.match_result?.matched_skills ?? []).map((skill) => (
                          <Pill key={skill} tone="good">
                            {skill}
                          </Pill>
                        ))}
                      </div>
                    </div>
                    <div>
                      <h3 className="mb-2 text-sm font-semibold">Missing Skills</h3>
                      <div className="flex flex-wrap gap-2">
                        {(active.match_result?.missing_skills ?? []).map((skill) => (
                          <Pill key={skill} tone="gap">
                            {skill}
                          </Pill>
                        ))}
                        {active.match_result?.missing_skills?.length === 0 && <Pill>No major gaps</Pill>}
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                    <div className="rounded-md border border-line bg-paper/70 p-3">
                      <div className="mb-1 text-xs font-semibold uppercase text-ink/55">Priority</div>
                      <div className="text-2xl font-semibold text-teal">{active.priority_score}</div>
                    </div>
                    <div className="rounded-md border border-line bg-paper/70 p-3">
                      <div className="mb-1 text-xs font-semibold uppercase text-ink/55">Readiness</div>
                      <div className="text-2xl font-semibold text-teal">{active.readiness_score}</div>
                      <div className="text-xs capitalize text-ink/60">{readinessText(active.readiness_label)}</div>
                    </div>
                    <div className="rounded-md border border-line bg-paper/70 p-3">
                      <div className="mb-1 text-xs font-semibold uppercase text-ink/55">Confidence</div>
                      <div className="text-2xl font-semibold">{active.match_result?.confidence ?? 0}%</div>
                    </div>
                    <div className="rounded-md border border-line bg-paper/70 p-3">
                      <div className="mb-1 text-xs font-semibold uppercase text-ink/55">Must-Have</div>
                      <div className="text-2xl font-semibold">{active.match_result?.coverage?.must_have ?? 0}%</div>
                    </div>
                    <div className="rounded-md border border-line bg-paper/70 p-3">
                      <div className="mb-1 text-xs font-semibold uppercase text-ink/55">Responsibilities</div>
                      <div className="text-2xl font-semibold">{active.match_result?.coverage?.responsibilities ?? 0}%</div>
                    </div>
                  </div>

                  <div className={cx("rounded-md border p-3", urgencyClasses(active.next_action.urgency))}>
                    <div className="mb-1 flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2 font-semibold">
                        <ListChecks size={16} aria-hidden="true" />
                        Next Action
                      </div>
                      <span className="shrink-0 text-xs font-semibold uppercase">{active.next_action.urgency}</span>
                    </div>
                    <div className="font-semibold">{active.next_action.label}</div>
                    <p className="mt-1 text-sm leading-6">{active.next_action.reason}</p>
                  </div>

                  <div>
                    <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
                      <ShieldCheck size={16} aria-hidden="true" />
                      Screening Checklist
                    </h3>
                    <div className="grid gap-2 md:grid-cols-2">
                      {active.screening_checks.map((check) => (
                        <div key={check.label} className={cx("rounded-md border p-3 text-sm", checkClasses(check.status))}>
                          <div className="mb-1 flex items-center justify-between gap-3">
                            <span className="font-semibold">{check.label}</span>
                            <span className="shrink-0 text-xs font-semibold uppercase">{check.status}</span>
                          </div>
                          <p className="leading-6">{check.detail}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
                      <Target size={16} aria-hidden="true" />
                      Score Breakdown
                    </h3>
                    <div className="grid gap-3">
                      {(active.match_result?.score_breakdown ?? []).map((item) => (
                        <div key={item.label} className="rounded-md border border-line bg-paper/70 p-3">
                          <div className="mb-2 flex items-center justify-between gap-3 text-sm">
                            <span className="font-semibold">{item.label}</span>
                            <span className="shrink-0 text-ink/65">
                              {item.earned}/{item.max}
                            </span>
                          </div>
                          <div className="h-2 overflow-hidden rounded-full bg-line">
                            <div className="h-full rounded-full bg-teal" style={{ width: `${Math.min(100, (item.earned / item.max) * 100)}%` }} />
                          </div>
                          <p className="mt-2 text-xs leading-5 text-ink/65">{item.detail}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="mb-2 text-sm font-semibold">Grounded Evidence</h3>
                    <div className="grid gap-3">
                      {(active.match_result?.evidence ?? []).slice(0, 5).map((item, index) => (
                        <div key={`${item.label}-${index}`} className="rounded-md border border-line bg-paper/70 p-3">
                          <div className="mb-1 text-xs font-semibold uppercase text-ink/55">{item.label}</div>
                          <p className="text-sm leading-6">{item.text}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
                      <AlertTriangle size={16} aria-hidden="true" />
                      Risk Flags
                    </h3>
                    <div className="grid gap-2">
                      {(active.match_result?.risk_flags ?? []).map((item) => (
                        <div key={`${item.severity}-${item.title}`} className={cx("rounded-md border p-3 text-sm leading-6", riskClasses(item.severity))}>
                          <div className="font-semibold">{item.title}</div>
                          <div>{item.detail}</div>
                        </div>
                      ))}
                      {(active.match_result?.risk_flags ?? []).length === 0 && (
                        <div className="rounded-md border border-teal/25 bg-teal/10 p-3 text-sm text-teal">No major risk flags detected.</div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="grid min-h-56 place-items-center text-center text-ink/60">
                  <div>
                    <FileQuestion className="mx-auto mb-3 text-teal" size={34} aria-hidden="true" />
                    <p className="text-sm">Upload a resume and job description.</p>
                  </div>
                </div>
              )}
            </Panel>

            <Panel className="p-5">
              <div className="mb-4 flex items-center gap-2">
                <MessageSquare size={18} aria-hidden="true" />
                <h2 className="text-base font-semibold">Profile Q&A</h2>
              </div>
              <form className="flex flex-col gap-3 md:flex-row" onSubmit={askQuestion}>
                <input
                  className="h-11 min-w-0 flex-1 rounded-md border border-line bg-white px-3 text-sm"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Ask about candidate fit, RAG experience, or gaps"
                  disabled={!active}
                />
                <button
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-ink px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={!active || !question.trim() || asking}
                >
                  {asking ? <Loader2 className="animate-spin" size={18} aria-hidden="true" /> : <MessageSquare size={18} aria-hidden="true" />}
                  Ask
                </button>
              </form>
              <div className="mt-3 flex flex-wrap gap-2">
                {["What are the missing gaps?", "What is the match score?", "Give resume bullet rewrites"].map((item) => (
                  <button
                    key={item}
                    className="inline-flex min-h-9 items-center rounded-md border border-line bg-white px-3 text-sm hover:bg-paper disabled:opacity-60"
                    disabled={!active || asking}
                    onClick={() => askActiveQuestion(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
              {answer && (
                <div className="mt-4 grid gap-3">
                  <p className="rounded-md border border-line bg-paper/80 p-3 text-sm leading-6">{answer.answer}</p>
                  {answer.citations.map((citation) => (
                    <div key={`${citation.source}-${citation.ordinal}`} className="rounded-md border border-line p-3 text-sm">
                      <div className="mb-1 text-xs font-semibold uppercase text-ink/55">
                        {citation.source} chunk {citation.ordinal}
                      </div>
                      <p className="leading-6">{citation.text}</p>
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </div>

          <div className="flex min-w-0 flex-col gap-4">
            {active && (
              <Panel className="p-5">
                <div className="mb-4 flex items-center gap-2">
                  <ClipboardList size={18} aria-hidden="true" />
                  <h2 className="text-base font-semibold">Recruiter Workflow</h2>
                </div>
                <div className="grid gap-3">
                  <label className="grid gap-1 text-sm font-medium">
                    Pipeline Stage
                    <select
                      className="h-11 rounded-md border border-line bg-white px-3 text-sm"
                      value={stageDraft}
                      onChange={(event) => setStageDraft(event.target.value)}
                    >
                      {pipelineStages.map((stage) => (
                        <option key={stage.value} value={stage.value}>
                          {stage.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="grid gap-1 text-sm font-medium">
                    Reviewer Notes
                    <textarea
                      className="min-h-28 resize-y rounded-md border border-line bg-white p-3 text-sm leading-6"
                      value={notesDraft}
                      onChange={(event) => setNotesDraft(event.target.value)}
                      placeholder="Capture recruiter observations, interview conditions, or follow-up checks"
                    />
                  </label>
                  <button
                    className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-teal px-3 text-sm font-semibold text-white hover:bg-teal/90 disabled:opacity-60"
                    onClick={saveWorkflow}
                    disabled={savingWorkflow}
                  >
                    {savingWorkflow ? <Loader2 className="animate-spin" size={16} aria-hidden="true" /> : <Save size={16} aria-hidden="true" />}
                    Save Workflow
                  </button>
                </div>
              </Panel>
            )}

            {active?.decision_memo && (
              <Panel className="p-5">
                <div className="mb-4 flex items-center gap-2">
                  <Target size={18} aria-hidden="true" />
                  <h2 className="text-base font-semibold">Decision Memo</h2>
                </div>
                <div className="grid gap-3 text-sm leading-6">
                  <div className="rounded-md border border-line bg-paper/70 p-3">
                    <div className="text-xs font-semibold uppercase text-ink/55">Recommendation</div>
                    <div className="font-semibold">{active.decision_memo.recommendation?.replaceAll("_", " ")}</div>
                  </div>
                  <p className="rounded-md border border-line p-3">{active.decision_memo.rationale}</p>
                  <div>
                    <h3 className="font-semibold">Conditions</h3>
                    <ul className="mt-2 grid gap-2">
                      {(active.decision_memo.conditions ?? []).map((item) => (
                        <li key={item} className="rounded-md border border-line p-3">{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </Panel>
            )}

            {active && (
              <Panel className="p-5">
                <div className="mb-4 flex items-center gap-2">
                  <Activity size={18} aria-hidden="true" />
                  <h2 className="text-base font-semibold">Activity Timeline</h2>
                </div>
                <div className="grid gap-3">
                  {activityEvents.length ? (
                    activityEvents.slice(0, 6).map((event) => (
                      <div key={event.id} className="rounded-md border border-line bg-paper/70 p-3 text-sm">
                        <div className="mb-1 flex items-start justify-between gap-3">
                          <span className="font-semibold capitalize">{eventLabel(event.event_type)}</span>
                          <span className="shrink-0 text-xs text-ink/55">{formatDateTime(event.created_at)}</span>
                        </div>
                        <p className="leading-6 text-ink/70">{event.message}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-ink/60">No activity yet.</p>
                  )}
                </div>
              </Panel>
            )}

            <Panel className="p-5">
              <div className="mb-4 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <FileQuestion size={18} aria-hidden="true" />
                  <h2 className="text-base font-semibold">Interview Plan</h2>
                </div>
                {active && (
                  <a
                    className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium hover:bg-paper"
                    href={`${API_BASE}/api/sessions/${active.id}/export`}
                    onClick={() => window.setTimeout(() => loadActivity(active.id), 600)}
                  >
                    <Download size={16} aria-hidden="true" />
                    Export
                  </a>
                )}
              </div>
              <div className="grid gap-4">
                {active?.interview_plan ? (
                  Object.entries(active.interview_plan).map(([category, questions]) => (
                    <div key={category}>
                      <h3 className="mb-2 text-sm font-semibold capitalize">{category.replace("_", " ")}</h3>
                      <ul className="grid gap-2">
                        {questions.map((item) => (
                          <li key={item} className="rounded-md border border-line bg-paper/70 p-3 text-sm leading-6">
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-ink/60">No interview plan yet.</p>
                )}
              </div>
            </Panel>

            <Panel className="p-5">
              <div className="mb-4 flex items-center gap-2">
                <BarChart3 size={18} aria-hidden="true" />
                <h2 className="text-base font-semibold">Feedback</h2>
              </div>
              {active?.feedback_report ? (
                <div className="grid gap-4 text-sm leading-6">
                  <p className="rounded-md bg-teal/10 p-3 text-teal">{active.feedback_report.role_fit_summary}</p>
                  <div>
                    <h3 className="font-semibold">Strengths</h3>
                    <ul className="mt-2 grid gap-2">
                      {active.feedback_report.strengths.map((item) => (
                        <li key={item} className="rounded-md border border-line p-3">{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h3 className="font-semibold">Next Steps</h3>
                    <ul className="mt-2 grid gap-2">
                      {active.feedback_report.next_steps.map((item) => (
                        <li key={item} className="rounded-md border border-line p-3">{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h3 className="flex items-center gap-2 font-semibold">
                      <ClipboardList size={16} aria-hidden="true" />
                      Resume Bullets
                    </h3>
                    <ul className="mt-2 grid gap-2">
                      {(active.feedback_report.tailored_resume_bullets ?? []).map((item) => (
                        <li key={item} className="rounded-md border border-line p-3">{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h3 className="flex items-center gap-2 font-semibold">
                      <Send size={16} aria-hidden="true" />
                      Outreach Message
                    </h3>
                    <p className="mt-2 rounded-md border border-line bg-paper/70 p-3">{active.feedback_report.outreach_message}</p>
                  </div>
                  <div>
                    <h3 className="font-semibold">Learning Plan</h3>
                    <div className="mt-2 grid gap-2">
                      {(active.feedback_report.learning_plan ?? []).map((item) => (
                        <div key={`${item.day}-${item.focus}`} className="rounded-md border border-line p-3">
                          <div className="text-xs font-semibold uppercase text-ink/55">Day {item.day}</div>
                          <div className="font-semibold">{item.focus}</div>
                          <div>{item.output}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-ink/60">No feedback yet.</p>
              )}
            </Panel>

            {active && (
              <button
                className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-berry/25 bg-berry/10 px-4 text-sm font-semibold text-berry hover:bg-berry/15"
                onClick={() => deleteSession(active.id)}
                title="Delete uploaded resume and analysis session"
              >
                <Trash2 size={18} aria-hidden="true" />
                Delete Session
              </button>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
