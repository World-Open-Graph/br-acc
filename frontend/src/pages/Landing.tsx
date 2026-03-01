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

const STATS_CACHE_KEY = "icarus_stats_cache";

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

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerTop}>
            <Link to={IS_PUBLIC_MODE ? "/app/search" : "/login"} className={styles.footerLink}>
              {t("landing.footer.platform")}
            </Link>
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
