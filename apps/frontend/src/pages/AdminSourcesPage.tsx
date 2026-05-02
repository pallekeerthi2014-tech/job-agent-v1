import { useCallback, useEffect, useState } from "react";

import { apiClient } from "../api/client";
import type {
  AdapterFieldSchema,
  AdapterTypeMeta,
  IngestionRun,
  IngestionRunPage,
  Source,
  SourceHealth,
  SourceJobSample,
  SourceRunResult,
  SourceTestResult,
} from "../types";

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
}

function fmtMs(ms: number) {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

// Filter fields that go in step 3 (title filters) out of step 2 (core config)
const TITLE_FILTER_NAMES = new Set(["include_titles", "exclude_titles"]);

// ── Field renderer ───────────────────────────────────────────────────────────

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: AdapterFieldSchema;
  value: unknown;
  onChange: (val: unknown) => void;
}) {
  const strVal = value == null ? "" : String(value);

  if (field.type === "boolean") {
    return (
      <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span style={{ fontSize: "0.9rem" }}>{field.description ?? field.label}</span>
      </label>
    );
  }

  if (field.type === "string_list") {
    const listVal = Array.isArray(value) ? (value as string[]).join("\n") : strVal;
    return (
      <textarea
        rows={3}
        value={listVal}
        placeholder={field.placeholder ?? "One value per line"}
        onChange={(e) =>
          onChange(
            e.target.value
              .split("\n")
              .map((s) => s.trim())
              .filter(Boolean)
          )
        }
        style={textareaStyle}
      />
    );
  }

  if (field.type === "object") {
    return (
      <textarea
        rows={4}
        value={typeof value === "object" ? JSON.stringify(value, null, 2) : strVal}
        placeholder={field.placeholder ?? '{"key": "value"}'}
        onChange={(e) => {
          try {
            onChange(JSON.parse(e.target.value));
          } catch {
            onChange(e.target.value);
          }
        }}
        style={textareaStyle}
      />
    );
  }

  const inputType =
    field.type === "secret"
      ? "password"
      : field.type === "url"
        ? "url"
        : field.type === "number"
          ? "number"
          : "text";

  return (
    <input
      type={inputType}
      value={strVal}
      placeholder={field.placeholder ?? ""}
      required={field.required}
      onChange={(e) =>
        onChange(field.type === "number" ? (e.target.value === "" ? "" : Number(e.target.value)) : e.target.value)
      }
      style={inputStyle}
    />
  );
}

const inputStyle: React.CSSProperties = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "1px solid var(--brand-border)",
  background: "rgba(255,255,255,0.9)",
  width: "100%",
  fontSize: "0.95rem",
};

const textareaStyle: React.CSSProperties = {
  ...inputStyle,
  resize: "vertical",
  fontFamily: "inherit",
};

// ── Wizard ───────────────────────────────────────────────────────────────────

type WizardMode = "add" | "edit";

type WizardProps = {
  mode: WizardMode;
  sourceTypes: AdapterTypeMeta[];
  initialSource?: Source | null;
  onClose: () => void;
  onSaved: () => void;
};

