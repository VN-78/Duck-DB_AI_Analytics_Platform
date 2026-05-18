<script lang="ts">
	import * as Tabs from '$lib/components/ui/tabs';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import {
		TableProperties,
		BarChart3,
		Filter,
		ChevronLeft,
		ChevronRight,
		Loader2,
		X,
		Search
	} from '@lucide/svelte';
	import { appState, type Visualization } from '$lib/stores/appState.svelte';
	import GenericDataTable from './GenericDataTable.svelte';
	import type { ColumnDef } from '@tanstack/table-core';
	import vegaEmbed from 'vega-embed';

	let showFilter = $state(false);
	let filterValue = $state('');

	// Dynamically generate column definitions based on the current table columns
	let columns = $derived<ColumnDef<any, any>[]>(
		appState.tableColumns.map((col) => ({
			accessorKey: col,
			header: col,
			cell: (info) => info.getValue()
		}))
	);

	async function nextPage() {
		if ((appState.currentPage + 1) * appState.pageSize < appState.totalRows) {
			appState.currentPage += 1;
			await appState.fetchTablePreview();
		}
	}

	async function prevPage() {
		if (appState.currentPage > 0) {
			appState.currentPage -= 1;
			await appState.fetchTablePreview();
		}
	}

	function removeVisualization(id: string, event: MouseEvent) {
		event.stopPropagation();
		appState.visualizations = appState.visualizations.filter((v) => v.id !== id);
		if (appState.activeTab === id) {
			appState.activeTab = 'data';
		}
	}

	function toggleFilter() {
		showFilter = !showFilter;
		if (!showFilter) filterValue = '';
	}

	/**
	 * Svelte action to render Vega-Lite.
	 * Bypasses Svelte 5 proxy issues by stripping reactivity with JSON serialization.
	 */
	function renderVega(node: HTMLElement, viz: Visualization) {
		const render = async (v: Visualization) => {
			try {
				console.log('Rendering Vega-Lite viz:', v.id, v.title);
				
				// Using JSON parse/stringify is the most reliable way to strip 
				// Svelte 5 proxies and ensure Vega receives a plain JS object.
				const spec = JSON.parse(JSON.stringify(v.spec));
				const data = JSON.parse(JSON.stringify(v.data));
				
				// Inject data into spec values
				spec.data = { values: data };
				
				console.log('Final Vega spec:', spec);

				await vegaEmbed(node, spec, {
					actions: {
						export: true,
						source: false,
						compiled: false,
						editor: true
					},
					theme: 'dark',
					width: node.clientWidth || 600,
					height: 300,
					renderer: 'svg'
				});
				console.log('Vega rendering successful for:', v.id);
			} catch (err) {
				console.error('Vega rendering failed for:', v.id, err);
				node.innerHTML = `<div class="p-4 text-destructive border border-destructive/20 bg-destructive/10 rounded-lg text-sm">
					Failed to render visualization: ${err instanceof Error ? err.message : String(err)}
				</div>`;
			}
		};

		// Initial render
		render(viz);

		return {
			update(newViz: Visualization) {
				console.log('Updating Vega-Lite viz:', newViz.id);
				render(newViz);
			}
		};
	}
</script>

