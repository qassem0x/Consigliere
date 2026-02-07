export interface Message {
    id?: string;
    role: 'user' | 'assistant';
    content: string;
    created_at?: string;
    
    tableData?: any[];
    imageData?: string;
    
    related_code?: {
        type: string;
        code: string;
    } | null;
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

export interface ChatType {
    id: string
    title: string | null
    file_id: string
    created_at: string
    type: string
}

export interface Dossier {
  file_type: string;
  briefing: string;
  key_entities: string[];
  recommended_actions: string[];
}

export interface FileUploadResult {
  status: string;
  file_id: string;
  filename: string;
}

export interface AnalysisResult {
  status: string;
  chat_id: string;
  dossier: Dossier;
}