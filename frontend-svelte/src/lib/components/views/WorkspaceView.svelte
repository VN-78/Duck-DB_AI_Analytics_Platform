<script lang="ts">
	import ChatPanel from '../chat/ChatPanel.svelte';
	import DataPanel from '../data/DataPanel.svelte';
</script>

<!-- Workspace container: Side-by-side on tablet (md) and larger, stacked on mobile -->
<div class="grid grid-cols-1 md:grid-cols-2 md:h-[calc(100vh-3.5rem)] bg-background relative z-30">
	<!-- Left Panel: Chat -->
	<div class="h-[70vh] md:h-full border-b md:border-b-0 md:border-r overflow-hidden flex flex-col">
		<ChatPanel />
	</div>
	
	<!-- Right Panel: Data (Table/Charts) -->
	<div class="h-[70vh] md:h-full overflow-hidden flex flex-col">
		<DataPanel />
	</div>
</div>
