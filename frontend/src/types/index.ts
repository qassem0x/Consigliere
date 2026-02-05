export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ExcelData {
  fileName: string;
  sheets: {
    name: string;
    data: any[];
    headers: string[];
  }[];
}

export interface AnalysisState {
  isAnalyzing: boolean;
  result: string | null;
  error: string | null;
}
