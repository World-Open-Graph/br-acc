import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes, useLocation, useParams } from "react-router";

import { AppShell } from "./components/common/AppShell";
import { PublicShell } from "./components/common/PublicShell";
import { Spinner } from "./components/common/Spinner";
import { IS_PATTERNS_ENABLED, IS_PUBLIC_MODE } from "./config/runtime";
import { Baseline } from "./pages/Baseline";
import { Dashboard } from "./pages/Dashboard";
import { Investigations } from "./pages/Investigations";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/Login";
import { Patterns } from "./pages/Patterns";
import { Register } from "./pages/Register";
import { Search } from "./pages/Search";
import { SharedInvestigation } from "./pages/SharedInvestigation";
import { useAuthStore } from "./stores/auth";

const EntityAnalysis = lazy(() => import("./pages/EntityAnalysis").then((m) => ({ default: m.EntityAnalysis })));
const Analytics = lazy(() => import("./pages/Analytics").then((m) => ({ default: m.Analytics })));
const ReportsPage = lazy(() => import("./pages/Reports").then((m) => ({ default: m.Reports })));
const ActivityPage = lazy(() => import("./pages/Activity").then((m) => ({ default: m.Activity })));

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RedirectIfAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (token) return <Navigate to="/app" replace />;
  return <>{children}</>;
}

function GraphRedirect() {
  const { entityId } = useParams();
  return <Navigate to={`/app/analysis/${entityId}`} replace />;
}

export function App() {
  // Analytics: track page views
  const location = useLocation();
  useEffect(() => {
    fetch("/api/v1/analytics/pageview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page: location.pathname }),
    }).catch(() => {});
  }, [location.pathname]);

  const restore = useAuthStore((s) => s.restore);

  useEffect(() => {
    restore();
  }, [restore]);

  return (
    <Routes>
      {/* Public shell — landing, login, register */}
      <Route
        element={IS_PUBLIC_MODE ? <PublicShell /> : (
          <RedirectIfAuth>
            <PublicShell />
          </RedirectIfAuth>
        )}
      >
        <Route index element={<Landing />} />
        {!IS_PUBLIC_MODE && <Route path="login" element={<Login />} />}
        {!IS_PUBLIC_MODE && <Route path="register" element={<Register />} />}
      </Route>

      {/* Public — shared investigation (no auth, no shell) */}
      <Route path="shared/:token" element={<SharedInvestigation />} />

      {/* Authenticated shell — the intelligence workspace */}
      <Route
        path="app"
        element={IS_PUBLIC_MODE ? <AppShell /> : (
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        )}
      >
        <Route index element={<Dashboard />} />
        <Route path="search" element={<Search />} />
        <Route path="analysis/:entityId" element={<Suspense fallback={<Spinner />}><EntityAnalysis /></Suspense>} />
        <Route path="graph/:entityId" element={<GraphRedirect />} />
        {IS_PATTERNS_ENABLED && <Route path="patterns" element={<Patterns />} />}
        {IS_PATTERNS_ENABLED && <Route path="patterns/:entityId" element={<Patterns />} />}
        <Route path="analytics" element={<Suspense fallback={<Spinner />}><Analytics /></Suspense>} />
        <Route path="reports" element={<Suspense fallback={<Spinner />}><ReportsPage /></Suspense>} />
        <Route path="activity" element={<Suspense fallback={<Spinner />}><ActivityPage /></Suspense>} />
        <Route path="baseline/:entityId" element={<Baseline />} />
        {!IS_PUBLIC_MODE && <Route path="investigations" element={<Investigations />} />}
        {!IS_PUBLIC_MODE && <Route path="investigations/:investigationId" element={<Investigations />} />}
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
