import { type ReactNode, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { type StatsResponse, getStats } from "@/api/client";
import { FeatureCard } from "@/components/landing/FeatureCard";
import {
  GraphIcon,
  InvestigationIcon,
  PatternIcon,
} from "@/components/landing/FeatureIcons";
import { IS_PATTERNS_ENABLED, IS_PUBLIC_MODE } from "@/config/runtime";
import { HeroGraph } from "@/components/landing/HeroGraph";
import { NetworkAnimation } from "@/components/landing/NetworkAnimation";
import { StatsBar } from "@/components/landing/StatsBar";

import styles from "./Landing.module.css";

function useReveal() {
  const setRef = useCallback((node: HTMLElement | null) => {
    if (!node) return;
    const cls = styles.revealed ?? "revealed";
    const hasMatchMedia = typeof window.matchMedia === "function";
    const prefersReduced = hasMatchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced || typeof IntersectionObserver === "undefined") {
      node.classList.add(cls);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting) {
          node.classList.add(cls);
          observer.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    observer.observe(node);
  }, []);
  return setRef;
}

function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(Math.round(n / 100_000) / 10).toFixed(1)}M`;
  if (n >= 1_000) return `${(Math.round(n / 100) / 10).toFixed(1)}K`;
  return String(n);
}

interface SourceDef {
  nameKey: string;
  descKey: string;
  countFn: (s: StatsResponse) => number | null;
}

const DATA_SOURCES: SourceDef[] = [
  { nameKey: "CNPJ", descKey: "landing.sources.cnpj", countFn: (s) => s.company_count },
  { nameKey: "TSE", descKey: "landing.sources.tse", countFn: (s) => s.person_count },
  { nameKey: "Transparência", descKey: "landing.sources.transparencia", countFn: (s) => s.contract_count },
  { nameKey: "CEIS/CNEP", descKey: "landing.sources.sanctions", countFn: (s) => s.sanction_count },
  { nameKey: "DATASUS", descKey: "landing.sources.cnes", countFn: (s) => s.health_count },
  { nameKey: "BNDES", descKey: "landing.sources.bndes", countFn: (s) => s.finance_count },
  { nameKey: "PGFN", descKey: "landing.sources.pgfn", countFn: () => null },
  { nameKey: "IBAMA", descKey: "landing.sources.ibama", countFn: (s) => s.embargo_count },
  { nameKey: "ComprasNet", descKey: "landing.sources.comprasnet", countFn: () => null },
  { nameKey: "TCU", descKey: "landing.sources.tcu", countFn: () => null },
  { nameKey: "TransfereGov", descKey: "landing.sources.transferegov", countFn: (s) => s.amendment_count },
  { nameKey: "RAIS", descKey: "landing.sources.rais", countFn: (s) => s.laborstats_count },
  { nameKey: "INEP", descKey: "landing.sources.inep", countFn: (s) => s.education_count },
];

interface FeatureDef {
  key: string;
  icon: ReactNode;
  iconBg: string;
}

const FEATURES: FeatureDef[] = [
  { key: "graph", icon: <GraphIcon />, iconBg: "var(--cyan-dim)" },
  { key: "patterns", icon: <PatternIcon />, iconBg: "var(--accent-dim)" },
  { key: "investigations", icon: <InvestigationIcon />, iconBg: "rgba(78, 168, 222, 0.12)" },
];

const STATS_CACHE_KEY = "bracc_stats_cache";

function LiveDatabaseStatus({ stats }: { stats: StatsResponse | null }) {
  if (!stats) return null;

  const DB_ROWS = [
    { label: "Empresas (CNPJ)", count: stats.company_count, loading: stats.company_count < 1000 },
    { label: "Sanções (CEIS/CNEP/OpenSanctions)", count: stats.sanction_count, loading: false },
    { label: "Pessoas / Sócios", count: stats.person_count, loading: stats.person_count < 100 },
    { label: "Contratos Públicos", count: stats.contract_count, loading: false },
    { label: "Financiamentos (BNDES)", count: stats.finance_count, loading: false },
    { label: "Saúde (DATASUS)", count: stats.health_count, loading: false },
    { label: "Embargos (IBAMA)", count: stats.embargo_count, loading: false },
  ].filter((r) => r.count > 0 || r.loading);

  return (
    <section style={{
      padding: "clamp(3rem, 6vw, 5rem) 0",
      background: "linear-gradient(180deg, #090b0b 0%, #0a0b0c 100%)",
      borderTop: "1px solid rgba(255,255,255,0.06)",
    }}>
      <div style={{ width: "min(72rem, calc(100% - 4rem))", margin: "0 auto" }}>
        <div style={{
          display: "flex", alignItems: "center", gap: "0.6rem",
          marginBottom: "0.8rem",
          fontFamily: "var(--font-mono)", fontSize: "0.68rem", fontWeight: 500,
          letterSpacing: "0.12em", textTransform: "uppercase" as const,
          color: "rgba(148,163,154,0.9)",
        }}>
          <span style={{ width: "1.5rem", height: "1px", background: "rgba(0,229,195,0.72)" }} />
          STATUS EM TEMPO REAL
        </div>
        <h2 style={{
          fontFamily: "var(--font-display)", fontStyle: "italic", fontWeight: 400,
          fontSize: "clamp(1.6rem, 3.5vw, 2.4rem)", lineHeight: 1,
          letterSpacing: "-0.018em", color: "#f0f3f1",
          marginBottom: "clamp(1.5rem, 3vw, 2rem)",
        }}>
          Base de Dados
        </h2>
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(16rem, 1fr))",
          gap: "0.6rem",
        }}>
          {DB_ROWS.map((row) => (
            <div key={row.label} style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "0.85rem 1.1rem",
              background: "#111416", border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "0.6rem",
            }}>
              <span style={{ fontSize: "0.85rem", color: "rgba(232,237,233,0.8)" }}>
                {row.label}
              </span>
              <span style={{
                fontFamily: "var(--font-mono)", fontSize: "0.85rem", fontWeight: 600,
                color: row.loading ? "rgba(234,179,8,0.9)" : "rgba(0,229,195,0.9)",
                display: "flex", alignItems: "center", gap: "0.4rem",
              }}>
                {row.loading && (
                  <span style={{
                    width: 6, height: 6, borderRadius: "50%",
                    background: "rgba(234,179,8,0.9)",
                    animation: "pulse 1.5s ease-in-out infinite",
                  }} />
                )}
                {row.count > 0 ? formatCount(row.count) : "Carregando..."}
              </span>
            </div>
          ))}
        </div>
        <p style={{
          marginTop: "1rem", fontSize: "0.78rem",
          color: "rgba(148,163,154,0.7)", fontFamily: "var(--font-mono)",
        }}>
          Total: {formatCount(stats.total_nodes)} entidades · {formatCount(stats.total_relationships)} conexões · Atualizado a cada visita
        </p>
      </div>
      <style>{`@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>
    </section>
  );
}

