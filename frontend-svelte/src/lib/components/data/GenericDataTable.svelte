<script lang="ts" generics="TData, TValue">
	import {
		getCoreRowModel,
		getFilteredRowModel,
		type ColumnDef,
	} from '@tanstack/table-core';
	import {
		createSvelteTable,
		FlexRender
	} from '$lib/components/ui/data-table/index.js';
	import * as Table from '$lib/components/ui/table/index.js';

	type DataTableProps<TData, TValue> = {
		columns: ColumnDef<TData, TValue>[];
		data: TData[];
		filterValue?: string;
	};

	let { data, columns, filterValue = '' }: DataTableProps<TData, TValue> = $props();

	const table = createSvelteTable({
		get data() {
			return data;
		},
		get columns() {
			return columns;
		},
		state: {
			get globalFilter() {
				return filterValue;
			}
		},
		getCoreRowModel: getCoreRowModel(),
		getFilteredRowModel: getFilteredRowModel(),
		onGlobalFilterChange: (updater) => {
			// This is handled by the parent via filterValue prop, 
			// but we need the hook for TanStack to work.
		}
	});
</script>

<div class="rounded-md border bg-card">
	<Table.Root>
		<Table.Header class="bg-muted/50">
			{#each table.getHeaderGroups() as headerGroup (headerGroup.id)}
				<Table.Row>
					{#each headerGroup.headers as header (header.id)}
						<Table.Head colspan={header.colSpan} class="font-mono text-[10px] uppercase tracking-wider">
							{#if !header.isPlaceholder}
								<FlexRender
									content={header.column.columnDef.header}
									context={header.getContext()}
								/>
							{/if}
						</Table.Head>
					{/each}
				</Table.Row>
			{/each}
		</Table.Header>
		<Table.Body>
			{#each table.getRowModel().rows as row (row.id)}
				<Table.Row data-state={row.getIsSelected() && 'selected'} class="hover:bg-muted/30 transition-colors">
					{#each row.getVisibleCells() as cell (cell.id)}
						<Table.Cell class="font-mono text-xs whitespace-nowrap">
							<FlexRender
								content={cell.column.columnDef.cell}
								context={cell.getContext()}
							/>
						</Table.Cell>
					{/each}
				</Table.Row>
			{:else}
				<Table.Row>
					<Table.Cell colspan={columns.length} class="h-24 text-center text-muted-foreground">
						No results.
					</Table.Cell>
				</Table.Row>
			{/each}
		</Table.Body>
	</Table.Root>
</div>
