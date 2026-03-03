import { useEffect, useState } from "react";

interface ETLData {
  running: boolean;
  phase: number | null;
  current_file: string | null;
  files_processed: number;
  total_files: number;
  percent: number;
  last_update: string | null;
  phases: Record<string, string>;
}

export function ETLProgress() {
  const [data, setData] = useState<ETLData | null>(null);

  useEffect(() => {
    const fetchProgress = () => {
      fetch("/api/v1/meta/etl-progress")
        .then((r) => (r.ok ? r.json() : null))
        .then(setData)
        .catch(() => null);
    };
    fetchProgress();
    const interval = setInterval(fetchProgress, 30000);
    return () => clearInterval(interval);
  }, []);

  if (!data) return null;

  // Hide widget entirely if ETL never ran (no log file, no progress)
  const neverRan = !data.running && data.phase === null && data.files_processed === 0;
  if (neverRan) return null;

  const isIdle = !data.running && (data.phase === 0 || data.phase === null);
  const phaseLabel = data.phase ? data.phases[String(data.phase)] || `Fase ${data.phase}` : "Aguardando início";

  const statusLabel = data.running
    ? "ETL em andamento"
    : data.percent >= 95
      ? "ETL concluído"
      : isIdle
        ? "ETL pausado"
        : "ETL pausado";

  return (
    <div
      style={{
        margin: "1rem auto",
        maxWidth: 600,
        padding: "1rem 1.25rem",
        background: "rgba(15,23,42,0.6)",
        borderRadius: 10,
        border: data.running
          ? "1px solid rgba(59,130,246,0.3)"
          : "1px solid rgba(71,85,105,0.2)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
        {data.running ? (
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "#3b82f6",
              animation: "pulse 2s infinite",
              flexShrink: 0,
            }}
          />
        ) : (
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: data.percent >= 95 ? "#10b981" : "#64748b",
              flexShrink: 0,
            }}
          />
        )}
        <span style={{ fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          {statusLabel}
        </span>
        {data.last_update && (
          <span style={{ fontSize: "0.625rem", color: "#475569", marginLeft: "auto" }}>
            {data.last_update}
          </span>
        )}
      </div>

      <div style={{ fontSize: "0.8125rem", color: "#e2e8f0", marginBottom: "0.5rem" }}>
        {data.phase ? `Fase ${data.phase}/4: ${phaseLabel}` : phaseLabel}
      </div>

      {/* Progress bar */}
      <div
        style={{
          height: 6,
          background: "rgba(30,41,59,0.8)",
          borderRadius: 3,
          overflow: "hidden",
          marginBottom: "0.375rem",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${Math.min(data.percent, 100)}%`,
            background: "linear-gradient(90deg, #3b82f6, #60a5fa)",
            borderRadius: 3,
            transition: "width 1s ease",
          }}
        />
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.625rem", color: "#64748b" }}>
        <span>
          Arquivos: {data.files_processed}/{data.total_files}
        </span>
        <span>{data.percent.toFixed(1)}%</span>
      </div>

      {data.current_file && (
        <div style={{ fontSize: "0.5625rem", color: "#475569", marginTop: "0.25rem", fontFamily: "monospace" }}>
          {data.current_file}
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