function PartnershipCTA() {
  return (
    <section style={{
      padding: "clamp(3rem, 6vw, 4.5rem) 0",
      background: "linear-gradient(135deg, rgba(30,58,95,0.3) 0%, rgba(30,27,75,0.3) 100%)",
      borderTop: "1px solid rgba(59,130,246,0.15)",
    }}>
      <div style={{
        width: "min(64rem, calc(100% - 4rem))", margin: "0 auto", textAlign: "center" as const,
      }}>
        <h2 style={{
          fontFamily: "var(--font-display)", fontStyle: "italic", fontWeight: 400,
          fontSize: "clamp(1.8rem, 4vw, 2.8rem)", lineHeight: 1,
          color: "#f0f3f1", marginBottom: "1rem",
        }}>
          Aberto a Parcerias
        </h2>
        <p style={{
          maxWidth: "38rem", margin: "0 auto 2rem", fontSize: "1rem",
          lineHeight: 1.6, color: "rgba(232,237,233,0.7)",
        }}>
          Pesquisadores, jornalistas, desenvolvedores, instituições, governos e universidades
          podem contribuir integrando novas bases de dados, criando investigações e expandindo o sistema.
          Quanto mais bases conectadas, mais poderoso o cruzamento.
        </p>
        <div style={{ display: "flex", gap: "0.8rem", justifyContent: "center", flexWrap: "wrap" as const }}>
          <a href="https://github.com/enioxt/br-acc" target="_blank" rel="noopener noreferrer" style={{
            display: "inline-flex", alignItems: "center", padding: "0.75rem 1.8rem",
            background: "rgba(59,130,246,0.9)", color: "white", borderRadius: "0.6rem",
            textDecoration: "none", fontWeight: 600, fontSize: "0.9rem",
          }}>
            GitHub — Código e Roadmap
          </a>
          <a href="https://t.me/EthikIntelligence" target="_blank" rel="noopener noreferrer" style={{
            display: "inline-flex", alignItems: "center", padding: "0.75rem 1.8rem",
            background: "transparent", color: "rgba(232,237,233,0.9)",
            border: "1px solid rgba(255,255,255,0.2)", borderRadius: "0.6rem",
            textDecoration: "none", fontWeight: 600, fontSize: "0.9rem",
          }}>
            Telegram
          </a>
        </div>
        <p style={{
          marginTop: "1.5rem", fontSize: "0.78rem",
          color: "rgba(148,163,154,0.7)", fontFamily: "var(--font-mono)",
        }}>
          100% open-source · Infraestrutura: $36/mês autofinanciado · Sem investidores, sem publicidade
        </p>
      </div>
    </section>
  );
}

