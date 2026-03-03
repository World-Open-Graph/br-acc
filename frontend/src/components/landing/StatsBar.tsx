import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type StatsResponse, getStats } from "@/api/client";
import { useCountUp } from "@/hooks/useCountUp";

import styles from "./StatsBar.module.css";

interface StatItemProps {
  target: number;
  label: string;
  suffix?: string;
}

function StatItem({ target, label, suffix = "" }: StatItemProps) {
  const { ref, value } = useCountUp(target);

  return (
    <div className={styles.item} ref={ref}>
      <span className={styles.number}>
        {value.toLocaleString()}
        {suffix && <span className={styles.suffix}>{suffix}</span>}
      </span>
      <span className={styles.label}>{label}</span>
    </div>
  );
}

function formatLargeNumber(n: number): { value: number; suffix: string } {
  if (n >= 1_000_000) return { value: Math.round(n / 100_000) / 10, suffix: "M" };
  if (n >= 1_000) return { value: Math.round(n / 100) / 10, suffix: "K" };
  return { value: n, suffix: "" };
}

const STATS_CACHE_KEY = "bracc_stats_cache";

function getCachedStats(): StatsResponse | null {
  try {
    const raw = localStorage.getItem(STATS_CACHE_KEY);
    return raw ? (JSON.parse(raw) as StatsResponse) : null;
  } catch {
    return null;
  }
}

export function StatsBar() {
  const { t } = useTranslation();
  const [stats, setStats] = useState<StatsResponse | null>(getCachedStats);
  const [error, setError] = useState(false);

  const fetchStats = () => {
    setError(false);
    getStats()
      .then((data) => {
        setStats(data);
        localStorage.setItem(STATS_CACHE_KEY, JSON.stringify(data));
      })
      .catch(() => setError(true));
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (error && !stats) {
    return (
      <div className={styles.bar}>
        <div className={styles.inner}>
          <div className={styles.item}>
            <span className={styles.errorText}>
              {t("common.error")}
            </span>
            <button className={styles.retryBtn} onClick={fetchStats}>
              {t("common.retry")}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className={styles.bar}>
        <div className={styles.inner}>
          <div className={styles.item}>
            <span className={styles.number}>{"-"}</span>
            <span className={styles.label}>{t("common.loading")}</span>
          </div>
        </div>
      </div>
    );
  }

  const nodes = formatLargeNumber(stats.total_nodes);
  const rels = formatLargeNumber(stats.total_relationships);

  return (
    <div className={styles.bar}>
      <div className={styles.inner}>
        <StatItem
          target={nodes.value}
          suffix={nodes.suffix}
          label={t("landing.stats.entities")}
        />
        <div className={styles.separator} />
        <StatItem
          target={rels.value}
          suffix={rels.suffix}
          label={t("landing.stats.connections")}
        />
        <div className={styles.separator} />
        <StatItem
          target={stats.data_sources}
          label={t("landing.stats.dataSources")}
        />
      </div>
    </div>
  );
}
