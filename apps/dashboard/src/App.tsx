import { Navigate, Route, Routes } from "react-router-dom";

import "./App.css";
import { Sidebar } from "./components/Sidebar";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { CreateDropPage } from "./pages/CreateDropPage";
import { LoginPage } from "./pages/LoginPage";
import { ManageDropsPage } from "./pages/ManageDropsPage";
import { OverviewPage } from "./pages/OverviewPage";
import { RedemptionQueuePage } from "./pages/RedemptionQueuePage";
import { ScanPage } from "./pages/ScanPage";
import { SettingsPage } from "./pages/SettingsPage";
import { isLoggedIn } from "./services/auth";

function ProtectedLayout({ children }: { children: React.ReactNode }) {
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-content">{children}</main>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedLayout>
            <OverviewPage />
          </ProtectedLayout>
        }
      />
      <Route
        path="/drops"
        element={
          <ProtectedLayout>
            <ManageDropsPage />
          </ProtectedLayout>
        }
      />
      <Route
        path="/drops/new"
        element={
          <ProtectedLayout>
            <CreateDropPage />
          </ProtectedLayout>
        }
      />
      <Route
        path="/analytics"
        element={
          <ProtectedLayout>
            <AnalyticsPage />
          </ProtectedLayout>
        }
      />
      <Route
        path="/queue"
        element={
          <ProtectedLayout>
            <RedemptionQueuePage />
          </ProtectedLayout>
        }
      />
      <Route
        path="/scan"
        element={
          <ProtectedLayout>
            <ScanPage />
          </ProtectedLayout>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedLayout>
            <SettingsPage />
          </ProtectedLayout>
        }
      />
    </Routes>
  );
}

export default App;
