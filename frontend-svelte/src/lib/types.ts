export interface Message {
    role: 'system' | 'user' | 'assistant' | 'tool';
    content: string;
    tool_calls?: ToolCall[];
    tool_call_id?: string;
}

export interface ToolCall {
    id: string;
    type: 'function';
    function: {
        name: string;
        arguments: string;
    };
}

export interface TablePreviewResponse {
    columns: string[];
    data: Record<string, any>[];
    total_rows: number;
    limit: number;
    offset: number;
}
