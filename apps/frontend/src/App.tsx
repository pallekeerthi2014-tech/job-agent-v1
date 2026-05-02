import { useEffect, useMemo, useState } from "react";

import { apiClient, clearStoredAccessToken, getStoredAccessToken, setStoredAccessToken } from "./api/client";
import { FiltersBar } from "./components/FiltersBar";
import { Layout } from "./components/Layout";
import { AdminCandidatesPage } from "./pages/AdminCandidatesPage";
import { AdminSourcesPage } from "./pages/AdminSourcesPage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { AdminWhatsappPage } from "./pages/AdminWhatsappPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { CandidateDetailPage } from "./pages/CandidateDetailPage";
import { CandidateListPage } from "./pages/CandidateListPage";
import { CandidatePortalPage } from "./pages/CandidatePortalPage";
import { EmployeeWorkQueuePage } from "./pages/EmployeeWorkQueuePage";
import { JobMatchDetailPage } from "./pages/JobMatchDetailPage";
import { LoginPage } from "./pages/LoginPage";
import { OperationsDashboardPage } from "./pages/OperationsDashboardPage";
import type {
  AlertRecipient,
  AlertRecipientCreatePayload,
  AnalyticsOverview,
  Application,
  Candidate,
  CandidateCreatePayload,
  Employee,
  Job,
  Match,
  PriorityFilter,
  User,
  UserCreatePayload,
  WorkQueueItem,
  WorkQueueReportPayload
} from "./types";

type ActivePage =
  | "operations-dashboard"
  | "candidate-list"
  | "candidate-detail"
  | "employee-work-queue"
  | "job-match-detail"
  | "admin-users"
  | "admin-candidates"
  | "admin-whatsapp"
  | "admin-sources"
  | "analytics";

const PRIORITY_TO_NUM: Record<Exclude<PriorityFilter, "All">, number> = {
  High: 1,
  Medium: 2,
  Low: 3
};

const DASHBOARD_PAGE_LIMIT = 200;
const ADMIN_ONLY_PAGES: ActivePage[] = ["admin-users", "admin-candidates", "admin-whatsapp", "admin-sources", "analytics"];

