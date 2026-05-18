<script lang="ts">
	import * as Empty from '$lib/components/ui/empty';
	import * as InputGroup from '$lib/components/ui/input-group';
	import { Button } from '$lib/components/ui/button';
	import { CloudUpload, PlusCircle, SendHorizontal, Database, HardDrive, Loader2 } from '@lucide/svelte';
	import { appState } from '$lib/stores/appState.svelte';

	let initialPrompt = $state('');
	let isUploading = $state(false);
	let fileInput: HTMLInputElement;

	async function handleFileUpload(event: Event) {
		const target = event.target as HTMLInputElement;
		const file = target.files?.[0];
		if (!file) return;

		isUploading = true;
		const formData = new FormData();
		formData.append('file', file);

		try {
			console.log('Starting upload for:', file.name);
			const response = await fetch('/api/v1/files/upload', {
				method: 'POST',
				body: formData
			});
			if (!response.ok) throw new Error('Upload failed');
			
			const result = await response.json();
			console.log('Upload successful, URI:', result.uri);
			appState.setFile(result.uri, file.name);
			// Fetch initial preview
			await appState.fetchTablePreview();
		} catch (error) {
			console.error('Upload failed:', error);
			appState.error = 'Failed to upload file. Please try again.';
		} finally {
			isUploading = false;
		}
	}

	function handleSubmitPrompt() {
		console.log('Submit prompted. Prompt:', initialPrompt, 'FileURI:', appState.fileUri);
		if (!initialPrompt.trim() || !appState.fileUri) {
			console.warn('Submit blocked: prompt or file missing');
			return;
		}

		// Add user message to state
		appState.messages.push({ role: 'user', content: initialPrompt });
		// Transition to workspace
		console.log('Transitioning to workspace view');
		appState.isWorkspaceView = true;
	}

    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSubmitPrompt();
        }
    }
</script>

<div class="container mx-auto flex flex-col items-center justify-center min-h-[calc(100vh-3.5rem)] px-4 py-12 max-w-2xl">
	<div class="text-center mb-10 w-full">
		<h2 class="text-3xl md:text-5xl font-bold text-primary mb-4">Initialize Analysis</h2>
		<p class="text-muted-foreground text-lg max-w-md mx-auto">
			Upload your dataset to begin generating insights. Supported formats: CSV, JSON, Parquet, or SQL Dumps.
		</p>
	</div>

	<Empty.Root 
		class="w-full bg-card border-dashed p-12 md:p-24 transition-colors hover:bg-muted/50 cursor-pointer group rounded-[2.5rem] shadow-md min-h-[520px] flex flex-col justify-center items-center relative overflow-hidden" 
		onclick={() => !isUploading && fileInput.click()}
	>
		{#if isUploading}
			<div class="absolute inset-0 bg-background/50 backdrop-blur-sm flex flex-col items-center justify-center z-10">
				<Loader2 class="w-12 h-12 animate-spin text-primary mb-4" />
				<span class="text-lg font-medium animate-pulse">Uploading Dataset...</span>
			</div>
		{/if}

		<input type="file" class="hidden" bind:this={fileInput} onchange={handleFileUpload} accept=".csv,.json,.parquet" />
		<Empty.Header class="flex flex-col items-center text-center">
			<Empty.Media variant="icon" class="bg-secondary p-5 rounded-full group-hover:bg-accent transition-colors mb-8">
				<CloudUpload class="w-10 h-10 text-primary" />
			</Empty.Media>
			<Empty.Title class="text-3xl md:text-4xl font-bold tracking-tight">
				{appState.fileName ? appState.fileName : 'Drag & drop files here'}
			</Empty.Title>
			<Empty.Description class="text-base md:text-xl mt-3 text-muted-foreground/80">
				{appState.fileName ? 'File ready for analysis' : 'or click to browse from your computer'}
			</Empty.Description>
		</Empty.Header>
		<Empty.Content class="mt-10 flex flex-col items-center gap-8 w-full max-w-sm mx-auto">
			{#if !appState.fileName}
				<Button variant="default" class="w-full py-7 text-xl font-semibold rounded-2xl shadow-lg transition-transform hover:scale-[1.02] active:scale-[0.98]">
					Select Files
				</Button>
			{/if}
			
			<div class="flex gap-4 w-full justify-center">
				<div class="flex-1 flex items-center justify-center gap-2 bg-secondary/40 border border-border/50 px-4 py-2.5 rounded-xl text-muted-foreground text-[10px] font-bold uppercase tracking-[0.2em]">
					<HardDrive class="w-3.5 h-3.5" />
					AWS S3
				</div>
				<div class="flex-1 flex items-center justify-center gap-2 bg-secondary/40 border border-border/50 px-4 py-2.5 rounded-xl text-muted-foreground text-[10px] font-bold uppercase tracking-[0.2em]">
					<Database class="w-3.5 h-3.5" />
					PostgreSQL
				</div>
			</div>
		</Empty.Content>
	</Empty.Root>

	<!-- Spacer to prevent overlap with fixed input -->
	<div class="h-40 w-full shrink-0"></div>

	<!-- Chat Input Anchored at Bottom -->
	<div class="fixed bottom-0 left-0 w-full p-6 md:p-12 flex justify-center bg-gradient-to-t from-background via-background/90 to-transparent pointer-events-none z-20">
		<div class="w-full max-w-2xl pointer-events-auto">
			{#if appState.error}
				<div class="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive text-sm text-center">
					{appState.error}
				</div>
			{/if}
			<InputGroup.Root class="bg-card shadow-2xl border-primary/20 focus-within:border-primary transition-all rounded-xl p-1">
				<InputGroup.Addon>
					<Button variant="ghost" size="icon" class="text-muted-foreground hover:text-foreground">
						<PlusCircle class="w-5 h-5" />
					</Button>
				</InputGroup.Addon>
				<InputGroup.Textarea
					bind:value={initialPrompt}
                    onkeydown={handleKeyDown}
					placeholder={appState.fileUri ? "Describe the analysis you want to perform..." : "Upload a file first to begin..."}
					disabled={!appState.fileUri || isUploading}
					class="min-h-[56px] py-4 text-base bg-transparent border-none focus-visible:ring-0 resize-none disabled:opacity-50"
				/>
				<InputGroup.Addon align="inline-end">
					<Button 
						variant="default" 
						size="icon" 
						class="rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-all"
						disabled={!initialPrompt.trim() || !appState.fileUri || isUploading}
						onclick={handleSubmitPrompt}
					>
						<SendHorizontal class="w-5 h-5" />
					</Button>
				</InputGroup.Addon>
			</InputGroup.Root>
			<div class="text-center mt-3">
				<span class="text-xs text-muted-foreground font-mono">
					Entropy AI v1.0 • Shift + Enter for new line
				</span>
			</div>
		</div>
	</div>
</div>
