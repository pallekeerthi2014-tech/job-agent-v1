import { type CSSProperties, useCallback, useEffect, useState } from "react";
import { apiClient } from "../api/client";
import type {
  AdapterFieldSchema,
  AdapterTypeMeta,
  AdapterTypeList,
  SourceCreate,
  SourceRead,
  SourceRunResult,
  SourceTestRequest,
  SourceTestResult,
  SourceUpdate,
} from "../types";

// ââ helpers ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

function fmtDate(dt: string | null): string {
  if (!dt) return "â";
  return new Date(dt).toLocaleString();
}

function adapterLabel(type: string, types: AdapterTypeMeta[]): string {
  return types.find((t) => t.adapter_type === type)?.label ?? type;
}

function btnStyle(color: string): CSSProperties {
  return {
    background: color, color: "#fff", border: "none",
    borderRadius: 6, padding: "4px 10px", cursor: "pointer", fontSize: 12,
    opacity: 1,
  };
}

// ââ result banners ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

function TestResultBanner({
  result, onClose,
}: {
  result: SourceTestResult;
  onClose: () => void;
}) {
  return (
    <div style={{
      background: result.success ? "#f0fdf4" : "#fef2f2",
      border: `1px solid ${result.success ? "#86efac" : "#fca5a5"}`,
      borderRadius: 8, padding: "12px 16px", marginBottom: 16,
      display: "flex", justifyContent: "space-between", alignItems: "flex-start",
    }}>
      <div>
        <strong>{result.success ? "â Connection successful" : "â Connection failed"}</strong>
        {" Â· "}{result.duration_seconds.toFixed(2)}s
        {result.error && <div style={{ color: "#ef4444", marginTop: 4 }}>{result.error}</div>}
        {result.success && result.samples.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              {result.jobs_found} jobs found Â· Sample:
            </div>
            {result.samples.map((s, i) => (
              <div key={i} style={{ fontSize: 12, color: "#555", marginBottom: 2 }}>
                â¢ {s.title} â {s.company}{s.location ? ` (${s.location})` : ""}
              </div>
            ))}
          </div>
        )}
      </div>
      <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 16 }}>â</button>
    </div>
  );
}

function RunResultBanner({
  result, onClose,
}: {
  result: SourceRunResult;
  onClose: () => void;
}) {
  const ok = !result.error;
  return (
    <div style={{
      background: ok ? "#f0fdf4" : "#fef2f2",
      border: `1px solid ${ok ? "#86efac" : "#fca5a5"}`,
      borderRadius: 8, padding: "12px 16px", marginBottom: 16,
      display: "flex", justifyContent: "space-between", alignItems: "flex-start",
    }}>
      <div>
        <strong>{ok ? "â Run complete" : "â Run failed"}</strong>
        {" â "}<em>{result.source_name}</em>{" Â· "}{result.duration_seconds.toFixed(2)}s
        {ok && (
          <span style={{ marginLeft: 8 }}>
            {result.jobs_stored} new jobs stored ({result.jobs_fetched} fetched)
          </span>
        )}
        {result.error && <div style={{ color: "#ef4444", marginTop: 4 }}>{result.error}</div>}
      </div>
      <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 16 }}>â</button>
    </div>
  );
}

// ââ source table ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

const TH: CSSProperties = {
  padding: "10px 14px", textAlign: "left", fontWeight: 600,
  fontSize: 13, color: "#555", borderBottom: "2px solid #e5e7eb",
};
const TD: CSSProperties = {
  padding: "10px 14px", fontSize: 13,
  borderBottom: "1px solid #f3f4f6", verticalAlign: "middle",
};