function SourceWizard({ mode, sourceTypes, initialSource, onClose, onSaved }: WizardProps) {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(mode === "edit" ? 2 : 1);
  const [selectedType, setSelectedType] = useState<string>(initialSource?.adapter_type ?? "");
  const [sourceName, setSourceName] = useState(initialSource?.name ?? "");
  const [enabled, setEnabled] = useState(initialSource?.enabled ?? true);
  const [config, setConfig] = useState<Record<string, unknown>>(
    (initialSource?.config as Record<string, unknown>) ?? {}
  );
  const [busy, setBusy] = useState(false);
  const [testResult, setTestResult] = useState<SourceTestResult | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const meta = sourceTypes.find((t) => t.adapter_type === selectedType);
  const coreFields = meta?.fields.filter((f) => !TITLE_FILTER_NAMES.has(f.name)) ?? [];
  const filterFields = meta?.fields.filter((f) => TITLE_FILTER_NAMES.has(f.name)) ?? [];

  function setField(name: string, val: unknown) {
    setConfig((prev) => ({ ...prev, [name]: val }));
  }

  async function handleTest() {
    if (!meta) return;
    setBusy(true);
    setSaveError(null);
    setTestResult(null);
    try {
      const result = await apiClient.testSourceConfig(selectedType, config);
      setTestResult(result);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Test failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSave() {
    setBusy(true);
    setSaveError(null);
    try {
      if (mode === "add") {
        await apiClient.createSource({ name: sourceName, adapter_type: selectedType, config, enabled });
      } else if (initialSource) {
        await apiClient.updateSource(initialSource.id, { name: sourceName, config, enabled });
      }
      onSaved();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <div>
            <p className="eyebrow" style={{ marginBottom: 2 }}>
              {mode === "add" ? "Add Source" : `Edit — ${initialSource?.name}`}
            </p>
            <h3 style={{ margin: 0, fontSize: "1.15rem" }}>
              {step === 1
                ? "Choose adapter type"
                : step === 2
                  ? "Configure connection"
                  : step === 3
                    ? "Title filters"
                    : "Test & save"}
            </h3>
          </div>
          <button onClick={onClose} style={closeBtnStyle}>✕</button>
        </div>

        {/* Step 1 — Pick adapter type */}
        {step === 1 && (
          <div>
            <div style={{ display: "grid", gap: 10, marginBottom: 20 }}>
              {sourceTypes.map((t) => (
                <label
                  key={t.adapter_type}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 12,
                    padding: "14px 16px",
                    borderRadius: 14,
                    border: `2px solid ${selectedType === t.adapter_type ? "var(--brand-green)" : "var(--brand-border)"}`,
                    background: selectedType === t.adapter_type ? "var(--brand-green-soft)" : "rgba(255,255,255,0.9)",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="radio"
                    name="adapter_type"
                    value={t.adapter_type}
                    checked={selectedType === t.adapter_type}
                    onChange={() => setSelectedType(t.adapter_type)}
                    style={{ marginTop: 3 }}
                  />
                  <div>
                    <strong style={{ fontSize: "0.95rem" }}>{t.label}</strong>
                    <span
                      style={{
                        marginLeft: 8,
                        fontSize: "0.72rem",
                        padding: "2px 7px",
                        borderRadius: 8,
                        background: "var(--brand-green-soft)",
                        color: "var(--brand-green-dark)",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.1em",
                      }}
                    >
                      {t.category}
                    </span>
                    <p style={{ margin: "4px 0 0", fontSize: "0.85rem", color: "var(--brand-muted)" }}>{t.description}</p>
                  </div>
                </label>
              ))}
            </div>
            <div style={footerStyle}>
              <button onClick={onClose} style={secondaryBtnStyle}>Cancel</button>
              <button
                className="primary-button"
                disabled={!selectedType}
                onClick={() => setStep(2)}
              >
                Next →
              </button>
            </div>
          </div>
        )}

        {/* Step 2 — Core config fields */}
        {step === 2 && meta && (
          <div>
            <div style={{ display: "grid", gap: 14, marginBottom: 20 }}>
              <div style={fieldGroupStyle}>
                <label style={labelStyle}>Source name *</label>
                <input
                  type="text"
                  value={sourceName}
                  placeholder={`e.g. ${meta.label}`}
                  required
                  onChange={(e) => setSourceName(e.target.value)}
                  style={inputStyle}
                />
                <small style={{ color: "var(--brand-muted)" }}>Unique display name for this feed.</small>
              </div>

              {coreFields.map((field) => (
                <div key={field.name} style={fieldGroupStyle}>
                  <label style={labelStyle}>
                    {field.label}
                    {field.required ? " *" : ""}
                  </label>
                  <FieldInput
                    field={field}
                    value={config[field.name] ?? field.default ?? ""}
                    onChange={(val) => setField(field.name, val)}
                  />
                  {field.description && field.type !== "boolean" && (
                    <small style={{ color: "var(--brand-muted)" }}>{field.description}</small>
                  )}
                </div>
              ))}

              <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={(e) => setEnabled(e.target.checked)}
                />
                <span style={{ fontSize: "0.95rem", fontWeight: 600 }}>Enabled</span>
                <small style={{ color: "var(--brand-muted)" }}>Uncheck to save but skip in scheduled runs.</small>
              </label>
            </div>

            <div style={footerStyle}>
              {mode === "add" ? (
                <button onClick={() => setStep(1)} style={secondaryBtnStyle}>← Back</button>
              ) : (
                <button onClick={onClose} style={secondaryBtnStyle}>Cancel</button>
              )}
              <button
                className="primary-button"
                disabled={!sourceName.trim()}
                onClick={() => setStep(3)}
              >
                Next →
              </button>
            </div>
          </div>
        )}

        {/* Step 3 — Title filters */}
        {step === 3 && (
          <div>
            <p style={{ margin: "0 0 16px", color: "var(--brand-muted)", fontSize: "0.9rem" }}>
              Control which job titles are ingested. Leave both lists empty to use the adapter's built-in defaults.
            </p>
            <div style={{ display: "grid", gap: 14, marginBottom: 20 }}>
              {filterFields.length === 0 ? (
                <p style={{ color: "var(--brand-muted)" }}>This adapter has no title filters.</p>
              ) : (
                filterFields.map((field) => (
                  <div key={field.name} style={fieldGroupStyle}>
                    <label style={labelStyle}>{field.label}</label>
                    <FieldInput
                      field={field}
                      value={config[field.name] ?? []}
                      onChange={(val) => setField(field.name, val)}
                    />
                    {field.description && (
                      <small style={{ color: "var(--brand-muted)" }}>{field.description}</small>
                    )}
                  </div>
                ))
              )}
            </div>

            <div style={footerStyle}>
              <button onClick={() => setStep(2)} style={secondaryBtnStyle}>← Back</button>
              <button className="primary-button" onClick={() => setStep(4)}>
                Next →
              </button>
            </div>
          </div>
        )}

        {/* Step 4 — Test & save */}
        {step === 4 && (
          <div>
            <p style={{ margin: "0 0 16px", color: "var(--brand-muted)", fontSize: "0.9rem" }}>
              Run a dry-run against the live source to verify the connection before saving. You can skip and save directly.
            </p>

            {saveError && <div className="error-banner" style={{ marginBottom: 12 }}>{saveError}</div>}

            {testResult && (
              <div style={testResultBoxStyle}>
                {testResult.success ? (
                  <>
                    <p style={{ margin: "0 0 8px", fontWeight: 700, color: "var(--brand-green)" }}>
                      ✅ Connection OK — {testResult.raw_jobs_returned} jobs returned in {fmtMs(testResult.duration_ms)}
                    </p>
                    {testResult.sample_jobs.length > 0 && (
                      <div style={{ display: "grid", gap: 6 }}>
                        {testResult.sample_jobs.slice(0, 5).map((j, i) => (
                          <SampleJobRow key={i} job={j} />
                        ))}
                        {testResult.raw_jobs_returned > 5 && (
                          <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--brand-muted)" }}>
                            …and {testResult.raw_jobs_returned - 5} more
                          </p>
                        )}
                      </div>
                    )}
                  </>
                ) : (
                  <p style={{ margin: 0, fontWeight: 700, color: "#8a2b1f" }}>
                    ❌ {testResult.error ?? "Connection failed"}
                  </p>
                )}
              </div>
            )}

            <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
              <button
                className="secondary-button"
                disabled={busy}
                onClick={() => void handleTest()}
                style={{ flex: 1 }}
              >
                {busy ? "Testing…" : "🔌 Test Connection"}
              </button>
            </div>

            <div style={footerStyle}>
              <button onClick={() => setStep(3)} style={secondaryBtnStyle}>← Back</button>
              <button
                className="primary-button"
                disabled={busy}
                onClick={() => void handleSave()}
              >
                {busy ? "Saving…" : "💾 Save Source"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function SampleJobRow({ job }: { job: SourceJobSample }) {
  return (
    <div
      style={{
        padding: "8px 12px",
        borderRadius: 10,
        background: "rgba(0,122,61,0.04)",
        border: "1px solid var(--brand-border)",
        fontSize: "0.85rem",
      }}
    >
      <strong>{job.title}</strong>
      {job.company ? <span style={{ color: "var(--brand-muted)", marginLeft: 6 }}>@ {job.company}</span> : null}
      {job.location ? <span style={{ color: "var(--brand-muted)", marginLeft: 6 }}>· {job.location}</span> : null}
    </div>
  );
}

// ── Shared modal styles ───────────────────────────────────────────────────────

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(16,19,20,0.45)",
  zIndex: 100,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 20,
};

const modalStyle: React.CSSProperties = {
  background: "var(--brand-surface)",
  borderRadius: 24,
  padding: 28,
  width: "100%",
  maxWidth: 560,
  maxHeight: "90vh",
  overflowY: "auto",
  boxShadow: "0 32px 80px rgba(7,58,35,0.18)",
  border: "1px solid var(--brand-border)",
};

const closeBtnStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  fontSize: "1.2rem",
  cursor: "pointer",
  color: "var(--brand-muted)",
  padding: "4px 8px",
};

const footerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "flex-end",
  gap: 10,
  marginTop: 4,
};

const secondaryBtnStyle: React.CSSProperties = {
  padding: "10px 20px",
  borderRadius: 12,
  border: "1px solid var(--brand-border)",
  background: "white",
  cursor: "pointer",
  fontSize: "0.9rem",
};

const fieldGroupStyle: React.CSSProperties = { display: "grid", gap: 6 };
const labelStyle: React.CSSProperties = { fontWeight: 600, fontSize: "0.9rem" };

const testResultBoxStyle: React.CSSProperties = {
  padding: "14px 16px",
  borderRadius: 14,
  background: "rgba(255,255,255,0.8)",
  border: "1px solid var(--brand-border)",
  marginBottom: 16,
};

// ── Status pill ───────────────────────────────────────────────────────────────

function StatusPill({ source }: { source: Source }) {
  if (!source.enabled) {
    return (
      <span className="queue-status-pill queue-status-skipped">Paused</span>
    );
  }
  if (source.last_error) {
    return <span className="queue-status-pill" style={{ background: "#fff0ee", color: "#8a2b1f", border: "1px solid #f1c3bb" }}>Error</span>;
  }
  if (source.last_run_at) {
    return <span className="queue-status-pill queue-status-pending">Active</span>;
  }
  return <span className="queue-status-pill" style={{ background: "#f5f5f5", color: "#666" }}>New</span>;
}

// ── Health pill (Phase 7) ─────────────────────────────────────────────────────

function HealthPill({ status }: { status: SourceHealth["health_status"] }) {
  const styles: Record<string, React.CSSProperties> = {
    healthy:  { background: "var(--brand-green-soft)", color: "var(--brand-green-dark)", border: "1px solid rgba(0,122,61,0.25)" },
    warning:  { background: "#fff8e1", color: "#7a5c00", border: "1px solid #ffe082" },
    critical: { background: "#fff0ee", color: "#8a2b1f", border: "1px solid #f1c3bb" },
    paused:   { background: "#f5f5f5", color: "#666",    border: "1px solid #ddd" },
  };
  const labels = { healthy: "✅ Healthy", warning: "⚠️ Warning", critical: "🔴 Critical", paused: "⏸ Paused" };
  return (
    <span style={{ ...styles[status], padding: "3px 10px", borderRadius: 20, fontSize: "0.75rem", fontWeight: 600, whiteSpace: "nowrap" }}>
      {labels[status]}
    </span>
  );
}

// ── Run history drawer (Phase 7) ──────────────────────────────────────────────

function RunHistoryDrawer({ sourceId, sourceName, onClose }: { sourceId: number; sourceName: string; onClose: () => void }) {
  const [page, setPage] = useState<IngestionRunPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const limit = 10;

  useEffect(() => {
    setLoading(true);
    apiClient.listSourceRuns(sourceId, { limit, offset })
      .then(setPage)
      .catch(() => setPage(null))
      .finally(() => setLoading(false));
  }, [sourceId, offset]);

  return (
    <div style={overlayStyle}>
      <div style={{ ...modalStyle, maxWidth: 680 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
          <div>
            <p className="eyebrow" style={{ marginBottom: 2 }}>Run History</p>
            <h3 style={{ margin: 0, fontSize: "1.1rem" }}>{sourceName}</h3>
          </div>
          <button onClick={onClose} style={closeBtnStyle}>✕</button>
        </div>

        {loading ? (
          <p style={{ color: "var(--brand-muted)" }}>Loading…</p>
        ) : !page || page.items.length === 0 ? (
          <p style={{ color: "var(--brand-muted)" }}>No runs recorded yet. Runs are tracked from the next pipeline cycle onward.</p>
        ) : (
          <>
            <div className="table-wrap" style={{ maxHeight: 420, overflowY: "auto" }}>
              <table>
                <thead>
                  <tr>
                    <th>Started</th>
                    <th>Status</th>
                    <th style={{ textAlign: "right" }}>Fetched</th>
                    <th style={{ textAlign: "right" }}>Stored</th>
                    <th style={{ textAlign: "right" }}>Skipped</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {page.items.map((run: IngestionRun) => (
                    <tr key={run.id}>
                      <td style={{ fontSize: "0.8rem", whiteSpace: "nowrap" }}>{fmtDate(run.started_at)}</td>
                      <td>
                        <span style={{
                          padding: "2px 8px", borderRadius: 12, fontSize: "0.75rem", fontWeight: 600,
                          background: run.status === "success" ? "var(--brand-green-soft)" : "#fff0ee",
                          color: run.status === "success" ? "var(--brand-green-dark)" : "#8a2b1f",
                          border: run.status === "success" ? "1px solid rgba(0,122,61,0.25)" : "1px solid #f1c3bb",
                        }}>
                          {run.status === "success" ? "✅ OK" : "❌ Error"}
                        </span>
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{run.raw_fetched}</td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{run.raw_stored}</td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{run.jobs_skipped}</td>
                      <td style={{ fontSize: "0.75rem", color: "#8a2b1f", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                          title={run.error_message ?? undefined}>
                        {run.error_message ? run.error_message.slice(0, 50) + (run.error_message.length > 50 ? "…" : "") : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12, fontSize: "0.85rem", color: "var(--brand-muted)" }}>
              <span>{page.total} total runs</span>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="secondary-button" style={{ padding: "4px 10px", fontSize: "0.8rem" }} disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>← Prev</button>
                <button className="secondary-button" style={{ padding: "4px 10px", fontSize: "0.8rem" }} disabled={offset + limit >= page.total} onClick={() => setOffset(offset + limit)}>Next →</button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ── Run result toast ──────────────────────────────────────────────────────────

function RunResultBanner({ result, onClose }: { result: SourceRunResult; onClose: () => void }) {
  return (
    <div
      style={{
        padding: "14px 18px",
        borderRadius: 16,
        background: result.success ? "var(--brand-green-soft)" : "#fff3f1",
        border: `1px solid ${result.success ? "rgba(0,122,61,0.2)" : "#f1c3bb"}`,
        color: result.success ? "var(--brand-green-dark)" : "#8a2b1f",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: 12,
      }}
    >
      <div>
        <strong>
          {result.success ? "✅" : "❌"} Run Now — {result.source_name}
        </strong>
        {result.success ? (
          <p style={{ margin: "4px 0 0", fontSize: "0.85rem" }}>
            {result.raw_jobs_stored} jobs stored · {result.jobs_skipped_irrelevant} skipped · {fmtMs(result.duration_ms)}
          </p>
        ) : (
          <p style={{ margin: "4px 0 0", fontSize: "0.85rem" }}>{result.error}</p>
        )}
      </div>
      <button onClick={onClose} style={{ ...closeBtnStyle, fontSize: "1rem" }}>✕</button>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function AdminSourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [sourceTypes, setSourceTypes] = useState<AdapterTypeMeta[]>([]);
  const [healthMap, setHealthMap] = useState<Map<number, SourceHealth>>(new Map());
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [wizardOpen, setWizardOpen] = useState(false);
  const [editingSource, setEditingSource] = useState<Source | null>(null);

  const [busySourceId, setBusySourceId] = useState<number | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [runResult, setRunResult] = useState<SourceRunResult | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Phase 7: run history drawer
  const [historySource, setHistorySource] = useState<Source | null>(null);

  // Sort controls
  type SortField = "name" | "type" | "health" | "last_run";
  const [sortBy, setSortBy] = useState<SortField>("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  // Run All
  const [runAllBusy, setRunAllBusy] = useState(false);
  const [runAllResults, setRunAllResults] = useState<SourceRunResult[]>([]);

  const loadAll = useCallback(async () => {
    setLoadError(null);
    try {
      const [typesResp, sourcesResp, healthResp] = await Promise.all([
        apiClient.listSourceTypes(),
        apiClient.listSources(),
        apiClient.getSourcesHealth().catch(() => [] as SourceHealth[]),
      ]);
      setSourceTypes(typesResp.types);
      setSources(sourcesResp);
      setHealthMap(new Map(healthResp.map((h) => [h.source_id, h])));
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load sources");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadAll(); }, [loadAll]);

  async function handleToggleEnabled(source: Source) {
    setBusySourceId(source.id);
    setActionError(null);
    try {
      await apiClient.updateSource(source.id, { enabled: !source.enabled });
      await loadAll();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusySourceId(null);
    }
  }

  async function handleDelete(id: number) {
    setBusySourceId(id);
    setActionError(null);
    try {
      await apiClient.deleteSource(id);
      setDeleteConfirmId(null);
      await loadAll();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusySourceId(null);
    }
  }

  function toggleSort(field: SortField) {
    if (sortBy === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortDir("asc");
    }
  }

  const healthOrder: Record<SourceHealth["health_status"], number> = { healthy: 0, warning: 1, critical: 2, paused: 3 };

  const sortedSources = [...sources].sort((a, b) => {
    let cmp = 0;
    if (sortBy === "name") cmp = a.name.localeCompare(b.name);
    else if (sortBy === "type") cmp = a.adapter_type.localeCompare(b.adapter_type);
    else if (sortBy === "health") {
      const ha = healthMap.get(a.id)?.health_status ?? "paused";
      const hb = healthMap.get(b.id)?.health_status ?? "paused";
      cmp = healthOrder[ha] - healthOrder[hb];
    } else if (sortBy === "last_run") {
      const da = a.last_run_at ? new Date(a.last_run_at).getTime() : 0;
      const db = b.last_run_at ? new Date(b.last_run_at).getTime() : 0;
      cmp = da - db;
    }
    return sortDir === "asc" ? cmp : -cmp;
  });

  async function handleRunAll() {
    const enabled = sources.filter((s) => s.enabled);
    if (enabled.length === 0) return;
    setRunAllBusy(true);
    setActionError(null);
    setRunAllResults([]);
    const results: SourceRunResult[] = [];
    for (const source of enabled) {
      try {
        const r = await apiClient.runSourceNow(source.id);
        results.push(r);
      } catch {
        results.push({
          source_id: source.id,
          source_name: source.name,
          success: false,
          raw_jobs_stored: 0,
          jobs_skipped_irrelevant: 0,
          error: "Request failed",
          duration_ms: 0,
        });
      }
    }
    setRunAllResults(results);
    setRunAllBusy(false);
    await loadAll();
  }

  async function handleRunNow(source: Source) {
    setBusySourceId(source.id);
    setActionError(null);
    setRunResult(null);
    try {
      const result = await apiClient.runSourceNow(source.id);
      setRunResult(result);
      await loadAll();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Run failed");
    } finally {
      setBusySourceId(null);
    }
  }

  function openAdd() {
    setEditingSource(null);
    setWizardOpen(true);
  }

  function openEdit(source: Source) {
    setEditingSource(source);
    setWizardOpen(true);
  }

  function closeWizard() {
    setWizardOpen(false);
    setEditingSource(null);
  }

  async function onWizardSaved() {
    closeWizard();
    await loadAll();
  }

  const typeLabel = (adapterType: string) =>
    sourceTypes.find((t) => t.adapter_type === adapterType)?.label ?? adapterType;

  return (
    <section className="dashboard-stack">
      {/* ── Header panel ────────────────────────────────────────────────────── */}
      <section className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div className="section-heading" style={{ margin: 0 }}>
            <h3>Job Sources</h3>
            <p>Manage the external feeds that the daily pipeline ingests. Runs automatically at 6 AM UTC.</p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="secondary-button"
              onClick={() => void handleRunAll()}
              disabled={runAllBusy || sources.filter((s) => s.enabled).length === 0}
              title="Run all enabled sources now"
            >
              {runAllBusy ? "⏳ Running All…" : "▶▶ Run All"}
            </button>
            <button className="primary-button" onClick={openAdd}>
              + Add Source
            </button>
          </div>
        </div>

        {actionError && (
          <div className="error-banner" style={{ marginTop: 12 }}>{actionError}</div>
        )}
        {runResult && (
          <div style={{ marginTop: 12 }}>
            <RunResultBanner result={runResult} onClose={() => setRunResult(null)} />
          </div>
        )}
        {runAllResults.length > 0 && (
          <div style={{ marginTop: 12, padding: "14px 18px", borderRadius: 14, background: "rgba(255,255,255,0.8)", border: "1px solid var(--brand-border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <strong style={{ fontSize: "0.9rem" }}>▶▶ Run All Results</strong>
              <button onClick={() => setRunAllResults([])} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--brand-muted)", fontSize: "1rem" }}>✕</button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {runAllResults.map((r) => (
                <div key={r.source_id} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: "0.85rem" }}>
                  <span>{r.success ? "✅" : "❌"}</span>
                  <span style={{ fontWeight: 600, minWidth: 140 }}>{r.source_name}</span>
                  {r.success
                    ? <span style={{ color: "var(--brand-muted)" }}>{r.raw_jobs_stored} stored · {r.jobs_skipped_irrelevant} skipped · {fmtMs(r.duration_ms)}</span>
                    : <span style={{ color: "#8a2b1f" }}>{r.error}</span>
                  }
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* ── Health summary (Phase 7) ─────────────────────────────────────────── */}
      {healthMap.size > 0 && (() => {
        const healths = Array.from(healthMap.values()).filter(h => h.enabled);
        const counts = { healthy: 0, warning: 0, critical: 0 };
        healths.forEach(h => { if (h.health_status in counts) counts[h.health_status as keyof typeof counts]++; });
        return (
          <section className="panel" style={{ padding: "14px 20px" }}>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
              <span style={{ fontSize: "0.85rem", color: "var(--brand-muted)", marginRight: 4 }}>Source health:</span>
              {counts.healthy > 0 && <span style={{ background: "var(--brand-green-soft)", color: "var(--brand-green-dark)", border: "1px solid rgba(0,122,61,0.25)", padding: "4px 12px", borderRadius: 20, fontSize: "0.8rem", fontWeight: 600 }}>✅ {counts.healthy} healthy</span>}
              {counts.warning > 0 && <span style={{ background: "#fff8e1", color: "#7a5c00", border: "1px solid #ffe082", padding: "4px 12px", borderRadius: 20, fontSize: "0.8rem", fontWeight: 600 }}>⚠️ {counts.warning} warning</span>}
              {counts.critical > 0 && <span style={{ background: "#fff0ee", color: "#8a2b1f", border: "1px solid #f1c3bb", padding: "4px 12px", borderRadius: 20, fontSize: "0.8rem", fontWeight: 600 }}>🔴 {counts.critical} critical</span>}
            </div>
          </section>
        );
      })()}

      {/* ── Sources table ────────────────────────────────────────────────────── */}
      <section className="panel">
        {loading ? (
          <p style={{ color: "var(--brand-muted)" }}>Loading sources…</p>
        ) : loadError ? (
          <div className="error-banner">{loadError}</div>
        ) : sources.length === 0 ? (
          <div className="empty-state">
            <p>No sources configured yet. Click <strong>+ Add Source</strong> to add the first feed.</p>
          </div>
        ) : (
          <>
            {/* Sort controls */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
              <span style={{ fontSize: "0.8rem", color: "var(--brand-muted)", marginRight: 4 }}>Sort by:</span>
              {(["name", "type", "health", "last_run"] as const).map((field) => {
                const labels = { name: "Name", type: "Type", health: "Health", last_run: "Last Run" };
                const active = sortBy === field;
                return (
                  <button
                    key={field}
                    onClick={() => toggleSort(field)}
                    style={{
                      padding: "4px 12px",
                      borderRadius: 20,
                      border: "1px solid var(--brand-border)",
                      background: active ? "var(--brand-green-soft)" : "white",
                      color: active ? "var(--brand-green-dark)" : "var(--brand-muted)",
                      fontWeight: active ? 700 : 400,
                      fontSize: "0.8rem",
                      cursor: "pointer",
                    }}
                  >
                    {labels[field]} {active ? (sortDir === "asc" ? "↑" : "↓") : ""}
                  </button>
                );
              })}
            </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Health</th>
                  <th>Last Run</th>
                  <th style={{ textAlign: "right" }}>Total</th>
                  <th style={{ textAlign: "right" }}>24h</th>
                  <th>Last Error</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedSources.map((source) => {
                  const busy = busySourceId === source.id;
                  return (
                    <tr key={source.id}>
                      <td>
                        <strong style={{ fontSize: "0.92rem" }}>{source.name}</strong>
                      </td>
                      <td>
                        <span style={{ fontSize: "0.82rem", color: "var(--brand-muted)" }}>
                          {typeLabel(source.adapter_type)}
                        </span>
                      </td>
                      <td>
                        <button
                          onClick={() => void handleToggleEnabled(source)}
                          disabled={busy}
                          style={{
                            background: "none",
                            border: "none",
                            cursor: busy ? "default" : "pointer",
                            padding: 0,
                          }}
                          title={source.enabled ? "Click to pause" : "Click to enable"}
                        >
                          <StatusPill source={source} />
                        </button>
                      </td>
                      <td>
                        {healthMap.has(source.id)
                          ? <HealthPill status={healthMap.get(source.id)!.health_status} />
                          : <span style={{ fontSize: "0.78rem", color: "var(--brand-muted)" }}>—</span>
                        }
                      </td>
                      <td style={{ fontSize: "0.82rem", color: "var(--brand-muted)" }}>
                        {fmtDate(source.last_run_at)}
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {source.jobs_total ?? "—"}
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {source.jobs_last_24h ?? "—"}
                      </td>
                      <td
                        style={{
                          fontSize: "0.78rem",
                          color: "#8a2b1f",
                          maxWidth: 180,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                        title={source.last_error ?? undefined}
                      >
                        {source.last_error ? source.last_error.slice(0, 60) + (source.last_error.length > 60 ? "…" : "") : "—"}
                      </td>
                      <td>
                        <div style={{ display: "flex", gap: 6, flexWrap: "nowrap" }}>
                          <button
                            className="secondary-button"
                            style={{ padding: "6px 10px", fontSize: "0.8rem" }}
                            disabled={busy}
                            onClick={() => openEdit(source)}
                          >
                            Edit
                          </button>
                          <button
                            className="secondary-button"
                            style={{ padding: "6px 10px", fontSize: "0.8rem" }}
                            disabled={busy}
                            onClick={() => void handleRunNow(source)}
                          >
                            {busy ? "…" : "▶ Run"}
                          </button>
                          <button
                            className="secondary-button"
                            style={{ padding: "6px 10px", fontSize: "0.8rem" }}
                            onClick={() => setHistorySource(source)}
                          >
                            History
                          </button>
                          {deleteConfirmId === source.id ? (
                            <>
                              <button
                                className="danger-button"
                                style={{ padding: "6px 10px", fontSize: "0.8rem" }}
                                disabled={busy}
                                onClick={() => void handleDelete(source.id)}
                              >
                                Confirm
                              </button>
                              <button
                                className="secondary-button"
                                style={{ padding: "6px 10px", fontSize: "0.8rem" }}
                                onClick={() => setDeleteConfirmId(null)}
                              >
                                Cancel
                              </button>
                            </>
                          ) : (
                            <button
                              className="danger-button"
                              style={{ padding: "6px 10px", fontSize: "0.8rem" }}
                              disabled={busy}
                              onClick={() => setDeleteConfirmId(source.id)}
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          </>
        )}
      </section>

      {/* ── Wizard modal ─────────────────────────────────────────────────────── */}
      {wizardOpen && (
        <SourceWizard
          mode={editingSource ? "edit" : "add"}
          sourceTypes={sourceTypes}
          initialSource={editingSource}
          onClose={closeWizard}
          onSaved={() => void onWizardSaved()}
        />
      )}

      {/* ── Run history drawer (Phase 7) ─────────────────────────────────────── */}
      {historySource && (
        <RunHistoryDrawer
          sourceId={historySource.id}
          sourceName={historySource.name}
          onClose={() => setHistorySource(null)}
        />
      )}
    </section>
  );
}
