import { useEffect, useState } from "react";
import styles from "./Activity.module.css";

interface ActivityItem {
  id: string;
  type: string;
  title: string;
  description: string;
  source: string;
  result_count: number;
  cost_usd: number;
  timestamp: string;
}

interface ActivityStats {
  total_events: number;
  by_type: Record<string, number>;
  total_cost_usd: number;
}

interface ActivityFeed {
  items: ActivityItem[];
  stats: ActivityStats;
}

const TYPE_ICONS: Record<string, string> = {
  chat: "💬",
  search: "🔍",
  report: "📄",
  entity_view: "👁️",
  tool_call: "🔧",
};

const TYPE_COLORS: Record<string, string> = {
  chat: "#4ade80",
  search: "#3b82f6",
  report: "#f59e0b",
  entity_view: "#8b5cf6",
  tool_call: "#ef4444",
};

const PAGE_SIZE = 10;

export function Activity() {
  const [feed, setFeed] = useState<ActivityFeed | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(0);

  const fetchFeed = async () => {
    try {
      const url = filter
        ? `/api/v1/activity/feed?limit=200&type=${filter}`
        : `/api/v1/activity/feed?limit=200`;
      const resp = await fetch(url);
      if (resp.ok) setFeed(await resp.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeed();
    const interval = setInterval(fetchFeed, 15000);
    return () => clearInterval(interval);
  }, [filter]);

  useEffect(() => { setPage(0); }, [filter]);

  const totalItems = feed?.items.length ?? 0;
  const totalPages = Math.ceil(totalItems / PAGE_SIZE);
  const pagedItems = feed?.items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE) ?? [];

  if (loading) return <div className={styles.loading}>Carregando atividades...</div>;
  if (!feed) return <div className={styles.loading}>Sem dados de atividade.</div>;

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Feed de Atividades</h1>
      <p className={styles.subtitle}>
        Todas as ações do sistema em tempo real - Mycelium Event Trail
      </p>

      <div className={styles.statsBar}>
        <div className={styles.stat}>
          <span className={styles.statValue}>{feed.stats.total_events}</span>
          <span className={styles.statLabel}>Total</span>
        </div>
        {Object.entries(feed.stats.by_type).map(([type, count]) => (
          <div
            key={type}
            className={styles.stat}
            onClick={() => setFilter(filter === type ? "" : type)}
            style={{ cursor: "pointer", borderColor: filter === type ? TYPE_COLORS[type] || "#4ade80" : "transparent" }}
          >
            <span className={styles.statValue}>
              {TYPE_ICONS[type] || "📊"} {count}
            </span>
            <span className={styles.statLabel}>{type}</span>
          </div>
        ))}
        <div className={styles.stat}>
          <span className={styles.statValue}>${feed.stats.total_cost_usd.toFixed(4)}</span>
          <span className={styles.statLabel}>Custo total</span>
        </div>
      </div>

      <div className={styles.timeline}>
        {pagedItems.map((item) => (
          <div key={item.id} className={styles.event}>
            <div
              className={styles.eventDot}
              style={{ backgroundColor: TYPE_COLORS[item.type] || "#666" }}
            />
            <div className={styles.eventContent}>
              <div className={styles.eventHeader}>
                <span className={styles.eventType}>
                  {TYPE_ICONS[item.type] || "📊"} {item.type}
                </span>
                <span className={styles.eventTime}>
                  {new Date(item.timestamp).toLocaleTimeString("pt-BR")}
                </span>
              </div>
              <div className={styles.eventTitle}>
                {item.type === "chat" ? "Consulta ao agente" :
                 item.type === "search" ? "Busca realizada" :
                 item.type === "entity_view" ? "Entidade visualizada" :
                 item.type === "report" ? "Relatório gerado" :
                 item.type === "tool_call" ? "Ferramenta utilizada" :
                 "Ação registrada"}
              </div>
              <div className={styles.eventMeta}>
                {item.source && <span>Fonte: {item.source}</span>}
                {item.result_count > 0 && <span>{item.result_count} resultados</span>}
                {item.cost_usd > 0 && <span>${item.cost_usd.toFixed(4)}</span>}
              </div>
            </div>
          </div>
        ))}
        {feed.items.length === 0 && (
          <div className={styles.empty}>
            Nenhuma atividade registrada. Faça uma busca no chatbot para começar.
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className={styles.pagination}>
          <button
            className={styles.pageBtn}
            disabled={page === 0}
            onClick={() => setPage(p => Math.max(0, p - 1))}
          >
            ← Anterior
          </button>
          <span className={styles.pageInfo}>
            Página {page + 1} de {totalPages} ({totalItems} eventos)
          </span>
          <button
            className={styles.pageBtn}
            disabled={page >= totalPages - 1}
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
          >
            Próxima →
          </button>
        </div>
      )}
    </div>
  );
}