export function Landing() {
  const { t } = useTranslation();

  const featuresRef = useReveal();
  const howRef = useReveal();
  const trustRef = useReveal();
  const sourcesRef = useReveal();

  const [stats, setStats] = useState<StatsResponse | null>(() => {
    try {
      const raw = localStorage.getItem(STATS_CACHE_KEY);
      return raw ? (JSON.parse(raw) as StatsResponse) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    getStats()
      .then((data) => {
        setStats(data);
        localStorage.setItem(STATS_CACHE_KEY, JSON.stringify(data));
      })
      .catch(() => {});
  }, []);

  const visibleFeatures = IS_PATTERNS_ENABLED
    ? FEATURES
    : FEATURES.filter((feature) => feature.key !== "patterns");

  return (
    <>
      <section className={styles.hero}>
        <NetworkAnimation />

        <div className={styles.heroContent}>
          <div className={styles.heroLeft}>
            <span className={styles.badge}>{t("landing.badge")}</span>

            <h1 className={styles.title}>{t("landing.hero")}</h1>

            <p className={styles.subtitle}>{t("landing.heroSubtitle")}</p>

            <Link to={IS_PUBLIC_MODE ? "/app/search" : "/login"} className={styles.cta}>
              {t("landing.cta")}
            </Link>

            <p className={styles.disclaimer}>{t("app.disclaimer")}</p>
          </div>

          <div className={styles.heroRight}>
            <HeroGraph />
          </div>
        </div>
      </section>

      <StatsBar />

      <section className={styles.features}>
        <div ref={featuresRef} className={`${styles.featuresInner} ${styles.reveal}`}>
          <span className={styles.sectionLabel}>
            {t("landing.features.sectionLabel")}
          </span>
          <h2 className={styles.sectionHeading}>
            {t("landing.features.sectionHeading")}
          </h2>
          <div className={styles.featuresGrid}>
            {visibleFeatures.map(({ key, icon, iconBg }) => (
              <FeatureCard
                key={key}
                icon={icon}
                iconBg={iconBg}
                title={t(`landing.features.${key}`)}
                description={t(`landing.features.${key}Desc`)}
              />
            ))}
          </div>
        </div>
      </section>

      <section className={styles.howItWorks}>
        <div ref={howRef} className={`${styles.howItWorksInner} ${styles.reveal}`}>
          <span className={styles.sectionLabel}>
            {t("landing.howItWorks.sectionLabel")}
          </span>
          <h2 className={styles.sectionHeading}>
            {t("landing.howItWorks.sectionHeading")}
          </h2>
          <div className={styles.stepsGrid}>
            {[1, 2, 3].map((n) => (
              <div key={n} className={styles.step}>
                <span className={styles.stepNumber}>{n}</span>
                <span className={styles.stepTitle}>
                  {t(`landing.howItWorks.step${n}`)}
                </span>
                <span className={styles.stepDesc}>
                  {t(`landing.howItWorks.step${n}Desc`)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div ref={trustRef} className={`${styles.trust} ${styles.reveal}`}>
        <div className={styles.trustItem}>
          <span className={styles.trustValue}>{t("landing.trust.openSourceValue")}</span>
          <span className={styles.trustLabel}>{t("landing.trust.openSource")}</span>
        </div>
        <div className={styles.trustItem}>
          <span className={styles.trustValue}>{t("landing.trust.neutralValue")}</span>
          <span className={styles.trustLabel}>{t("landing.trust.neutral")}</span>
        </div>
        <div className={styles.trustItem}>
          <span className={styles.trustValue}>{t("landing.trust.auditableValue")}</span>
          <span className={styles.trustLabel}>{t("landing.trust.auditable")}</span>
        </div>
      </div>

      <section className={styles.sources}>
        <div ref={sourcesRef} className={`${styles.sourcesInner} ${styles.reveal}`}>
          <span className={styles.sectionLabel}>
            {t("landing.sources.sectionLabel")}
          </span>
          <h2 className={styles.sectionHeading}>
            {t("landing.sources.sectionHeading")}
          </h2>
          <div className={styles.sourcesGrid}>
            {DATA_SOURCES.map((source) => {
              const count = stats ? source.countFn(stats) : null;
              return (
                <div key={source.nameKey} className={styles.sourceCard}>
                  <div className={styles.sourceHeader}>
                    <span className={styles.sourceName}>{source.nameKey}</span>
                    <span className={styles.sourceCount}>
                      {count != null ? formatCount(count) : "\u2014"}
                    </span>
                  </div>
                  <span className={styles.sourceDesc}>{t(source.descKey)}</span>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <LiveDatabaseStatus stats={stats} />

      <PartnershipCTA />

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerTop}>
            <Link to={IS_PUBLIC_MODE ? "/app/search" : "/login"} className={styles.footerLink}>
              {t("landing.footer.platform")}
            </Link>
            <a href="https://github.com/enioxt/br-acc" target="_blank" rel="noopener noreferrer" className={styles.footerLink}>
              GitHub
            </a>
            <span className={styles.footerLink}>
              {t("landing.footer.methodology")}
            </span>
            <span className={styles.footerLink}>
              {t("landing.footer.license")}
            </span>
          </div>
          <div className={styles.footerDivider} />
          <span className={styles.footerBrand}>{t("landing.footer.brand")}</span>
          <p className={styles.footerDisclaimer}>{t("app.disclaimer")}</p>
        </div>
      </footer>
    </>
  );
}
