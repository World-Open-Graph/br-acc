import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Outlet, useLocation, useNavigate } from "react-router";

import {
  BarChart3,
  ChevronLeft,
  ChevronRight,
  FolderOpen,
  LogOut,
  Moon,
  Search,
  Sun,
  Landmark,
} from "lucide-react";

import { registerActions, type Action } from "@/actions/registry";
import { CommandPalette } from "@/components/common/CommandPalette";
import { Kbd } from "@/components/common/Kbd";
import { KeyboardShortcutsHelp } from "@/components/common/KeyboardShortcutsHelp";
import { StatusBar } from "@/components/common/StatusBar";
import { ToastContainer } from "@/components/common/ToastContainer";
import { IS_PATTERNS_ENABLED, IS_PUBLIC_MODE } from "@/config/runtime";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { useAuthStore } from "@/stores/auth";

import styles from "./AppShell.module.css";

const NAV_ITEMS = [
  { path: "/app", icon: BarChart3, labelKey: "nav.dashboard" },
  { path: "/app/emendas", icon: Landmark, labelKey: "nav.emendas" },
  { path: "/app/search", icon: Search, labelKey: "nav.search" },
  { path: "/app/investigations", icon: FolderOpen, labelKey: "nav.investigations" },
] as const;

export function AppShell() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();

  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [isMobileBlocked, setIsMobileBlocked] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    try {
      const saved = localStorage.getItem("bracc_theme");
      if (saved === "light" || saved === "dark") return saved;
    } catch { /* noop */ }
    if (typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: light)").matches) return "light";
    return "dark";
  });

  // Desktop-only: check viewport on mount and resize
  useEffect(() => {
    function check() {
      setIsMobileBlocked(window.innerWidth < 1024);
    }
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  const isGraphRoute = location.pathname.startsWith("/app/graph") || location.pathname.startsWith("/app/analysis");

  // Auto-collapse sidebar on graph/analysis routes
  useEffect(() => {
    if (isGraphRoute) setSidebarCollapsed(true);
  }, [isGraphRoute]);

  // Apply theme to document
  useEffect(() => {
    if (theme === "light") {
      document.documentElement.dataset.theme = "light";
    } else {
      delete document.documentElement.dataset.theme;
    }
    try { localStorage.setItem("bracc_theme", theme); } catch { /* noop */ }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  const toggleLang = useCallback(() => {
    const next = i18n.language === "pt-BR" ? "en" : "pt-BR";
    i18n.changeLanguage(next);
  }, [i18n]);

  const handleLogout = useCallback(() => {
    logout();
    navigate("/");
  }, [logout, navigate]);

  // Register actions for command palette + keyboard shortcuts
  const actions: Action[] = useMemo(
    () => {
      const base: Action[] = [
        { id: "go-dashboard", label: t("command.goToDashboard"), shortcut: "cmd+1", group: t("command.navigation"), handler: () => navigate("/app") },
        { id: "go-search", label: t("command.goToSearch"), shortcut: "cmd+2", group: t("command.navigation"), handler: () => navigate("/app/search") },
        { id: "toggle-sidebar", label: t("command.toggleSidebar"), shortcut: "cmd+b", group: t("command.actions"), handler: () => setSidebarCollapsed((p) => !p) },
        { id: "command-palette", label: t("shortcuts.commandPalette"), shortcut: "cmd+k", group: t("command.actions"), handler: () => setCommandOpen(true) },
        { id: "show-shortcuts", label: t("command.showShortcuts"), shortcut: "shift+?", group: t("command.actions"), handler: () => setShortcutsOpen(true) },
      ];
      if (IS_PATTERNS_ENABLED) {
        base.push(
          { id: "go-patterns", label: t("command.goToPatterns"), shortcut: "cmd+3", group: t("command.navigation"), handler: () => navigate("/app/patterns") },
        );
      }
      if (!IS_PUBLIC_MODE) {
        base.push(
          { id: "go-investigations", label: t("command.goToInvestigations"), shortcut: "cmd+4", group: t("command.navigation"), handler: () => navigate("/app/investigations") },
        );
      }
      return base;
    },
    [t, navigate],
  );

  useEffect(() => {
    registerActions(actions);
  }, [actions]);

  useKeyboardShortcuts();

  const isActive = (path: string) => {
    if (path === "/app") return location.pathname === "/app";
    return location.pathname.startsWith(path);
  };

  if (isMobileBlocked) {
    return (
      <div className={styles.mobileBlock}>
        <h1 className={styles.mobileTitle}>{t("mobile.title")}</h1>
        <p className={styles.mobileMessage}>{t("mobile.message")}</p>
        <p className={styles.mobileHint}>{t("mobile.hint")}</p>
      </div>
    );
  }

  return (
    <div className={styles.shell}>
      <nav className={`${styles.sidebar} ${sidebarCollapsed ? styles.collapsed : ""}`}>
        <div className={styles.sidebarHeader}>
          <Link to="/app" className={styles.logo}>
            {sidebarCollapsed ? "B" : "BR-ACC"}
          </Link>
        </div>

        <div className={styles.navItems}>
          {NAV_ITEMS
            .filter((item) => !(IS_PUBLIC_MODE && item.path.includes("investigations")))
            .map(({ path, icon: Icon, labelKey }) => (
              <Link
                key={path}
                to={path}
                className={`${styles.navItem} ${isActive(path) ? styles.navItemActive : ""}`}
                title={sidebarCollapsed ? t(labelKey) : undefined}
              >
                <Icon size={18} />
                {!sidebarCollapsed && <span>{t(labelKey)}</span>}
              </Link>
            ))}
        </div>

        <div className={styles.sidebarFooter}>
          {!sidebarCollapsed && (
            <button className={styles.cmdHint} onClick={() => setCommandOpen(true)}>
              <Kbd>&#8984;K</Kbd>
            </button>
          )}
          <button className={styles.langToggle} onClick={toggleTheme} title={theme === "dark" ? t("nav.themeLight") : t("nav.themeDark")}>
            {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
          </button>
          <button className={styles.langToggle} onClick={toggleLang} title={i18n.language === "pt-BR" ? "English" : "Portugues"}>
            {i18n.language === "pt-BR" ? "EN" : "PT"}
          </button>
          {user && !sidebarCollapsed && (
            <span className={styles.userEmail}>{user.email}</span>
          )}
          {!IS_PUBLIC_MODE && (
            <button className={styles.logoutBtn} onClick={handleLogout} title={t("nav.logout")} aria-label={t("nav.logout")}>
              <LogOut size={16} />
              {!sidebarCollapsed && <span>{t("nav.logout")}</span>}
            </button>
          )}
          <button
            className={styles.collapseBtn}
            onClick={() => setSidebarCollapsed((p) => !p)}
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>
      </nav>

      <div className={styles.content}>
        <main className={styles.main}><Outlet /></main>
        <StatusBar />
      </div>

      <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} />
      <KeyboardShortcutsHelp open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
      <ToastContainer />
    </div>
  );
}
