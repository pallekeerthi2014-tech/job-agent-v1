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
  const [rowBusyId, setRowBusyId] = useState<number | null>(null);
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

  const health = useMemo(() => {
    const linked = rows.filter((row) => row.mailbox);
    const flowing = linked.filter((row) => isFlowing(row.mailbox)).length;
    const needsCheck = linked.filter((row) => row.mailbox?.status === "forwarding_active").length;
    const notSeen = linked.filter((row) => row.mailbox?.status === "no_messages_seen").length;
    const lastCheck = linked
      .map((row) => row.mailbox?.last_successful_scan_at)
      .filter(Boolean)
      .sort()
      .pop();
    return {
      total: candidates.length,
      linked: linked.length,
      flowing,
      needsCheck,
      notSeen,
      lastCheck
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
      setNotice("Candidate created. Link the Gmail address below after forwarding is configured.");
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
      if (!email) throw new Error("Enter the candidate Gmail address before linking.");
      const existingMailbox = mailboxByCandidate.get(selectedCandidate.id);
      const mailbox = existingMailbox ?? await apiClient.createCandidateMailbox({
        candidate_id: selectedCandidate.id,
        email
      });
      await apiClient.markCandidateMailboxForwardingActive(mailbox.id);
      await loadMailboxes();
      setNotice(`Forwarding setup recorded for ${email}. Send a test email, confirm it lands in ${CENTRAL_INBOX}, then mark the flow as received.`);
    } catch (linkError) {
      setError(linkError instanceof Error ? linkError.message : "Unable to link candidate Gmail.");
    } finally {
      setBusy(false);
    }
  }

  async function updateFlowCheck(mailbox: CandidateMailbox, emailsFlowing: boolean) {
    setRowBusyId(mailbox.id);
    setError(null);
    setNotice(null);
    try {
      await apiClient.updateCandidateMailboxFlowCheck(mailbox.id, {
        emails_flowing: emailsFlowing,
        last_error: emailsFlowing ? null : "No forwarded email found in the central ThinkSuccess Gmail inbox."
      });
      await loadMailboxes();
      setNotice(emailsFlowing ? `${mailbox.email} is marked as flowing.` : `${mailbox.email} is marked as not seen yet.`);
    } catch (flowError) {
      setError(flowError instanceof Error ? flowError.message : "Unable to update flow check.");
    } finally {
      setRowBusyId(null);
    }
  }

  return (
    <section className="dashboard-stack">
      <section className="panel gmail-analytics-console">
        <div className="gmail-console-header">
          <div className="section-heading">
            <h3>Central Gmail Analytics</h3>
            <p>Track candidate Gmail forwarding into {CENTRAL_INBOX} and publish the analytics sheet from the central inbox.</p>
          </div>
          <a className="secondary-button" href={REPORT_SHEET_URL} target="_blank" rel="noreferrer">
            Open Analytics Sheet
          </a>
        </div>

        {error ? <div className="error-banner">{error}</div> : null}
        {notice ? <p className="success-msg">{notice}</p> : null}

        <div className="gmail-health-grid">
          <MetricCard label="Total candidates" value={health.total} />
          <MetricCard label="Gmail linked" value={health.linked} />
          <MetricCard label="Emails flowing" value={health.flowing} tone="good" />
          <MetricCard label="Needs check" value={health.needsCheck + health.notSeen} tone={health.needsCheck + health.notSeen ? "warn" : "default"} />
          <MetricCard label="Last flow check" value={formatDate(health.lastCheck)} wide />
        </div>
      </section>

      <section className="gmail-admin-layout">
        <section className="panel">
          <div className="section-heading">
            <h3>Link Candidate Gmail</h3>
            <p>Use this after the candidate Gmail forwards all incoming mail to the central ThinkSuccess inbox.</p>
          </div>
          <div className="gmail-connect-grid">
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
              {busy ? "Saving..." : "Record forwarding setup"}
            </button>
          </div>
          <div className="gmail-forwarding-card">
            <span>Forwarding destination</span>
            <strong>{CENTRAL_INBOX}</strong>
            <p>Forward all incoming mail and keep Gmail's copy in the candidate Inbox. After a test email appears in the central inbox, use the health table to mark it as flowing.</p>
          </div>
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
          <h3>Forwarding Health</h3>
          <p>Shows whether each candidate Gmail has been linked, whether emails are flowing into ThinkSuccess, and when that check last ran.</p>
        </div>
        <div className="table-wrapper">
          <table className="gmail-health-table">
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Candidate Gmail</th>
                <th>Flow status</th>
                <th>Last email seen</th>
                <th>Last check run</th>
                <th>Issue</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ candidate, mailbox }) => {
                const status = flowStatus(mailbox);
                return (
                  <tr key={candidate.id}>
                    <td>
                      <strong>{candidate.name}</strong>
                      <span className="gmail-table-subtext">{candidate.active ? "Active" : "Inactive"}</span>
                    </td>
                    <td>{mailbox?.email ?? candidate.email ?? "Missing"}</td>
                    <td><FlowBadge status={status} /></td>
                    <td>{formatDate(mailbox?.last_email_scan_at)}</td>
                    <td>{formatDate(mailbox?.last_successful_scan_at)}</td>
                    <td>{mailbox?.last_error ?? ""}</td>
                    <td>
                      {mailbox ? (
                        <div className="gmail-table-actions">
                          <button
                            className="secondary-button"
                            onClick={() => void updateFlowCheck(mailbox, true)}
                            disabled={rowBusyId === mailbox.id}
                          >
                            Received
                          </button>
                          <button
                            className="ghost-button"
                            onClick={() => void updateFlowCheck(mailbox, false)}
                            disabled={rowBusyId === mailbox.id}
                          >
                            Not seen
                          </button>
                        </div>
                      ) : (
                        <button
                          className="secondary-button"
                          onClick={() => {
                            setSelectedCandidateId(candidate.id);
                            setTrackingEmail(candidate.email ?? "");
                          }}
                        >
                          Link
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

function FlowBadge({ status }: { status: ReturnType<typeof flowStatus> }) {
  return <span className={`flow-badge flow-${status.tone}`}>{status.label}</span>;
}

function flowStatus(mailbox?: CandidateMailbox | null) {
  if (!mailbox) return { label: "Needs setup", tone: "muted" as const };
  if (isFlowing(mailbox)) return { label: "Flowing", tone: "good" as const };
  if (mailbox.status === "forwarding_active") return { label: "Awaiting test", tone: "warn" as const };
  if (mailbox.status === "no_messages_seen") return { label: "Not seen", tone: "bad" as const };
  return { label: mailbox.status || "Unknown", tone: "muted" as const };
}

function isFlowing(mailbox?: CandidateMailbox | null) {
  return Boolean(mailbox && (mailbox.status === "flowing" || (mailbox.gmail_connected && mailbox.last_email_scan_at)));
}

function formatDate(value?: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}
