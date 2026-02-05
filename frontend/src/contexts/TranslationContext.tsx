import React, { createContext, useState, useCallback } from 'react';

const translations = {
  en: {
    title: "Consigliere",
    nav: {
      features: "Architecture",
      process: "The Logic",
      enterprise: "Self-Hosted",
      start: "CONSULT NOW",
      login: "SIGN IN",
      register: "DEPLOY"
    },
    hero: {
      status: "Confidential Node Active • Local Execution Mode",
      tagline: "The AI Analyst that respects Omertà.",
      headline: "Your Intelligence,",
      headlineSpan: "Privately Decoded.",
      subheadline: "The self-hosted analyst that solves the security risk of public AI. It runs locally, executes code on your iron, and never sends your data rows to the cloud. Only schemas leave; your secrets stay home.",
      ctaPrimary: "Connect Local Source",
      ctaSecondary: "Zero-Leak Protocol",
      nodes: {
        excel: "EXCEL / CSV",
        db: "SQL DATABASES",
        json: "JSON / REST API",
        docs: "DOCUMENTS"
      }
    },
    auth: {
      loginTitle: "Access Secure Node",
      registerTitle: "Establish Sovereign Identity",
      email: "Administrative Email",
      password: "Create Password",
      name: "Full Name",
      company: "Organization / Project",
      forgot: "Forgot credentials?",
      noAccount: "Not an authorized user?",
      hasAccount: "Already have a node?",
      submitLogin: "IDENTIFY",
      submitRegister: "INITIALIZE DEPLOYMENT",
      socialLogin: "Authenticate with GitHub"
    },
    connect: {
      title: "Establish Secure Link",
      subtitle: "Select your intelligence source. All processing remains within your local perimeter.",
      step1: "Choose Source Type",
      step2: "Connection Parameters",
      excelTitle: "Spreadsheets",
      excelDesc: "Excel, CSV, or OpenDocument files",
      pdfTitle: "Documents",
      pdfDesc: "Unstructured PDF reports & dossiers",
      mysqlTitle: "MySQL / MariaDB",
      mysqlDesc: "Direct local relational link",
      postgresTitle: "PostgreSQL",
      postgresDesc: "Advanced enterprise relational link",
      back: "Return to selection",
      cancel: "Abort Linkage",
      connect: "ESTABLISH LINK",
      upload: "Upload File",
      host: "Internal Host / IP",
      port: "Port",
      user: "Database User",
      pass: "Database Password",
      dbName: "Database Name",
      placeholderFile: "Drag and drop or browse files"
    },
    ticker: {
      insights: "Local Queries Handled: 842,109",
      active: "Encrypted Sessions: 12,042",
      uptime: "System Integrity: Verified",
      latency: "Local Execution: 12ms",
      encrypted: "Architecture: Zero-Trust Schema-Only"
    },
    features: {
      headline: "Absolute Data Sovereignty",
      subheadline: "Why gamble with public LLMs when you can have a Consigliere that never talks to strangers?",
      f1: { t: "Schema-Only Sync", d: "We only share column names with the AI. Your actual rows never touch the cloud. Ever." },
      f2: { t: "Local Execution", d: "The AI writes Python or SQL—Consigliere executes it instantly on your own hardware." },
      f3: { t: "Self-Hosted Privacy", d: "Dockerized deployment for your private VPC. No third-party access, no external logs." },
      f4: { t: "Dual-Output Engine", d: "High-level strategic summaries paired with interactive, locally-rendered data grids." },
      f5: { t: "Code-First Logic", d: "Bypass manual pivot tables. Consigliere writes the analysis code so you don't have to." },
      f6: { t: "Zero Technical Debt", d: "Non-technical users can dialogue with complex datasets using pure natural language." }
    },
    howItWorks: {
      headline: "The Code of Silence",
      s1: { t: "Local Mounting", d: "Mount your volumes or connect your DB. Data stays within your firewall." },
      s2: { t: "Schema Extraction", d: "Only metadata is used for context. Your proprietary records stay on the iron." },
      s3: { t: "Safe Execution", d: "Analysis happens in a local sandbox. You get the verdict without the leak." }
    },
    cta: {
      headline: "Your Data, Your Rules.",
      subheadline: "Experience the 'digital employee' that respects your secrets. No cloud uploads, no technical compromises. Just absolute clarity.",
      button: "Deploy Your Consigliere"
    },
    tool: {
      exit: "Close Dossier",
      placeholder: "Inquire about trends, anomalies, or summaries...",
      thinking: "Computing...",
      disclaimer: "Zero-Leak Architecture",
      sidebar: {
        dossier: "Active Dossier",
        schema: "Technical Schema",
        insights: "Automated Leads",
        clear: "Purge History"
      }
    }
  }
};

export type Language = 'en';

interface TranslationContextType {
  lang: Language;
  setLang: (lang: Language) => void;
  t: (typeof translations)['en'];
}

export const TranslationContext = createContext<TranslationContextType | undefined>(undefined);

export const TranslationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lang, setLang] = useState<Language>('en');

  const changeLanguage = useCallback((newLang: Language) => {
    setLang(newLang);
    document.documentElement.lang = newLang;
    document.documentElement.dir = 'ltr';
  }, []);

  const value: TranslationContextType = {
    lang,
    setLang: changeLanguage,
    t: translations[lang]
  };

  return (
    <TranslationContext.Provider value={value}>
      {children}
    </TranslationContext.Provider>
  );
};

export const useTranslation = () => {
  const context = React.useContext(TranslationContext);
  if (!context) {
    throw new Error('useTranslation must be used within TranslationProvider');
  }
  return context;
};
