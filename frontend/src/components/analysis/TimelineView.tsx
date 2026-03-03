import { memo, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import type { TimelineEvent } from "@/api/client";
import { entityColors } from "@/styles/tokens";

import styles from "./TimelineView.module.css";

interface TimelineViewProps {
  events: TimelineEvent[];
  loading: boolean;
  hasMore: boolean;
  onLoadMore: () => void;
}

function formatDate(iso: string): string {
  if (!iso) return "-";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString("pt-BR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  } catch {
    return iso;
  }
}

function TimelineViewInner({
  events,
  loading,
  hasMore,
  onLoadMore,
}: TimelineViewProps) {
  const { t } = useTranslation();
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!hasMore || loading) return;
    const el = sentinelRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          onLoadMore();
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, loading, onLoadMore]);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>{t("analysis.timeline")}</h2>
        <span className={styles.count}>{events.length}</span>
      </div>

      <div className={styles.scroll}>
        {events.length === 0 && !loading && (
          <p className={styles.empty}>{t("analysis.noTimeline")}</p>
        )}

        <div className={styles.timeline}>
          {events.map((event) => {
            const color =
              entityColors[event.entity_type] ?? "var(--text-muted)";
            return (
              <div key={event.id} className={styles.event}>
                <div className={styles.lineCol}>
                  <span
                    className={styles.dot}
                    style={{ backgroundColor: color }}
                  />
                  <span className={styles.line} />
                </div>
                <div className={styles.card}>
                  <span className={styles.date}>
                    {formatDate(event.date)}
                  </span>
                  <span
                    className={styles.categoryBadge}
                    style={{ backgroundColor: `${color}26` }}
                  >
                    {t(`entity.${event.entity_type}`, event.entity_type)}
                  </span>
                  <p className={styles.label}>{event.label}</p>
                  {(event.sources ?? []).length > 0 && (
                    <div className={styles.sources}>
                      {(event.sources ?? []).map((s) => (
                        <span key={s.database} className={styles.sourcePill}>
                          {s.database}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {loading && (
          <div className={styles.loadingRow}>
            <div className={styles.skeleton} />
            <div className={styles.skeleton} />
          </div>
        )}

        {hasMore && !loading && <div ref={sentinelRef} className={styles.sentinel} />}
      </div>
    </div>
  );
}

export const TimelineView = memo(TimelineViewInner);