function SourceTable({
  sources, adapterTypes, actionBusy, onEdit, onToggle, onDelete, onTest, onRunNow,
}: {
  sources: SourceRead[];
  adapterTypes: AdapterTypeMeta[];
  actionBusy: number | null;
  onEdit: (s: SourceRead) => void;
  onToggle: (s: SourceRead) => void;
  onDelete: (s: SourceRead) => void;
  onTest: (s: SourceRead) => void;
  onRunNow: (s: SourceRead) => void;
}) {
  if (sources.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: 60, color: "#888" }}>
        No sources configured yet. Click <strong>+ Add Source</strong> to get started.
      </div>
    );
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{
        width: "100%", borderCollapse: "collapse", background: "#fff",
        borderRadius: 8, overflow: "hidden", boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
      }}>
        <thead style={{ background: "#f9fafb" }}>
          <tr>
            {["Name","Adapter","Enabled","Last Run","Total","24h","7d","Status","Actions"].map(h => (
              <th key={h} style={TH}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sources.map((src) => {
            const busy = actionBusy === src.id;
            return (
              <tr key={src.id} style={{ opacity: busy ? 0.6 : 1 }}>
                <td style={{ ...TD, fontWeight: 600 }}>{src.name}</td>
                <td style={TD}>
                  <span style={{
                    background: "#e0e7ff", color: "#3730a3",
                    padding: "2px 8px", borderRadius: 12, fontSize: 11,
                  }}>
                    {adapterLabel(src.adapter_type, adapterTypes)}
                  </span>
                </td>
                <td style={TD}>
                  <button
                    onClick={() => onToggle(src)}
                    style={{
                      background: src.enabled ? "#22c55e" : "#d1d5db",
                      color: "#fff", border: "none", borderRadius: 12,
                      padding: "3px 10px", cursor: "pointer", fontSize: 12,
                    }}
                  >
                    {src.enabled ? "On" : "Off"}
                  </button>
                </td>
                <td style={{ ...TD, color: "#888", fontSize: 12 }}>{fmtDate(src.last_run_at)}</td>
                <td style={{ ...TD, textAlign: "center" }}>{src.jobs_total}</td>
                <td style={{ ...TD, textAlign: "center" }}>{src.jobs_last_24h}</td>
                <td style={{ ...TD, textAlign: "center" }}>{src.jobs_last_7d}</td>
                <td style={TD}>
                  {src.last_error ? (
                    <span title={src.last_error} style={{ color: "#ef4444", fontSize: 11 }}>â  Error</span>
                  ) : (
                    <span style={{ color: "#22c55e", fontSize: 11 }}>â OK</span>
                  )}
                </td>
                <td style={TD}>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <button onClick={() => onEdit(src)} disabled={busy} style={btnStyle("#3b82f6")}>Edit</button>
                    <button onClick={() => onTest(src)} disabled={busy} style={btnStyle("#8b5cf6")}>{busy ? "â¦" : "Test"}</button>
                    <button onClick={() => onRunNow(src)} disabled={busy} style={btnStyle("#f59e0b")}>{busy ? "â¦" : "Run Now"}</button>
                    <button onClick={() => onDelete(src)} disabled={busy} style={btnStyle("#ef4444")}>Delete</button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ââ field input âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

const INPUT_STYLE: CSSProperties = {
  width: "100%", padding: "8px 12px", border: "1px solid #d1d5db",
  borderRadius: 6, fontSize: 13, boxSizing: "border-box",
};

function FieldInput({
  field, value, onChange,
}: {
  field: AdapterFieldSchema;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const label = (
    <label style={{ display: "block", fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
      {field.label}
      {field.required && <span style={{ color: "#ef4444" }}> *</span>}
      {field.description && (
        <span style={{ fontWeight: 400, color: "#888", marginLeft: 6, fontSize: 12 }}>
          {field.description}
        </span>
      )}
    </label>
  );

  if (field.field_type === "boolean") {
    return (
      <div style={{ marginBottom: 14, display: "flex", alignItems: "center", gap: 8 }}>
        <input
          type="checkbox"
          checked={Boolean(value ?? field.default_value ?? false)}
          onChange={(e) => onChange(e.target.checked)}
        />
        {label}
      </div>
    );
  }

  if (field.field_type === "string_list") {
    const arr = Array.isArray(value) ? (value as string[]).join(", ") : String(value ?? "");
    return (
      <div style={{ marginBottom: 14 }}>
        {label}
        <input
          style={INPUT_STYLE}
          value={arr}
          placeholder={field.placeholder ?? "comma-separated values"}
          onChange={(e) =>
            onChange(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))
          }
        />
      </div>
    );
  }

  if (field.field_type === "number") {
    return (
      <div style={{ marginBottom: 14 }}>
        {label}
        <input
          type="number"
          style={INPUT_STYLE}
          value={String(value ?? field.default_value ?? "")}
          placeholder={field.placeholder}
          onChange={(e) => onChange(Number(e.target.value))}
        />
      </div>
    );
  }

  if (field.options && field.options.length > 0) {
    return (
      <div style={{ marginBottom: 14 }}>
        {label}
        <select
          style={INPUT_STYLE}
          value={String(value ?? field.default_value ?? "")}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">â select â</option>
          {field.options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      </div>
    );
  }

  return (
    <div style={{ marginBottom: 14 }}>
      {label}
      <input
        type={field.field_type === "secret" ? "password" : "text"}
        style={INPUT_STYLE}
        value={String(value ?? field.default_value ?? "")}
        placeholder={field.placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

// ââ add/edit modal ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

type WizardStep = 1 | 2 | 3;

function SourceModal({
  source, adapterTypes, onClose, onSaved,
}: {
  source: SourceRead | null;
  adapterTypes: AdapterTypeMeta[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = !!source;
  const [step, setStep] = useState<WizardStep>(isEdit ? 2 : 1);
  const [adapterType, setAdapterType] = useState(source?.adapter_type ?? "");
  const [name, setName] = useState(source?.name ?? "");
  const [config, setConfig] = useState<Record<string, unknown>>(
    source?.config ?? {}
  );
  const [enabled, setEnabled] = useState(source?.enabled ?? true);
  const [busy, setBusy] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<SourceTestResult | null>(null);

  const selectedMeta = adapterTypes.find((t) => t.adapter_type === adapterType);

  const handleFieldChange = (fieldName: string, val: unknown) =>
    setConfig((prev) => ({ ...prev, [fieldName]: val }));

  const handleTest = () => {
    if (!adapterType) return;
    setBusy(true);
    setTestResult(null);
    apiClient
      .testSourceConfig({ adapter_type: adapterType, config, sample_size: 3 })
      .then(setTestResult)
      .catch((e: Error) => setSaveError(e.message))
      .finally(() => setBusy(false));
  };

  const handleSave = () => {
    if (!name.trim() || !adapterType) {
      setSaveError("Source name and adapter type are required.");
      return;
    }
    setBusy(true);
    const p: Promise<SourceRead> = isEdit
      ? apiClient.updateSource(source!.id, { name: name.trim(), config, enabled } as SourceUpdate)
      : apiClient.createSource({ name: name.trim(), adapter_type: adapterType, config, enabled } as SourceCreate);
    p.then(() => onSaved())
      .catch((e: Error) => setSaveError(e.message))
      .finally(() => setBusy(false));
  };

  const stepLabel = (s: WizardStep) =>
    s === 1 ? "Adapter" : s === 2 ? "Config" : "Test";

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }}>
      <div style={{
        background: "#fff", borderRadius: 12, width: 660, maxWidth: "95vw",
        maxHeight: "90vh", overflowY: "auto",
        boxShadow: "0 20px 60px rgba(0,0,0,0.2)",
      }}>
        {/* header */}
        <div style={{
          padding: "20px 24px 16px", borderBottom: "1px solid #e5e7eb",
          display: "flex", justifyContent: "space-between", alignItems: "flex-start",
        }}>
          <div>
            <h3 style={{ margin: 0 }}>{isEdit ? `Edit: ${source!.name}` : "Add Source"}</h3>
            {!isEdit && (
              <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
                {([1, 2, 3] as WizardStep[]).map((s) => (
                  <span key={s} style={{
                    fontSize: 12, padding: "2px 12px", borderRadius: 12,
                    background: step === s ? "#3b82f6" : step > s ? "#bbf7d0" : "#e5e7eb",
                    color: step === s ? "#fff" : step > s ? "#166534" : "#555",
                    fontWeight: step === s ? 600 : 400,
                  }}>
                    {s}. {stepLabel(s)}
                  </span>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: 22, color: "#aaa", lineHeight: 1 }}
          >
            â
          </button>
        </div>

        <div style={{ padding: "20px 24px" }}>
          {saveError && (
            <div style={{
              background: "#fef2f2", border: "1px solid #fca5a5",
              borderRadius: 8, padding: "10px 14px", marginBottom: 16, color: "#dc2626",
            }}>
              {saveError}
            </div>
          )}

          {/* ââ Step 1: pick adapter type ââ */}
          {step === 1 && (
            <div>
              <h4 style={{ margin: "0 0 16px", color: "#374151" }}>Select Adapter Type</h4>
              <div style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))",
                gap: 10,
              }}>
                {adapterTypes.map((t) => (
                  <div
                    key={t.adapter_type}
                    onClick={() => setAdapterType(t.adapter_type)}
                    style={{
                      border: `2px solid ${adapterType === t.adapter_type ? "#3b82f6" : "#e5e7eb"}`,
                      borderRadius: 8, padding: "12px 14px", cursor: "pointer",
                      background: adapterType === t.adapter_type ? "#eff6ff" : "#fff",
                      transition: "border-color 0.1s",
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{t.label}</div>
                    <div style={{ fontSize: 11, color: "#888", lineHeight: 1.4 }}>{t.description}</div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end" }}>
                <button
                  onClick={() => adapterType && setStep(2)}
                  disabled={!adapterType}
                  style={{
                    ...btnStyle("#3b82f6"),
                    padding: "9px 22px", fontSize: 14,
                    opacity: adapterType ? 1 : 0.4,
                    cursor: adapterType ? "pointer" : "not-allowed",
                  }}
                >
                  Next â
                </button>
              </div>
            </div>
          )}

          {/* ââ Step 2: config fields ââ */}
          {step === 2 && (
            <div>
              <h4 style={{ margin: "0 0 16px", color: "#374151" }}>
                Configure: {selectedMeta?.label ?? adapterType}
              </h4>

              {/* source name */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "block", fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
                  Source Name <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Clover Health Greenhouse"
                  style={INPUT_STYLE}
                />
              </div>

              {/* dynamic adapter fields */}
              {selectedMeta?.fields.map((field) => (
                <FieldInput
                  key={field.name}
                  field={field}
                  value={config[field.name]}
                  onChange={(v) => handleFieldChange(field.name, v)}
                />
              ))}

              {/* enabled */}
              <div style={{ marginTop: 4, display: "flex", alignItems: "center", gap: 8 }}>
                <input
                  type="checkbox"
                  id="src-enabled"
                  checked={enabled}
                  onChange={(e) => setEnabled(e.target.checked)}
                />
                <label htmlFor="src-enabled" style={{ fontSize: 13, cursor: "pointer" }}>
                  Enabled â include in daily pipeline
                </label>
              </div>

              <div style={{ marginTop: 22, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                {!isEdit ? (
                  <button onClick={() => setStep(1)} style={{ ...btnStyle("#6b7280"), padding: "9px 20px", fontSize: 14 }}>
                    â Back
                  </button>
                ) : <span />}
                <div style={{ display: "flex", gap: 10 }}>
                  {!isEdit && (
                    <button
                      onClick={() => { setSaveError(null); setStep(3); }}
                      style={{ ...btnStyle("#8b5cf6"), padding: "9px 20px", fontSize: 14 }}
                    >
                      Test First â
                    </button>
                  )}
                  <button
                    onClick={handleSave}
                    disabled={busy}
                    style={{ ...btnStyle("#22c55e"), padding: "9px 22px", fontSize: 14 }}
                  >
                    {busy ? "Savingâ¦" : isEdit ? "Save Changes" : "Save Source"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ââ Step 3: test connection ââ */}
          {step === 3 && (
            <div>
              <h4 style={{ margin: "0 0 8px", color: "#374151" }}>Test Connection</h4>
              <p style={{ color: "#6b7280", fontSize: 13, margin: "0 0 20px" }}>
                Dry-run the adapter to confirm it returns valid jobs before saving.
                Nothing is written to the database.
              </p>

              <button
                onClick={handleTest}
                disabled={busy}
                style={{ ...btnStyle("#8b5cf6"), padding: "10px 26px", fontSize: 14 }}
              >
                {busy ? "Testingâ¦" : "â¶ Run Test"}
              </button>

              {testResult && (
                <div style={{ marginTop: 16 }}>
                  <TestResultBanner result={testResult} onClose={() => setTestResult(null)} />
                </div>
              )}

              <div style={{ marginTop: 22, display: "flex", justifyContent: "space-between" }}>
                <button onClick={() => setStep(2)} style={{ ...btnStyle("#6b7280"), padding: "9px 20px", fontSize: 14 }}>
                  â Back
                </button>
                <button
                  onClick={handleSave}
                  disabled={busy}
                  style={{ ...btnStyle("#22c55e"), padding: "9px 22px", fontSize: 14 }}
                >
                  {busy ? "Savingâ¦" : "Save Source"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ââ main page âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

export function AdminSourcesPage() {
  const [sources, setSources] = useState<SourceRead[]>([]);
  const [adapterTypes, setAdapterTypes] = useState<AdapterTypeMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [editSource, setEditSource] = useState<SourceRead | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [testResult, setTestResult] = useState<SourceTestResult | null>(null);
  const [runResult, setRunResult] = useState<SourceRunResult | null>(null);
  const [actionBusy, setActionBusy] = useState<number | null>(null);

  const loadAll = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiClient.listSources(),
      apiClient.listSourceTypes(),
    ])
      .then(([srcs, types]: [SourceRead[], AdapterTypeList]) => {
        setSources(srcs);
        setAdapterTypes(types.adapter_types);
        setPageError(null);
      })
      .catch((e: Error) => setPageError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const handleToggle = (src: SourceRead) => {
    apiClient
      .updateSource(src.id, { enabled: !src.enabled })
      .then(loadAll)
      .catch((e: Error) => setPageError(e.message));
  };

  const handleDelete = (src: SourceRead) => {
    if (!window.confirm(`Delete "${src.name}"? This cannot be undone.`)) return;
    apiClient.deleteSource(src.id).then(loadAll).catch((e: Error) => setPageError(e.message));
  };

  const handleRunNow = (src: SourceRead) => {
    setActionBusy(src.id);
    setRunResult(null);
    setTestResult(null);
    apiClient
      .runSourceNow(src.id)
      .then((r: SourceRunResult) => { setRunResult(r); loadAll(); })
      .catch((e: Error) => setPageError(e.message))
      .finally(() => setActionBusy(null));
  };

  const handleTestExisting = (src: SourceRead) => {
    setActionBusy(src.id);
    setTestResult(null);
    setRunResult(null);
    apiClient
      .testExistingSource(src.id)
      .then(setTestResult)
      .catch((e: Error) => setPageError(e.message))
      .finally(() => setActionBusy(null));
  };

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1200 }}>
      {/* page header */}
      <div style={{
        display: "flex", justifyContent: "space-between",
        alignItems: "center", marginBottom: 24,
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 22 }}>Feed Sources</h2>
          <p style={{ margin: "4px 0 0", color: "#6b7280", fontSize: 14 }}>
            Manage job ingestion sources Â· {sources.length} source{sources.length !== 1 ? "s" : ""} configured
          </p>
        </div>
        <button
          onClick={() => { setShowAddModal(true); setTestResult(null); setRunResult(null); }}
          style={{
            ...btnStyle("#3b82f6"),
            padding: "10px 20px", fontSize: 14, fontWeight: 600, borderRadius: 8,
          }}
        >
          + Add Source
        </button>
      </div>

      {/* banners */}
      {pageError && (
        <div style={{
          background: "#fef2f2", border: "1px solid #fca5a5",
          borderRadius: 8, padding: "12px 16px", marginBottom: 16,
          display: "flex", justifyContent: "space-between",
        }}>
          <span style={{ color: "#dc2626" }}>{pageError}</span>
          <button onClick={() => setPageError(null)} style={{ background: "none", border: "none", cursor: "pointer" }}>â</button>
        </div>
      )}
      {runResult && <RunResultBanner result={runResult} onClose={() => setRunResult(null)} />}
      {testResult && <TestResultBanner result={testResult} onClose={() => setTestResult(null)} />}

      {/* table */}
      {loading ? (
        <div style={{ textAlign: "center", padding: 60, color: "#888" }}>Loading sourcesâ¦</div>
      ) : (
        <SourceTable
          sources={sources}
          adapterTypes={adapterTypes}
          actionBusy={actionBusy}
          onEdit={(src) => { setEditSource(src); setTestResult(null); setRunResult(null); }}
          onToggle={handleToggle}
          onDelete={handleDelete}
          onTest={handleTestExisting}
          onRunNow={handleRunNow}
        />
      )}

      {/* modal */}
      {(showAddModal || editSource !== null) && (
        <SourceModal
          source={editSource}
          adapterTypes={adapterTypes}
          onClose={() => { setShowAddModal(false); setEditSource(null); }}
          onSaved={() => { setShowAddModal(false); setEditSource(null); loadAll(); }}
        />
      )}
    </div>
  );
}
