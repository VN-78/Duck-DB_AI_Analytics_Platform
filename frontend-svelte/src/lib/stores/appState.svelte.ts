import { type Message } from '$lib/types';

export interface Visualization {
    id: string;
    title: string;
    chartType: string;
    data: any[];
    spec: any;
}

class AppState {
    fileUri = $state<string | null>(null);
    fileName = $state<string | null>(null);
    messages = $state<Message[]>([]);
    isWorkspaceView = $state(false);
    error = $state<string | null>(null);
    
    // Pagination for DataTable
    tableData = $state<any[]>([]);
    tableColumns = $state<string[]>([]);
    totalRows = $state(0);
    currentPage = $state(0);
    pageSize = $state(10);
    isLoadingTable = $state(false);

    // Visualizations
    visualizations = $state<Visualization[]>([]);
    activeTab = $state('data');

    setFile(uri: string, name: string) {
        this.fileUri = uri;
        this.fileName = name;
        this.error = null;
    }

    reset() {
        this.fileUri = null;
        this.fileName = null;
        this.messages = [];
        this.isWorkspaceView = false;
        this.error = null;
        this.tableData = [];
        this.tableColumns = [];
        this.totalRows = 0;
        this.currentPage = 0;
        this.visualizations = [];
        this.activeTab = 'data';
    }

    async fetchTablePreview() {
        if (!this.fileUri) return;
        
        this.isLoadingTable = true;
        this.error = null;
        try {
            const offset = this.currentPage * this.pageSize;
            const response = await fetch(`/api/v1/files/preview?uri=${encodeURIComponent(this.fileUri)}&limit=${this.pageSize}&offset=${offset}`);
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to fetch preview');
            }
            
            const result = await response.json();
            this.tableData = result.data;
            this.tableColumns = result.columns;
            this.totalRows = result.total_rows;
        } catch (err: any) {
            this.error = err.message;
            console.error('Error fetching table preview:', err);
        } finally {
            this.isLoadingTable = false;
        }
    }

    addVisualization(viz: Visualization) {
        this.visualizations.push(viz);
        this.activeTab = viz.id;
    }
}

export const appState = new AppState();
