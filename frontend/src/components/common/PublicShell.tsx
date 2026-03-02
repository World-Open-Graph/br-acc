import { useTranslation } from "react-i18next";
import { Link, Outlet } from "react-router";

import { IS_PUBLIC_MODE } from "@/config/runtime";
import { useAuthStore } from "@/stores/auth";

import styles from "./PublicShell.module.css";

export function PublicShell() {
  const { t, i18n } = useTranslation();
  const token = useAuthStore((s) => s.token);

  const toggleLang = () => {
    const next = i18n.language === "pt-BR" ? "en" : "pt-BR";
    i18n.changeLanguage(next);
  };

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Link to="/" className={styles.logo}>
          {t("app.title")}
        </Link>
        <div className={styles.actions}>
          {IS_PUBLIC_MODE ? (
            <Link to="/app/search" className={styles.registerLink}>
              Open Explorer
            </Link>
          ) : !token && (
            <>
              <Link to="/login" className={styles.authLink}>
                {t("nav.login")}
              </Link>
              <Link to="/register" className={styles.registerLink}>
                {t("nav.register")}
              </Link>
            </>
          )}
          <button
            onClick={toggleLang}
            className={styles.langToggle}
            type="button"
          >
            {i18n.language === "pt-BR" ? "EN" : "PT"}
          </button>
        </div>
      </header>
      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  );
}
