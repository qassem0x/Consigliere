import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { TranslationProvider } from './src/contexts/TranslationContext';
import { AuthProvider } from './src/contexts/AuthContext';
import { LoadingSpinner } from './src/components';
import {
  LandingPage,
  LoginPage,
  RegisterPage,
} from './src/pages';
import { ExcelData, Message } from './types';
import { useAuth } from './src/contexts/AuthContext';
import { DashboardPage } from './src/pages/DashboardPage';
import ProtectedRoute from './src/components/ProtectedRoute';

function AppContent() {
  const [excelData, setExcelData] = useState<ExcelData | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const { isLoading } = useAuth();

  const handleDataLoaded = (data: ExcelData, initialMessages: Message[]) => {
    setExcelData(data);
    setMessages(initialMessages);
  };

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <DashboardPage />
        </ProtectedRoute>
      } />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <TranslationProvider>
      <Router>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </Router>
    </TranslationProvider>
  );
}