<div class="flex flex-col h-full bg-card border-l">
	<Tabs.Root bind:value={appState.activeTab} class="flex flex-col h-full">
		<Tabs.List
			class="w-full justify-start rounded-none border-b bg-muted/50 px-2 h-12 overflow-x-auto overflow-y-hidden no-scrollbar"
		>
			<Tabs.Trigger
				value="data"
				class="gap-2 data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-full bg-transparent shrink-0"
			>
				<TableProperties class="w-4 h-4" />
				Data
			</Tabs.Trigger>

			{#each appState.visualizations as viz}
				<Tabs.Trigger
					value={viz.id}
					class="gap-2 data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-full bg-transparent group shrink-0"
				>
					<BarChart3 class="w-4 h-4" />
					<span class="max-w-25 truncate">{viz.title}</span>
					<button
						class="ml-1 p-0.5 rounded-full hover:bg-muted opacity-0 group-hover:opacity-100 transition-opacity"
						onclick={(e) => removeVisualization(viz.id, e)}
					>
						<X class="w-3 h-3" />
					</button>
				</Tabs.Trigger>
			{/each}
		</Tabs.List>

		<Tabs.Content value="data" class="flex-1 flex flex-col p-0 m-0 overflow-hidden">
			<!-- Toolbar -->
			<div class="p-4 border-b flex flex-col gap-4 bg-card">
				<div class="flex justify-between items-center">
					<div class="flex items-center gap-3">
						<h3 class="font-medium text-lg truncate max-w-50 md:max-w-xs">
							{appState.fileName || 'Dataset Preview'}
						</h3>
						{#if appState.isLoadingTable}
							<Loader2 class="w-4 h-4 animate-spin text-muted-foreground" />
						{/if}
					</div>
					<div class="flex gap-2">
						<Button 
							variant={showFilter ? "secondary" : "outline"} 
							size="icon" 
							class="h-8 w-8 {showFilter ? 'bg-primary/10 border-primary/20 text-primary' : ''}"
							onclick={toggleFilter}
						>
							<Filter class="w-4 h-4" />
						</Button>
					</div>
				</div>

				{#if showFilter}
					<div class="relative group animate-in fade-in slide-in-from-top-1 duration-200">
						<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
						<Input 
							bind:value={filterValue} 
							placeholder="Search in current page..." 
							class="pl-9 h-9 bg-muted/50 border-border/50 focus:bg-background transition-all rounded-xl"
							autofocus
						/>
						{#if filterValue}
							<button 
								class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
								onclick={() => filterValue = ''}
							>
								<X class="w-3.5 h-3.5" />
							</button>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Data Table Container -->
			<div class="flex-1 overflow-auto p-4 bg-muted/30">
				{#if appState.tableData.length > 0}
					<GenericDataTable data={appState.tableData} {columns} {filterValue} />
				{:else if appState.isLoadingTable}
					<div class="flex flex-col items-center justify-center h-64 border rounded-lg bg-card">
						<Loader2 class="w-8 h-8 animate-spin text-primary mb-4" />
						<p class="text-sm text-muted-foreground">Loading dataset...</p>
					</div>
				{:else}
					<div
						class="flex flex-col items-center justify-center h-64 border border-dashed rounded-lg bg-card"
					>
						<TableProperties class="w-12 h-12 text-muted mb-4 opacity-20" />
						<p class="text-sm text-muted-foreground">No data available to preview.</p>
					</div>
				{/if}

				<!-- Pagination -->
				{#if appState.totalRows > 0}
					<div class="mt-4 flex justify-between items-center px-1">
						<span class="text-xs text-muted-foreground font-mono">
							Showing {appState.currentPage * appState.pageSize + 1}-{Math.min(
								(appState.currentPage + 1) * appState.pageSize,
								appState.totalRows
							)} of {appState.totalRows} rows
						</span>
						<div class="flex gap-2">
							<Button
								variant="outline"
								size="sm"
								onclick={prevPage}
								disabled={appState.currentPage === 0 || appState.isLoadingTable}
							>
								<ChevronLeft class="w-4 h-4 mr-1" />
								Prev
							</Button>
							<Button
								variant="outline"
								size="sm"
								onclick={nextPage}
								disabled={(appState.currentPage + 1) * appState.pageSize >= appState.totalRows ||
									appState.isLoadingTable}
							>
								Next
								<ChevronRight class="w-4 h-4 ml-1" />
							</Button>
						</div>
					</div>
				{/if}
			</div>
		</Tabs.Content>

		{#each appState.visualizations as viz}
			<Tabs.Content
				value={viz.id}
				class="flex-1 flex flex-col p-0 m-0 overflow-hidden bg-muted/30"
			>
				<div class="p-4 border-b flex justify-between items-center bg-card">
					<h3 class="font-medium text-lg truncate">{viz.title}</h3>
					<div class="flex gap-2">
					</div>
				</div>
				<div class="flex-1 p-6 flex items-center justify-center overflow-auto">
					<div class="w-full max-w-4xl bg-card border rounded-xl p-6 shadow-sm overflow-hidden min-h-100 flex items-center justify-center">
						<div use:renderVega={viz} class="w-full h-full min-h-75"></div>
					</div>
				</div>
			</Tabs.Content>
		{/each}
	</Tabs.Root>
</div>

<style>
	:global(.no-scrollbar::-webkit-scrollbar) {
		display: none;
	}
	:global(.no-scrollbar) {
		-ms-overflow-style: none;
		scrollbar-width: none;
	}
</style>
