import { useEffect, useMemo, useState } from "react";

import { apiClient } from "./api/client";
import { FiltersBar } from "./components/FiltersBar";
import { Layout } from "./components/Layout";
import { CandidateDetailPage } from "./pages/CandidateDetailPage";
import { CandidateListPage } from "./pages/CandidateListPage";
import { EmployeeWorkQueuePage } from "./pages/EmployeeWorkQueuePage";
import { JobMatchDetailPage } from "./pages/JobMatchDetailPage";
import { OperationsDashboardPage } from "./pages/OperationsDashboardPage";
import type { Application, Candidate, Employee, Job, Match, PriorityFilter, WorkQueueItem } from "./types";

type ActivePage =
  | "operations-dashboard"
  | "candidate-list"
  | "candidate-detail"
  | "employee-work-queue"
  | "job-match-detail";

const PRIORITY_TO_NUM: Record<Exclude<PriorityFilter, "All">, number> = {
  High: 1,
  Medium: 2,
  Low: 3
};

const DASHBOARD_PAGE_LIMIT = 200;

export default function App() {
  const [activePage, setActivePage] = useState<ActivePage>("operations-dashboard");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [workQueues, setWorkQueues] = useState<WorkQueueItem[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(null);
  const [selectedPriority, setSelectedPriority] = useState<PriorityFilter>("All");
  const [selectedMatchId, setSelectedMatchId] = useState<number | null>(null);
  const [dashboardSearchTerm, setDashboardSearchTerm] = useState("");
  const [dashboardSourceFilter, setDashboardSourceFilter] = useState("all");
  const [dashboardStatusFilter, setDashboardStatusFilter] = useState("pending");
  const [dashboardDayFilter, setDashboardDayFilter] = useState("all");
  const [busyMatchId, setBusyMatchId] = useState<number | null>(null);
  const [busyQueueId, setBusyQueueId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    try {
      setError(null);
      const priorityValue = selectedPriority === "All" ? undefined : PRIORITY_TO_NUM[selectedPriority];

      const [candidateResponse, employeeResponse, jobResponse, matchResponse, applicationResponse, workQueueResponse] =
        await Promise.all([
          apiClient.getCandidates({
            limit: DASHBOARD_PAGE_LIMIT,
            offset: 0
          }),
          apiClient.getEmployees(),
          apiClient.getJobs({
            limit: DASHBOARD_PAGE_LIMIT,
            offset: 0
          }),
          apiClient.getMatches({
            limit: DASHBOARD_PAGE_LIMIT,
            offset: 0,
            candidate_id: selectedCandidateId ?? undefined,
            employee_id: selectedEmployeeId ?? undefined,
            priority: priorityValue,
            sort_by: "score",
            sort_order: "desc"
          }),
          apiClient.getApplications({
            limit: DASHBOARD_PAGE_LIMIT,
            offset: 0,
            candidate_id: selectedCandidateId ?? undefined,
            employee_id: selectedEmployeeId ?? undefined
          }),
          apiClient.getWorkQueues({
            limit: DASHBOARD_PAGE_LIMIT,
            offset: 0,
            candidate_id: selectedCandidateId ?? undefined,
            employee_id: selectedEmployeeId ?? undefined,
            priority: selectedPriority === "All" ? undefined : selectedPriority,
            sort_by: "created_at",
            sort_order: "desc"
          })
        ]);

      setCandidates(candidateResponse.items);
      setEmployees(employeeResponse);
      setJobs(jobResponse.items);
      setMatches(matchResponse.items);
      setApplications(applicationResponse.items);
      setWorkQueues(workQueueResponse.items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unknown dashboard error");
    }
  }

  useEffect(() => {
    void loadData();
  }, [selectedCandidateId, selectedEmployeeId, selectedPriority]);

  const candidateMap = useMemo(() => new Map(candidates.map((candidate) => [candidate.id, candidate])), [candidates]);
  const employeeMap = useMemo(() => new Map(employees.map((employee) => [employee.id, employee])), [employees]);
  const jobMap = useMemo(() => new Map(jobs.map((job) => [job.id, job])), [jobs]);
  const matchMap = useMemo(() => new Map(matches.map((match) => [match.id, match])), [matches]);
  const selectedCandidate = selectedCandidateId ? candidateMap.get(selectedCandidateId) ?? null : null;
  const selectedMatch = selectedMatchId ? matches.find((match) => match.id === selectedMatchId) ?? null : null;
  const selectedJob = selectedMatch ? jobMap.get(selectedMatch.job_id) ?? null : null;
  const selectedMatchCandidate = selectedMatch ? candidateMap.get(selectedMatch.candidate_id) ?? null : null;
  const candidateMatches = selectedCandidate ? matches.filter((match) => match.candidate_id === selectedCandidate.id) : [];
  const candidateApplications = selectedCandidate
    ? applications.filter((application) => application.candidate_id === selectedCandidate.id)
    : [];

  function viewMatch(match: Match) {
    setSelectedMatchId(match.id);
    setSelectedCandidateId(match.candidate_id);
    setActivePage("job-match-detail");
  }

  function viewQueueItem(queueItem: WorkQueueItem) {
    if (!queueItem.match_id) {
      return;
    }

    const match = matchMap.get(queueItem.match_id);
    if (!match) {
      return;
    }
    viewMatch(match);
  }

  async function updateApplication(
    params: {
      candidateId: number;
      jobId: number;
      employeeId?: number | null;
      matchId?: number | null;
      queueId?: number | null;
    },
    status: "applied" | "skipped"
  ) {
    if (params.matchId) {
      setBusyMatchId(params.matchId);
    }
    if (params.queueId) {
      setBusyQueueId(params.queueId);
    }
    try {
      await apiClient.createApplication({
        candidate_id: params.candidateId,
        job_id: params.jobId,
        employee_id: params.employeeId ?? selectedEmployeeId ?? undefined,
        status,
        notes: status === "applied" ? "Applied from operations dashboard." : "Skipped from operations dashboard."
      });
      await loadData();
    } finally {
      setBusyMatchId(null);
      setBusyQueueId(null);
    }
  }

  return (
    <Layout activePage={activePage} onNavigate={(page) => setActivePage(page as ActivePage)}>
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

      {error ? <div className="error-banner">{error}</div> : null}

      <FiltersBar
        candidates={candidates}
        employees={employees}
        selectedCandidateId={selectedCandidateId}
        selectedEmployeeId={selectedEmployeeId}
        selectedPriority={selectedPriority}
        onCandidateChange={setSelectedCandidateId}
        onEmployeeChange={setSelectedEmployeeId}
        onPriorityChange={setSelectedPriority}
      />

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
              {
                candidateId: queueItem.candidate_id,
                jobId: queueItem.job_id,
                employeeId: queueItem.employee_id,
                matchId: queueItem.match_id,
                queueId: queueItem.id
              },
              "applied"
            )
          }
          onSkip={(queueItem) =>
            updateApplication(
              {
                candidateId: queueItem.candidate_id,
                jobId: queueItem.job_id,
                employeeId: queueItem.employee_id,
                matchId: queueItem.match_id,
                queueId: queueItem.id
              },
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
          candidateMap={candidateMap}
          jobMap={jobMap}
          busyMatchId={busyMatchId}
          onViewJob={viewMatch}
          onMarkApplied={(match) =>
            updateApplication(
              {
                candidateId: match.candidate_id,
                jobId: match.job_id,
                employeeId: candidateMap.get(match.candidate_id)?.assigned_employee ?? selectedEmployeeId ?? undefined,
                matchId: match.id
              },
              "applied"
            )
          }
          onSkip={(match) =>
            updateApplication(
              {
                candidateId: match.candidate_id,
                jobId: match.job_id,
                employeeId: candidateMap.get(match.candidate_id)?.assigned_employee ?? selectedEmployeeId ?? undefined,
                matchId: match.id
              },
              "skipped"
            )
          }
        />
      ) : null}

      {activePage === "job-match-detail" ? (
        <JobMatchDetailPage
          match={selectedMatch}
          candidate={selectedMatchCandidate}
          job={selectedJob}
          busy={busyMatchId === selectedMatch?.id}
          onMarkApplied={() =>
            selectedMatch
              ? updateApplication(
                  {
                    candidateId: selectedMatch.candidate_id,
                    jobId: selectedMatch.job_id,
                    employeeId:
                      candidateMap.get(selectedMatch.candidate_id)?.assigned_employee ?? selectedEmployeeId ?? undefined,
                    matchId: selectedMatch.id
                  },
                  "applied"
                )
              : Promise.resolve()
          }
          onSkip={() =>
            selectedMatch
              ? updateApplication(
                  {
                    candidateId: selectedMatch.candidate_id,
                    jobId: selectedMatch.job_id,
                    employeeId:
                      candidateMap.get(selectedMatch.candidate_id)?.assigned_employee ?? selectedEmployeeId ?? undefined,
                    matchId: selectedMatch.id
                  },
                  "skipped"
                )
              : Promise.resolve()
          }
        />
      ) : null}
    </Layout>
  );
}
