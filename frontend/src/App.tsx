import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import DashboardLayout from "./layouts/DashboardLayout";

// Stubs for your pages (create these in your src/pages folder)
import DataSources from "./pages/DataSources";
import Workspaces from "./pages/Workspaces";
import DataSourceChat from "./pages/DataSourceChat";

function Overview() {
  return <div className="p-8 text-white">Overview Dashboard Coming Soon...</div>;
}

function Settings() {
  return <div className="p-8 text-white">Account Settings Coming Soon...</div>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* The Layout acts as a wrapper for all child routes */}
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Overview />} />
          <Route path="/datasources" element={<DataSources />} />
          <Route path="/workspaces/*" element={<Workspaces />} />
          <Route path="/datasources/:id" element={<DataSourceChat />} />
          <Route path="/settings" element={<Settings />} />

        </Route>
        
        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}