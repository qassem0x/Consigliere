export interface StepResult {
    step_number: number;
    step_description: string;
    detailed_description?: string;
    step_type: 'chart' | 'table' | 'metric' | 'summary';
    type: 'image' | 'table' | 'text' | 'error';
    data: any;
    description?: string;
    columns?: string[];
    total_rows?: number;
    mime?: string;
}

export interface ExecutionPlan {
    plan: Array<{
        step_number: number;
        type: string;
        description: string;
        depends_on: number[];
    }>;
    reasoning: string;
}

export interface ChatType {
    id: string;
    title: string | null;
    created_at: string;
    file_id?: string | null;
    connection_id?: string | null;
    type?: string;
    file?: {
        file_path: string;
        filename: string;
    };
    settings?: {
        zero_leaks_mode: boolean;
        max_row_limit: number;
    };
}

export interface Dossier {
    briefing: string;
    key_entities: string[];
    recommended_actions: string[];
}

export interface Message {
    id?: string;
    role: 'user' | 'assistant';
    content: string;
    created_at?: string;
    tableData?: any;
    imageData?: any;
    steps?: StepResult[];
    plan?: any;
    related_code?: {
        type: string;
        code: string;
    } | null;
    streamingStatus?: 'planning' | 'processing' | 'complete' | 'error' | 'cancelled';
    currentStep?: number;
}
