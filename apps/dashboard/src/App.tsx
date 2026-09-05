import { Link, Route, Routes } from "react-router-dom";

import "./App.css";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { CreateDropPage } from "./pages/CreateDropPage";
import { LiveQueuePage } from "./pages/LiveQueuePage";
import { LoginPage } from "./pages/LoginPage";

function App() {
  return (
    <div>
      <nav>
        <Link to="/">Login</Link> | <Link to="/drops/new">Create Drop</Link> |{" "}
        <Link to="/queue">Live Queue</Link> | <Link to="/analytics">Analytics</Link>
      </nav>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/drops/new" element={<CreateDropPage />} />
        <Route path="/queue" element={<LiveQueuePage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
      </Routes>
    </div>
  );
}

export default App;
