<script lang="ts">
	import LandingView from '$lib/components/views/LandingView.svelte';
	import WorkspaceView from '$lib/components/views/WorkspaceView.svelte';
	import { appState } from '$lib/stores/appState.svelte';
</script>

{#if !appState.isWorkspaceView}
	<LandingView />
{:else}
	<WorkspaceView />
{/if}
