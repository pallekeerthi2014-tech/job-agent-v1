import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../api/client";
import type { Candidate, CandidateCreatePayload, CandidateMailbox, Employee } from "../types";

type GmailAnalyticsAdminPageProps = {
  candidates: Candidate[];
  employees: Employee[];
  onCreateCandidate: (payload: CandidateCreatePayload) => Promise<void>;
  onRefreshCandidates: () => Promise<void>;
};

const REPORT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1vttuuGRxZpf5VpW9CjMTj-KHPO0NxovWYWTgiJNPjQs/edit";
const CENTRAL_INBOX = "thinksuccess.ITconsulting@gmail.com";

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
  const [trackingEmail, setTrackingEmail] = useState("");
  const [mailboxes, setMailboxes] = useState<CandidateMailbox[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const mailboxByCandidate = useMemo(
    () => new Map(mailboxes.map((mailbox) => [mailbox.candidate_id, mailbox])),
    [mailboxes]
  );

  const selectedCandidate = typeof selectedCandidateId === "number"
    ? candidates.find((candidate) => candidate.id === selectedCandidateId) ?? null
    : null;

  const rows = useMemo(
    () => candidates.map((candidate) => ({
      candidate,
      mailbox: mailboxByCandidate.get(candidate.id) ?? null
    })),
    [candidates, mailboxByCandidate]
  );

  const summary = useMemo(() => {
    const linked = rows.filter((row) => row.mailbox);
    const emailRecorded = linked.filter((row) => hasRecordedForward(row.mailbox)).length;
    const waitingForEmail = linked.length - emailRecorded;
    const latestEmail = linked
      .map((row) => row.mailbox?.last_email_scan_at)
      .filter(Boolean)
      .sort()
      .pop();
    return {
      total: candidates.length,
      linked: linked.length,
      emailRecorded,
      waitingForEmail,
      latestEmail
    };
  }, [candidates.length, rows]);

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
    try {
      await onCreateCandidate(form);
      setForm(BLANK_FORM);
      await onRefreshCandidates();
      setNotice("Candidate created. Save the forwarding Gmail below after forwarding is enabled.");
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Unable to create candidate.");
    } finally {
      setBusy(false);
    }
  }

  async function handleLinkForwardingMailbox() {
    if (!selectedCandidate) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const email = (trackingEmail || selectedCandidate.email || "").trim().toLowerCase();
      if (!email) throw new Error("Enter the candidate Gmail address before saving.");
      const existingMailbox = mailboxByCandidate.get(selectedCandidate.id);
      const mailbox = existingMailbox ?? await apiClient.createCandidateMailbox({
        candidate_id: selectedCandidate.id,
        email
      });
      await apiClient.markCandidateMailboxForwardingActive(mailbox.id);
      await loadMailboxes();
      setNotice(`Forwarding setup saved for ${email}. Last email time appears only after a real inbox scanner records a forwarded message.`);
    } catch (linkError) {
      setError(linkError instanceof Error ? linkError.message : "Unable to save forwarding setup.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="dashboard-stack">
      <section className="panel gmail-analytics-console">
        <div className="gmail-console-header">
          <div className="section-heading">
            <h3>Gmail Forwarding Monitor</h3>
            <p>Candidate Gmail accounts forwarding into {CENTRAL_INBOX}, with the last forwarded email timestamp recorded by analytics.</p>
          </div>
          <a className="secondary-button" href={REPORT_SHEET_URL} target="_blank" rel="noreferrer">
            Open Analytics Sheet
          </a>
        </div>

        {error ? <div className="error-banner">{error}</div> : null}
        {notice ? <p className="success-msg">{notice}</p> : null}

        <div className="gmail-health-grid">
          <MetricCard label="Total candidates" value={summary.total} />
          <MetricCard label="Forwarding saved" value={summary.linked} />
          <MetricCard label="Email recorded" value={summary.emailRecorded} tone="good" />
          <MetricCard label="Awaiting first email" value={summary.waitingForEmail} tone={summary.waitingForEmail ? "warn" : "default"} />
          <MetricCard label="Latest email recorded" value={formatDate(summary.latestEmail)} wide />
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Save Forwarding Setup</h3>
          <p>Use this after the candidate Gmail has been configured to forward incoming mail to the ThinkSuccess inbox.</p>
        </div>
        <div className="gmail-setup-grid">
          <label>
            Candidate
            <select
              value={selectedCandidateId}
              onChange={(event) => {
                const candidateId = event.target.value ? Number(event.target.value) : "";
                const candidate = candidates.find((item) => item.id === candidateId);
                setSelectedCandidateId(candidateId);
                setTrackingEmail(candidate?.email ?? "");
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
          <label>
            Candidate Gmail
            <input
              type="email"
              value={trackingEmail}
              onChange={(event) => setTrackingEmail(event.target.value)}
              placeholder="abc.tsc@gmail.com"
            />
          </label>
          <button className="primary-button" onClick={() => void handleLinkForwardingMailbox()} disabled={!selectedCandidate || busy}>
            {busy ? "Saving..." : "Save setup"}
          </button>
          <div className="gmail-forwarding-card">
            <span>Forwarding destination</span>
            <strong>{CENTRAL_INBOX}</strong>
          </div>
        </div>
      </section>

      <section className="gmail-admin-layout">
        <section className="panel">
          <div className="section-heading">
            <h3>What This Page Shows</h3>
            <p>This page is a forwarding monitor, not a Gmail reader.</p>
          </div>
          <ul className="gmail-steps-list">
            <li>It lists which candidate Gmail accounts are saved for forwarding.</li>
            <li>It shows when analytics last recorded an email from that Gmail.</li>
            <li>It does not open, scan, or read your Gmail inbox from the website.</li>
          </ul>
        </section>

        <section className="panel">
          <div className="section-heading">
            <h3>Add Candidate</h3>
            <p>Create the candidate first if they are not already in the operations dashboard.</p>
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
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Forwarding Status</h3>
          <p>Which candidate Gmail accounts are saved, and when analytics last recorded a forwarded email from each one.</p>
        </div>
        <div className="table-wrapper">
          <table className="gmail-health-table">
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Candidate Gmail</th>
                <th>Forwarding</th>
                <th>Last email from this Gmail</th>
                <th>Last analytics update</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ candidate, mailbox }) => {
                const status = forwardingStatus(mailbox);
                return (
                  <tr key={candidate.id}>
                    <td>
                      <strong>{candidate.name}</strong>
                      <span className="gmail-table-subtext">{candidate.active ? "Active" : "Inactive"}</span>
                    </td>
                    <td>{mailbox?.email ?? candidate.email ?? "Missing"}</td>
                    <td><ForwardingBadge status={status} /></td>
                    <td>{formatDate(mailbox?.last_email_scan_at)}</td>
                    <td>{formatDate(mailbox?.last_successful_scan_at)}</td>
                    <td>
                      {mailbox ? (
                        <span className="gmail-table-subtext">Saved</span>
                      ) : (
                        <button
                          className="secondary-button"
                          onClick={() => {
                            setSelectedCandidateId(candidate.id);
                            setTrackingEmail(candidate.email ?? "");
                          }}
                        >
                          Save setup
                        </button>
                      )}
                    </td>
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

function MetricCard({ label, value, tone = "default", wide = false }: { label: string; value: string | number; tone?: "default" | "good" | "warn"; wide?: boolean }) {
  return (
    <div className={`gmail-metric-card gmail-metric-${tone}${wide ? " gmail-metric-wide" : ""}`}>
      <span>{label}</span>
      <strong>{value || "None"}</strong>
    </div>
  );
}

function ForwardingBadge({ status }: { status: ReturnType<typeof forwardingStatus> }) {
  return <span className={`flow-badge flow-${status.tone}`}>{status.label}</span>;
}

function forwardingStatus(mailbox?: CandidateMailbox | null) {
  if (!mailbox) return { label: "Needs setup", tone: "muted" as const };
  if (hasRecordedForward(mailbox)) return { label: "Email recorded", tone: "good" as const };
  return { label: "Setup saved", tone: "warn" as const };
}

function hasRecordedForward(mailbox?: CandidateMailbox | null) {
  return Boolean(mailbox?.last_email_scan_at && mailbox.status !== "flowing");
}

function formatDate(value?: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}