export default function App() {
  const initialResetToken = new URLSearchParams(window.location.search).get("reset_token");
  const [activePage, setActivePage] = useState<ActivePage>("operations-dashboard");
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccess, setAuthSuccess] = useState<string | null>(null);
  const [authBusy, setAuthBusy] = useState(false);
  const [forgotPasswordPreview, setForgotPasswordPreview] = useState<Awaited<ReturnType<typeof apiClient.forgotPassword>> | null>(null);

  // Core data
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [workQueues, setWorkQueues] = useState<WorkQueueItem[]>([]);

  // Phase 3 data
  const [whatsappRecipients, setWhatsappRecipients] = useState<AlertRecipient[]>([]);
  const [analyticsData, setAnalyticsData] = useState<AnalyticsOverview | null>(null);
  const [analyticsBusy, setAnalyticsBusy] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  // Selections & filters
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(null);
  const [selectedPriority, setSelectedPriority] = useState<PriorityFilter>("All");
  const [selectedMatchId, setSelectedMatchId] = useState<number | null>(null);
  const [dashboardSearchTerm, setDashboardSearchTerm] = useState("");
  const [dashboardSourceFilter, setDashboardSourceFilter] = useState("all");
  const [dashboardStatusFilter, setDashboardStatusFilter] = useState("pending");
  const [dashboardDayFilter, setDashboardDayFilter] = useState("all");

  // Busy / error states
  const [busyMatchId, setBusyMatchId] = useState<number | null>(null);
  const [busyQueueId, setBusyQueueId] = useState<number | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [adminBusy, setAdminBusy] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);
  const [whatsappBusy, setWhatsappBusy] = useState(false);
  const [whatsappError, setWhatsappError] = useState<string | null>(null);
  const [candidateAdminBusy, setCandidateAdminBusy] = useState(false);
  const [candidateAdminError, setCandidateAdminError] = useState<string | null>(null);

  // ── Auth bootstrap ──────────────────────────────────────────────────────────
  useEffect(() => {
    async function bootstrapAuth() {
      const existingToken = getStoredAccessToken();
      if (!existingToken) { setAuthReady(true); return; }
      try {
        const user = await apiClient.getMe();
        setCurrentUser(user);
      } catch {
        clearStoredAccessToken();
      } finally {
        setAuthReady(true);
      }
    }
    void bootstrapAuth();
  }, []);

  useEffect(() => {
    if (!currentUser) { setSelectedEmployeeId(null); return; }
    if (currentUser.role === "employee") {
      setSelectedEmployeeId(currentUser.employee_id ?? null);
      if (ADMIN_ONLY_PAGES.includes(activePage)) {
        setActivePage("operations-dashboard");
      }
    }
  }, [activePage, currentUser]);

  // ── Main data load ──────────────────────────────────────────────────────────
  async function loadData() {
    if (!currentUser) return;
    try {
      setPageError(null);
      const priorityValue = selectedPriority === "All" ? undefined : PRIORITY_TO_NUM[selectedPriority];

      const [
        candidateResponse, employeeResponse, jobResponse, matchResponse,
        applicationResponse, workQueueResponse, userResponse, waResponse
      ] = await Promise.all([
        apiClient.getCandidates({
          limit: DASHBOARD_PAGE_LIMIT, offset: 0,
          employee_id: currentUser.role === "employee" ? currentUser.employee_id ?? undefined : selectedEmployeeId ?? undefined
        }),
        apiClient.getEmployees(),
        apiClient.getJobs({ limit: DASHBOARD_PAGE_LIMIT, offset: 0 }),
        apiClient.getMatches({
          limit: DASHBOARD_PAGE_LIMIT, offset: 0,
          candidate_id: selectedCandidateId ?? undefined,
          employee_id: currentUser.role === "employee" ? currentUser.employee_id ?? undefined : selectedEmployeeId ?? undefined,
          priority: priorityValue,
          sort_by: "score", sort_order: "desc"
        }),
        apiClient.getApplications({
          limit: DASHBOARD_PAGE_LIMIT, offset: 0,
          candidate_id: selectedCandidateId ?? undefined,
          employee_id: currentUser.role === "employee" ? currentUser.employee_id ?? undefined : selectedEmployeeId ?? undefined
        }),
        apiClient.getWorkQueues({
          limit: DASHBOARD_PAGE_LIMIT, offset: 0,
          candidate_id: selectedCandidateId ?? undefined,
          employee_id: currentUser.role === "employee" ? currentUser.employee_id ?? undefined : selectedEmployeeId ?? undefined,
          priority: selectedPriority === "All" ? undefined : selectedPriority,
          sort_by: "created_at", sort_order: "desc"
        }),
        currentUser.role === "super_admin" ? apiClient.getUsers() : Promise.resolve([]),
        currentUser.role === "super_admin" ? apiClient.getWhatsappRecipients() : Promise.resolve([])
      ]);

      setCandidates(candidateResponse.items);
      setEmployees(employeeResponse);
      setJobs(jobResponse.items);
      setMatches(matchResponse.items);
      setApplications(applicationResponse.items);
      setWorkQueues(workQueueResponse.items);
      setUsers(userResponse);
      setWhatsappRecipients(waResponse as AlertRecipient[]);
    } catch (loadError) {
      setPageError(loadError instanceof Error ? loadError.message : "Unknown dashboard error");
    }
  }

  useEffect(() => { void loadData(); }, [currentUser, selectedCandidateId, selectedEmployeeId, selectedPriority]);

  // Load analytics when navigating to analytics page
  useEffect(() => {
    if (activePage !== "analytics" || !currentUser || currentUser.role !== "super_admin") return;
    setAnalyticsBusy(true);
    setAnalyticsError(null);
    apiClient.getAnalyticsOverview()
      .then(setAnalyticsData)
      .catch((e) => setAnalyticsError(e instanceof Error ? e.message : "Analytics load failed"))
      .finally(() => setAnalyticsBusy(false));
  }, [activePage, currentUser]);

  // ── Derived maps ────────────────────────────────────────────────────────────
  const candidateMap = useMemo(() => new Map(candidates.map((c) => [c.id, c])), [candidates]);
  const employeeMap = useMemo(() => new Map(employees.map((e) => [e.id, e])), [employees]);
  const jobMap = useMemo(() => new Map(jobs.map((j) => [j.id, j])), [jobs]);
  const matchMap = useMemo(() => new Map(matches.map((m) => [m.id, m])), [matches]);
  const selectedCandidate = selectedCandidateId ? candidateMap.get(selectedCandidateId) ?? null : null;
  const selectedMatch = selectedMatchId ? matches.find((m) => m.id === selectedMatchId) ?? null : null;
  const selectedJob = selectedMatch ? jobMap.get(selectedMatch.job_id) ?? null : null;
  const selectedMatchCandidate = selectedMatch ? candidateMap.get(selectedMatch.candidate_id) ?? null : null;
  const candidateMatches = selectedCandidate ? matches.filter((m) => m.candidate_id === selectedCandidate.id) : [];
  const candidateApplications = selectedCandidate ? applications.filter((a) => a.candidate_id === selectedCandidate.id) : [];

  // ── Auth handlers ───────────────────────────────────────────────────────────
  async function handleLogin(payload: { email: string; password: string }) {
    setAuthBusy(true); setAuthError(null); setAuthSuccess(null);
    try {
      const response = await apiClient.login(payload);
      setStoredAccessToken(response.access_token);
      setCurrentUser(response.user);
      setActivePage("operations-dashboard");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Login failed");
    } finally { setAuthBusy(false); }
  }

  async function handleRegister(payload: { name: string; email: string; password: string }) {
    setAuthBusy(true); setAuthError(null); setAuthSuccess(null);
    try {
      const response = await apiClient.candidateRegister(payload);
      setStoredAccessToken(response.access_token);
      setCurrentUser(response.user);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Registration failed");
    } finally { setAuthBusy(false); }
  }

  async function handleGoogleAuth(credential: string) {
    setAuthBusy(true); setAuthError(null); setAuthSuccess(null);
    try {
      const response = await apiClient.portalGoogleAuth(credential);
      setStoredAccessToken(response.access_token);
      setCurrentUser(response.user);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Google sign-in failed");
    } finally { setAuthBusy(false); }
  }

  async function handleForgotPassword(payload: { email: string }) {
    setAuthBusy(true); setAuthError(null); setAuthSuccess(null);
    try {
      const response = await apiClient.forgotPassword(payload);
      setForgotPasswordPreview(response);
      setAuthSuccess(response.message);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Unable to prepare reset password flow");
    } finally { setAuthBusy(false); }
  }

  async function handleSelfResetPassword(payload: { token: string; password: string }) {
    setAuthBusy(true); setAuthError(null); setAuthSuccess(null);
    try {
      const response = await apiClient.resetPassword(payload);
      setAuthSuccess(response.message);
      setForgotPasswordPreview(null);
      if (window.location.search.includes("reset_token")) {
        window.history.replaceState({}, "", window.location.pathname);
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Unable to reset password");
    } finally { setAuthBusy(false); }
  }

  function handleLogout() {
    clearStoredAccessToken();
    setCurrentUser(null);
    setUsers([]); setCandidates([]); setEmployees([]); setJobs([]);
    setMatches([]); setApplications([]); setWorkQueues([]);
    setWhatsappRecipients([]); setAnalyticsData(null);
    setSelectedCandidateId(null); setSelectedEmployeeId(null); setSelectedMatchId(null);
  }

  // ── Navigation ──────────────────────────────────────────────────────────────
  function viewMatch(match: Match) {
    setSelectedMatchId(match.id);
    setSelectedCandidateId(match.candidate_id);
    setActivePage("job-match-detail");
  }

  function viewQueueItem(queueItem: WorkQueueItem) {
    if (!queueItem.match_id) return;
    const match = matchMap.get(queueItem.match_id);
    if (match) viewMatch(match);
  }

  // ── Application / skip ──────────────────────────────────────────────────────
  async function updateApplication(
    params: { candidateId: number; jobId: number; employeeId?: number | null; matchId?: number | null; queueId?: number | null },
    status: "applied" | "skipped"
  ) {
    if (params.matchId) setBusyMatchId(params.matchId);
    if (params.queueId) setBusyQueueId(params.queueId);
    try {
      await apiClient.createApplication({
        candidate_id: params.candidateId,
        job_id: params.jobId,
        employee_id: params.employeeId ?? selectedEmployeeId ?? undefined,
        status,
        notes: status === "applied" ? "Applied from dashboard." : "Skipped from dashboard."
      });
      await loadData();
    } finally {
      setBusyMatchId(null);
      setBusyQueueId(null);
    }
  }

  // ── Report work queue item ──────────────────────────────────────────────────
  async function handleReportQueueItem(queueItem: WorkQueueItem, payload: WorkQueueReportPayload) {
    setBusyQueueId(queueItem.id);
    try {
      await apiClient.reportWorkQueueItem(queueItem.id, payload);
      await loadData();
    } finally {
      setBusyQueueId(null);
    }
  }

  // ── Admin: Users ────────────────────────────────────────────────────────────
  async function handleCreateUser(payload: UserCreatePayload) {
    setAdminBusy(true); setAdminError(null);
    try { await apiClient.createUser(payload); await loadData(); }
    catch (error) { setAdminError(error instanceof Error ? error.message : "Unable to create user"); }
    finally { setAdminBusy(false); }
  }

  async function handleToggleUser(user: User) {
    setAdminBusy(true); setAdminError(null);
    try { await apiClient.updateUser(user.id, { is_active: !user.is_active }); await loadData(); }
    catch (error) { setAdminError(error instanceof Error ? error.message : "Unable to update user"); }
    finally { setAdminBusy(false); }
  }

  async function handleResetPassword(user: User, newPassword: string) {
    setAdminBusy(true); setAdminError(null);
    try { await apiClient.updateUser(user.id, { password: newPassword }); await loadData(); }
    catch (error) { setAdminError(error instanceof Error ? error.message : "Unable to reset password"); }
    finally { setAdminBusy(false); }
  }

  // ── Admin: Candidates ───────────────────────────────────────────────────────
  async function handleCreateCandidate(payload: CandidateCreatePayload) {
    setCandidateAdminBusy(true); setCandidateAdminError(null);
    try { await apiClient.createCandidate(payload); await loadData(); }
    catch (error) { setCandidateAdminError(error instanceof Error ? error.message : "Unable to create candidate"); }
    finally { setCandidateAdminBusy(false); }
  }

  async function handleUpdateCandidate(id: number, payload: Partial<CandidateCreatePayload>) {
    setCandidateAdminBusy(true); setCandidateAdminError(null);
    try { await apiClient.updateCandidate(id, payload); await loadData(); }
    catch (error) { setCandidateAdminError(error instanceof Error ? error.message : "Unable to update candidate"); }
    finally { setCandidateAdminBusy(false); }
  }

  async function handleDeleteCandidate(id: number) {
    setCandidateAdminBusy(true); setCandidateAdminError(null);
    try { await apiClient.deleteCandidate(id); await loadData(); }
    catch (error) { setCandidateAdminError(error instanceof Error ? error.message : "Unable to delete candidate"); }
    finally { setCandidateAdminBusy(false); }
  }

  // ── Admin: WhatsApp ─────────────────────────────────────────────────────────
  async function handleAddWhatsapp(payload: AlertRecipientCreatePayload) {
    setWhatsappBusy(true); setWhatsappError(null);
    try { await apiClient.createWhatsappRecipient(payload); await loadData(); }
    catch (error) { setWhatsappError(error instanceof Error ? error.message : "Unable to add recipient"); }
    finally { setWhatsappBusy(false); }
  }

  async function handleToggleWhatsapp(recipient: AlertRecipient) {
    setWhatsappBusy(true); setWhatsappError(null);
    try { await apiClient.updateWhatsappRecipient(recipient.id, { is_active: !recipient.is_active }); await loadData(); }
    catch (error) { setWhatsappError(error instanceof Error ? error.message : "Unable to update recipient"); }
    finally { setWhatsappBusy(false); }
  }

  async function handleDeleteWhatsapp(id: number) {
    setWhatsappBusy(true); setWhatsappError(null);
    try { await apiClient.deleteWhatsappRecipient(id); await loadData(); }
    catch (error) { setWhatsappError(error instanceof Error ? error.message : "Unable to remove recipient"); }
    finally { setWhatsappBusy(false); }
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  if (!authReady) return <main className="login-shell">Loading...</main>;

  if (!currentUser) {
    return (
      <LoginPage
        error={authError}
        successMessage={authSuccess}
        isSubmitting={authBusy}
        initialResetToken={initialResetToken}
        forgotPasswordPreview={forgotPasswordPreview}
        googleClientId={import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined}
        onLogin={handleLogin}
        onRegister={handleRegister}
        onGoogleAuth={handleGoogleAuth}
        onForgotPassword={handleForgotPassword}
        onResetPassword={handleSelfResetPassword}
      />
    );
  }

  // ── Candidate portal short-circuit ──────────────────────────────────────────
  if (currentUser.role === "candidate") {
    return <CandidatePortalPage currentUser={currentUser} onLogout={handleLogout} />;
  }

  const showFiltersBar = !ADMIN_ONLY_PAGES.includes(activePage);

  return (
    <Layout activePage={activePage} onNavigate={(page) => setActivePage(page as ActivePage)} currentUser={currentUser} onLogout={handleLogout}>
      <section className="hero">
        <div>
          <p className="eyebrow">Think Success Consulting</p>
          <h2>Daily job matching operations in one branded workspace.</h2>
          <p className="hero-copy">
            Review candidate-job fit, inspect match explanations, and move through employee actions with a focused
            recruiting operations console.
          </p>
        </div>
      </section>

      {pageError ? <div className="error-banner">{pageError}</div> : null}

      {showFiltersBar ? (
        <FiltersBar
          candidates={candidates}
          employees={employees}
          canFilterByEmployee={currentUser.role === "super_admin"}
          selectedCandidateId={selectedCandidateId}
          selectedEmployeeId={selectedEmployeeId}
          selectedPriority={selectedPriority}
          onCandidateChange={setSelectedCandidateId}
          onEmployeeChange={setSelectedEmployeeId}
          onPriorityChange={setSelectedPriority}
        />
      ) : null}

      {activePage === "operations-dashboard" ? (
        <OperationsDashboardPage
          queueItems={workQueues}
          candidateMap={candidateMap}
          employeeMap={employeeMap}
          jobMap={jobMap}
          matchMap={matchMap}
          busyQueueId={busyQueueId}
          searchTerm={dashboardSearchTerm}
          sourceFilter={dashboardSourceFilter}
          statusFilter={dashboardStatusFilter}
          dayFilter={dashboardDayFilter}
          onSearchTermChange={setDashboardSearchTerm}
          onSourceFilterChange={setDashboardSourceFilter}
          onStatusFilterChange={setDashboardStatusFilter}
          onDayFilterChange={setDashboardDayFilter}
          onOpenMatch={viewQueueItem}
          onMarkApplied={(queueItem) =>
            updateApplication(
              { candidateId: queueItem.candidate_id, jobId: queueItem.job_id, employeeId: queueItem.employee_id, matchId: queueItem.match_id, queueId: queueItem.id },
              "applied"
            )
          }
          onSkip={(queueItem) =>
            updateApplication(
              { candidateId: queueItem.candidate_id, jobId: queueItem.job_id, employeeId: queueItem.employee_id, matchId: queueItem.match_id, queueId: queueItem.id },
              "skipped"
            )
          }
        />
      ) : null}

      {activePage === "candidate-list" ? (
        <CandidateListPage matches={matches} candidateMap={candidateMap} jobMap={jobMap} onSelectMatch={viewMatch} />
      ) : null}

      {activePage === "candidate-detail" ? (
        <CandidateDetailPage
          candidate={selectedCandidate}
          matches={candidateMatches}
          jobMap={jobMap}
          applications={candidateApplications}
          onSelectMatch={viewMatch}
        />
      ) : null}

      {activePage === "employee-work-queue" ? (
        <EmployeeWorkQueuePage
          matches={matches}
          workQueueItems={workQueues}
          candidateMap={candidateMap}
          jobMap={jobMap}
          busyMatchId={busyMatchId}
          busyQueueId={busyQueueId}
          onViewJob={viewMatch}
          onMarkApplied={(match) =>
            updateApplication({ candidateId: match.candidate_id, jobId: match.job_id, matchId: match.id }, "applied")
          }
          onSkip={(match) =>
            updateApplication({ candidateId: match.candidate_id, jobId: match.job_id, matchId: match.id }, "skipped")
          }
          onReport={handleReportQueueItem}
        />
      ) : null}

      {activePage === "job-match-detail" ? (
        <JobMatchDetailPage
          match={selectedMatch}
          job={selectedJob}
          candidate={selectedMatchCandidate}
          busy={busyMatchId === selectedMatch?.id}
          onMarkApplied={() =>
            selectedMatch
              ? updateApplication({ candidateId: selectedMatch.candidate_id, jobId: selectedMatch.job_id, matchId: selectedMatch.id }, "applied")
              : Promise.resolve()
          }
          onSkip={() =>
            selectedMatch
              ? updateApplication({ candidateId: selectedMatch.candidate_id, jobId: selectedMatch.job_id, matchId: selectedMatch.id }, "skipped")
              : Promise.resolve()
          }
        />
      ) : null}

      {activePage === "admin-candidates" && currentUser.role === "super_admin" ? (
        <AdminCandidatesPage
          candidates={candidates}
          employees={employees}
          busy={candidateAdminBusy}
          error={candidateAdminError}
          onCreateCandidate={handleCreateCandidate}
          onUpdateCandidate={handleUpdateCandidate}
          onDeleteCandidate={handleDeleteCandidate}
          onRefresh={loadData}
        />
      ) : null}

      {activePage === "admin-users" && currentUser.role === "super_admin" ? (
        <AdminUsersPage
          users={users}
          busy={adminBusy}
          error={adminError}
          onCreateUser={handleCreateUser}
          onToggleUser={handleToggleUser}
          onResetPassword={handleResetPassword}
        />
      ) : null}

      {activePage === "admin-whatsapp" && currentUser.role === "super_admin" ? (
        <AdminWhatsappPage
          recipients={whatsappRecipients}
          busy={whatsappBusy}
          error={whatsappError}
          onAdd={handleAddWhatsapp}
          onToggle={handleToggleWhatsapp}
          onDelete={handleDeleteWhatsapp}
        />
      ) : null}

      {activePage === "admin-sources" && currentUser.role === "super_admin" ? (
        <AdminSourcesPage />
      ) : null}

      {activePage === "analytics" && currentUser.role === "super_admin" ? (
        <AnalyticsPage
          data={analyticsData}
          busy={analyticsBusy}
          error={analyticsError}
          onRefresh={() => {
            setAnalyticsBusy(true);
            apiClient.getAnalyticsOverview()
              .then(setAnalyticsData)
              .catch((e) => setAnalyticsError(e instanceof Error ? e.message : "Analytics load failed"))
              .finally(() => setAnalyticsBusy(false));
          }}
        />
      ) : null}
    </Layout>
  );
}
