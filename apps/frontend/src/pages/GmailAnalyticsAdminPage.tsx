import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../api/client";
import type { Candidate, CandidateCreatePayload, CandidateMailbox, Employee, GmailAnalyticsRunResponse } from "../types";

type GmailAnalyticsAdminPageProps = {
  candidates: Candidate[];
  employees: Employee[];
  onCreateCandidate: (payload: CandidateCreatePayload) => Promise<void>;
  onRefreshCandidates: () => Promise<void>;
};

const REPORT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1vttuuGRxZpf5VpW9CjMTj-KHPO0NxovWYWTgiJNPjQs/edit";

const BLANK_FORM: CandidateCreatePayload = {
  name: "",
  email: "",
  phone: "",
  location: "",
  assigned_employee: null,
  active: true
};

export function GmailAnalyticsAdminPage({
  candidates,
  employees,
  onCreateCandidate,
  onRefreshCandidates
}: GmailAnalyticsAdminPageProps) {
  const [form, setForm] = useState<CandidateCreatePayload>(BLANK_FORM);
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | "">("");
  const [mailboxes, setMailboxes] = useState<CandidateMailbox[]>([]);
  const [busy, setBusy] = useState(false);
  const [scanBusy, setScanBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [connectUrl, setConnectUrl] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<GmailAnalyticsRunResponse | null>(null);

  const mailboxByCandidate = useMemo(
    () => new Map(mailboxes.map((mailbox) => [mailbox.candidate_id, mailbox])),
    [mailboxes]
  );
  const selectedCandidate = typeof selectedCandidateId === "number"
    ? candidates.find((candidate) => candidate.id === selectedCandidateId) ?? null
    : null;

  async function loadMailboxes() {
    try {
      setMailboxes(await apiClient.getCandidateMailboxes());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load mailbox status.");
    }
  }

  useEffect(() => {
    void loadMailboxes();
  }, []);

  async function handleCreateCandidate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    setConnectUrl(null);
    try {
      await onCreateCandidate(form);
      setForm(BLANK_FORM);
      await onRefreshCandidates();
      setNotice("Candidate created. Select the candidate below, then click Generate Gmail connect link.");
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Unable to create candidate.");
    } finally {
      setBusy(false);
    }
  }

  async function handleGenerateLink() {
    if (!selectedCandidate) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    setConnectUrl(null);
    try {
      const existingMailbox = mailboxByCandidate.get(selectedCandidate.id);
      if (!existingMailbox && selectedCandidate.email) {
        await apiClient.createCandidateMailbox({
          candidate_id: selectedCandidate.id,
          email: selectedCandidate.email
        }).catch((createError) => {
          if (createError instanceof Error && createError.message.includes("409")) return;
          throw createError;
        });
      }
      const response = await apiClient.getCandidateGmailOAuthUrl(selectedCandidate.id);
      setConnectUrl(response.authorization_url);
      await loadMailboxes();
    } catch (linkError) {
      setError(linkError instanceof Error ? linkError.message : "Unable to generate Gmail connect link.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRunScan() {
    setScanBusy(true);
    setError(null);
    setRunResult(null);
    try {
      const result = await apiClient.runGmailAnalytics(true);
      setRunResult(result);
      await loadMailboxes();
    } catch (scanError) {
      setError(scanError instanceof Error ? scanError.message : "Unable to run Gmail analytics scan.");
    } finally {
      setScanBusy(false);
    }
  }

  return (
    <section className="dashboard-stack">
      <section className="panel">
        <div className="section-heading">
          <h3>Gmail Analytics Onboarding</h3>
          <p>Add candidate Gmail accounts, generate secure Google permission links, and publish mailbox analytics to the company Sheet.</p>
        </div>
        {error ? <div className="error-banner">{error}</div> : null}
        {notice ? <p className="success-msg">{notice}</p> : null}
        <div className="gmail-action-row">
          <a className="secondary-button" href={REPORT_SHEET_URL} target="_blank" rel="noreferrer">
            Open Analytics Sheet
          </a>
          <button className="primary-button" onClick={() => void handleRunScan()} disabled={scanBusy}>
            {scanBusy ? "Scanning..." : "Run scan and update Sheet"}
          </button>
        </div>
        {runResult ? (
          <div className="gmail-run-summary">
            <span>Mailboxes scanned: <strong>{runResult.mailboxes_scanned}</strong></span>
            <span>Email events: <strong>{runResult.email_events_created}</strong></span>
            <span>Calendar events: <strong>{runResult.calendar_events_upserted}</strong></span>
            <span>Sheet updated: <strong>{runResult.sheets_published ? "Yes" : "No"}</strong></span>
            <span>Failures: <strong>{runResult.failures}</strong></span>
          </div>
        ) : null}
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Add Candidate</h3>
          <p>Use the candidate Gmail that employees will use for applications.</p>
        </div>
        <form className="admin-user-form" onSubmit={(event) => void handleCreateCandidate(event)}>
          <label>
            Candidate name
            <input
              required
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              placeholder="Example: Priya Sharma"
            />
          </label>
          <label>
            Candidate Gmail
            <input
              required
              type="email"
              value={form.email ?? ""}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
              placeholder="candidate@gmail.com"
            />
          </label>
          <label>
            Phone
            <input
              value={form.phone ?? ""}
              onChange={(event) => setForm({ ...form, phone: event.target.value })}
              placeholder="Optional"
            />
          </label>
          <label>
            Location
            <input
              value={form.location ?? ""}
              onChange={(event) => setForm({ ...form, location: event.target.value })}
              placeholder="Optional"
            />
          </label>
          <label>
            Assigned employee
            <select
              value={form.assigned_employee ?? ""}
              onChange={(event) => setForm({ ...form, assigned_employee: event.target.value ? Number(event.target.value) : null })}
            >
              <option value="">Unassigned</option>
              {employees.map((employee) => (
                <option key={employee.id} value={employee.id}>{employee.name}</option>
              ))}
            </select>
          </label>
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Saving..." : "Create candidate"}
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Connect Candidate Gmail</h3>
          <p>Select a candidate, generate the Google link, then open it and sign in with that candidate Gmail.</p>
        </div>
        <div className="gmail-connect-grid">
          <label>
            Candidate
            <select
              value={selectedCandidateId}
              onChange={(event) => {
                setSelectedCandidateId(event.target.value ? Number(event.target.value) : "");
                setConnectUrl(null);
              }}
            >
              <option value="">Select candidate</option>
              {candidates.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.name} {candidate.email ? `(${candidate.email})` : ""}
                </option>
              ))}
            </select>
          </label>
          <button className="primary-button" onClick={() => void handleGenerateLink()} disabled={!selectedCandidate || busy}>
            {busy ? "Preparing..." : "Generate Gmail connect link"}
          </button>
        </div>
        {connectUrl ? (
          <div className="gmail-connect-result">
            <p>Open this link, sign in with the candidate Gmail, and click Allow.</p>
            <a className="primary-button" href={connectUrl} target="_blank" rel="noreferrer">Open Google permission page</a>
            <textarea readOnly value={connectUrl} />
          </div>
        ) : null}
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Mailbox Status</h3>
          <p>Connected candidates are ready for scan and reporting.</p>
        </div>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Email</th>
                <th>Gmail</th>
                <th>Calendar</th>
                <th>Status</th>
                <th>Last scan</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => {
                const mailbox = mailboxByCandidate.get(candidate.id);
                return (
                  <tr key={candidate.id}>
                    <td>{candidate.name}</td>
                    <td>{mailbox?.email ?? candidate.email ?? "Missing"}</td>
                    <td>{mailbox?.gmail_connected ? "Connected" : "Not connected"}</td>
                    <td>{mailbox?.calendar_connected ? "Connected" : "Not connected"}</td>
                    <td>{mailbox?.status ?? "not_connected"}</td>
                    <td>{formatDate(mailbox?.last_successful_scan_at)}</td>
                    <td>{mailbox?.last_error ?? ""}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}
