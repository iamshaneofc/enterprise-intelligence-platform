import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppLayout } from "@/layouts/AppLayout";
import { Login } from "@/pages/Login";
import { Register } from "@/pages/Register";
import { Overview } from "@/pages/Overview";
import { KnowledgeBase } from "@/pages/KnowledgeBase";
import { AIInvestigation } from "@/pages/AIInvestigation";
import { AgentRuns } from "@/pages/AgentRuns";
import { Conversations } from "@/pages/Conversations";
import { Evaluation } from "@/pages/Evaluation";
import { SettingsPage } from "@/pages/Settings";

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Authentication Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected Application Routes */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Overview />} />
            <Route path="/documents" element={<KnowledgeBase />} />
            <Route path="/chat" element={<AIInvestigation />} />
            <Route path="/agents" element={<AgentRuns />} />
            <Route path="/conversations" element={<Conversations />} />
            <Route path="/evaluation" element={<Evaluation />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>

          {/* Fallback Catch-all Route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;

