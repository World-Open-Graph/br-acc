import { useCallback, useEffect, useState } from "react";
import { getJourney, removeJourneyEntry, clearJourney, exportJourneyJSON, exportJourneyMarkdown, getJourneyStats, type JourneyEntry } from "@/lib/journey";

const TYPE_ICONS: Record<string, string> = {
  search: "🔍", entity: "📊", chat: "💬", pattern: "🔗", investigation: "📋",
};

export function JourneyPanel() {
  const [entries, setEntries] = useState<JourneyEntry[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [stats, setStats] = useState({ total: 0, searches: 0, entities: 0, chats: 0, lastActive: "Nunca" });

  const refresh = useCallback(() => {
    const j = getJourney();
    setEntries([...j.entries].reverse());
    setStats(getJourneyStats());
  }, []);

  useEffect(() => {
    refresh();
    const handler = () => refresh();
    window.addEventListener("journey-updated", handler);
    return () => window.removeEventListener("journey-updated", handler);
  }, [refresh]);

  const handleExportJSON = () => {
    const blob = new Blob([exportJourneyJSON()], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "egos-jornada-" + new Date().toISOString().slice(0, 10) + ".json";
    a.click(); URL.revokeObjectURL(url);
  };

  const handleExportMD = () => {
    const blob = new Blob([exportJourneyMarkdown()], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "egos-jornada-" + new Date().toISOString().slice(0, 10) + ".md";
    a.click(); URL.revokeObjectURL(url);
  };

  const handleShare = async () => {
    const md = exportJourneyMarkdown();
    try {
      if (navigator.share) {
        await navigator.share({ title: "Jornada EGOS Inteligencia", text: md });
      } else {
        await navigator.clipboard.writeText(md);
        alert("Jornada copiada para a area de transferencia!");
      }
    } catch { /* user cancelled */ }
  };

  const handleClear = () => {
    if (confirm("Limpar toda a jornada de pesquisa?")) {
      clearJourney();
      refresh();
    }
  };

  if (entries.length === 0 && !isOpen) return null;

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        style={{
          position: "fixed", bottom: 80, left: 16, zIndex: 90,
          display: "flex", alignItems: "center", gap: 6,
          padding: "8px 14px", borderRadius: 20,
          background: "rgba(15,23,42,0.9)", backdropFilter: "blur(12px)",
          border: "1px solid rgba(0,229,195,0.2)",
          color: "#94a3b8", fontSize: 12, cursor: "pointer",
          boxShadow: "0 4px 20px rgba(0,0,0,0.3)",
        }}
      >
        <span style={{ fontSize: 14 }}>📖</span>
        <span>{stats.total} pesquisas</span>
      </button>
    );
  }

  return (
    <div style={{
      position: "fixed", bottom: 16, left: 16, zIndex: 90,
      width: 340, maxHeight: "70vh",
      display: "flex", flexDirection: "column",
      background: "rgba(15,23,42,0.95)", backdropFilter: "blur(16px)",
      borderRadius: 12, border: "1px solid rgba(71,85,105,0.3)",
      boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
      overflow: "hidden",
    }}>
      <div style={{
        padding: "12px 14px", borderBottom: "1px solid rgba(71,85,105,0.2)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <div>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0" }}>📖 Jornada</span>
          <span style={{ fontSize: 10, color: "#64748b", marginLeft: 8 }}>{stats.total} registros</span>
        </div>
        <button onClick={() => setIsOpen(false)} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 16 }}>✕</button>
      </div>

      <div style={{ display: "flex", gap: 8, padding: "8px 14px", borderBottom: "1px solid rgba(71,85,105,0.1)" }}>
        {[
          { label: "Buscas", value: stats.searches, color: "#3b82f6" },
          { label: "Entidades", value: stats.entities, color: "#8b5cf6" },
          { label: "Chat", value: stats.chats, color: "#00e5c3" },
        ].map((s) => (
          <div key={s.label} style={{ textAlign: "center", flex: 1 }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: s.color, display: "block" }}>{s.value}</span>
            <span style={{ fontSize: 9, color: "#64748b", textTransform: "uppercase" }}>{s.label}</span>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 4, padding: "6px 14px", borderBottom: "1px solid rgba(71,85,105,0.1)" }}>
        {[
          { label: "JSON", onClick: handleExportJSON },
          { label: "Markdown", onClick: handleExportMD },
          { label: "Compartilhar", onClick: handleShare },
          { label: "Limpar", onClick: handleClear },
        ].map((a) => (
          <button key={a.label} onClick={a.onClick} style={{
            fontSize: 10, padding: "3px 8px", borderRadius: 4,
            background: a.label === "Limpar" ? "rgba(239,68,68,0.1)" : "rgba(59,130,246,0.1)",
            border: "1px solid " + (a.label === "Limpar" ? "rgba(239,68,68,0.2)" : "rgba(59,130,246,0.2)"),
            color: a.label === "Limpar" ? "#ef4444" : "#94a3b8",
            cursor: "pointer",
          }}>
            {a.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "8px 10px", maxHeight: "40vh" }}>
        {entries.map((e) => (
          <div key={e.id} style={{
            display: "flex", alignItems: "flex-start", gap: 8,
            padding: "6px 8px", borderRadius: 6, marginBottom: 4,
            background: "rgba(30,41,59,0.5)",
            border: "1px solid rgba(71,85,105,0.15)",
          }}>
            <span style={{ fontSize: 12, flexShrink: 0 }}>{TYPE_ICONS[e.type] || "📄"}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <a
                href={e.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  fontSize: 11, color: "#e2e8f0", textDecoration: "none", fontWeight: 500,
                  display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}
              >
                {e.title}
              </a>
              <span style={{ fontSize: 9, color: "#475569" }}>
                {new Date(e.timestamp).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                {e.description && (" - " + e.description.slice(0, 40))}
              </span>
            </div>
            <button
              onClick={() => { removeJourneyEntry(e.id); refresh(); }}
              style={{ background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: 10, padding: 2, flexShrink: 0 }}
            >✕</button>
          </div>
        ))}
        {entries.length === 0 && (
          <div style={{ textAlign: "center", padding: "20px 0", color: "#475569", fontSize: 12 }}>
            Suas pesquisas aparecerao aqui automaticamente.
          </div>
        )}
      </div>
    </div>
  );
}
