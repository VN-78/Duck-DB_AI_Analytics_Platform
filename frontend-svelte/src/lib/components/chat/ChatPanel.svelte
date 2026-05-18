<script lang="ts">
	import * as InputGroup from '$lib/components/ui/input-group';
	import { Button } from '$lib/components/ui/button';
	import { SendHorizontal, PlusCircle, Bot, User, Loader2 } from '@lucide/svelte';
	import { appState } from '$lib/stores/appState.svelte';
	import { onMount } from 'svelte';
	import { marked } from 'marked';
	import DOMPurify from 'isomorphic-dompurify';

	let currentPrompt = $state('');
	let isThinking = $state(false);
	let chatContainer: HTMLDivElement;

	function renderMarkdown(content: string) {
		return DOMPurify.sanitize(marked.parse(content, { breaks: true }) as string);
	}

	function scrollToBottom() {
		if (chatContainer) {
			chatContainer.scrollTop = chatContainer.scrollHeight;
		}
	}

	onMount(() => {
		// If we already have a user message from the landing page, trigger the agent
		if (appState.messages.length === 1 && appState.messages[0].role === 'user') {
			runAgent();
		}
	});

	async function runAgent() {
		if (isThinking || !appState.fileUri) return;

		isThinking = true;
		const messages = [...appState.messages];
		
		try {
			const response = await fetch('/api/v1/agent/run', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					messages,
					file_uri: appState.fileUri
				})
			});

			if (!response.body) return;

			const reader = response.body.getReader();
			const decoder = new TextDecoder();
			let assistantMessage = '';
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				
				// Keep the last partial line in the buffer
				buffer = lines.pop() || '';

				for (const line of lines) {
					if (!line.trim() || !line.startsWith('data: ')) continue;
					
					try {
						const jsonStr = line.slice(6).trim();
						if (!jsonStr) continue;
						
						const data = JSON.parse(jsonStr);
						console.log('Received SSE event:', data.status, data.tool || '');
						
						if (data.status === 'complete') {
							assistantMessage = data.message;
							// Update state with final message
							appState.messages.push({ role: 'assistant', content: assistantMessage });
						} else if (data.status === 'history_update') {
							// Sync history if needed
						} else if (data.status === 'success') {
							if (data.tool === 'preview_dataset') {
								await appState.fetchTablePreview();
							} else if (data.tool === 'generate_visualization') {
								try {
									const vizData = JSON.parse(data.result);
									if (vizData.type === 'vega_lite') {
										appState.addVisualization({
											id: `viz-${Date.now()}`,
											title: vizData.spec.title || 'New Visualization',
											chartType: vizData.chart_type,
											data: vizData.data,
											spec: vizData.spec
										});
									}
								} catch (e) {
									console.error('Failed to parse visualization data:', e);
								}
							}
						}
					} catch (e) {
						console.error('Error parsing SSE line:', line, e);
					}
				}
				scrollToBottom();
			}
		} catch (error) {
			console.error('Agent run failed:', error);
		} finally {
			isThinking = false;
			scrollToBottom();
		}
	}

	async function handleSubmit() {
		if (!currentPrompt.trim() || isThinking) return;

		appState.messages.push({ role: 'user', content: currentPrompt });
		const promptToSubmit = currentPrompt;
		currentPrompt = '';
		scrollToBottom();
		await runAgent();
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSubmit();
		}
	}
</script>

<div class="flex flex-col h-full bg-background relative overflow-hidden">
	<!-- Chat Header -->
	<div class="px-6 py-4 border-b bg-card/50 backdrop-blur sticky top-0 z-10 flex items-center justify-between">
		<div class="flex items-center gap-3">
			<Bot class="w-5 h-5 text-primary" />
			<h2 class="font-semibold text-lg truncate max-w-[200px] md:max-w-md">
				{appState.fileName ? `Analysis: ${appState.fileName}` : 'Analysis Workspace'}
			</h2>
		</div>
		<div class="flex gap-2">
			<div class="px-2 py-1 bg-secondary border rounded-md text-[10px] uppercase font-mono text-muted-foreground flex items-center gap-1.5">
				<span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
				Live Session
			</div>
		</div>
	</div>

	<!-- Chat History -->
	<div bind:this={chatContainer} class="flex-1 overflow-y-auto px-4 py-8 space-y-8 scroll-smooth">
		<div class="max-w-2xl mx-auto flex flex-col gap-8">
			{#each appState.messages as msg}
				<div class="flex flex-col gap-2 {msg.role === 'user' ? 'items-end' : 'items-start'}">
					<div class="flex items-center gap-2 mb-1 px-1">
						{#if msg.role === 'assistant'}
							<Bot class="w-4 h-4 text-primary" />
							<span class="text-xs font-mono text-muted-foreground">Analytica</span>
						{:else if msg.role === 'user'}
							<span class="text-xs font-mono text-muted-foreground">You</span>
							<User class="w-4 h-4 text-muted-foreground" />
						{/if}
					</div>
					
					<div class="max-w-[90%] p-4 rounded-2xl border transition-all
						{msg.role === 'user' 
							? 'bg-secondary/30 border-primary/20 rounded-tr-sm text-foreground' 
							: 'bg-card border-border rounded-tl-sm text-foreground shadow-sm'}">
						<div class="prose prose-sm dark:prose-invert max-w-none">
							{@html renderMarkdown(msg.content)}
						</div>
					</div>
				</div>
			{/each}

			{#if isThinking}
				<div class="flex flex-col items-start gap-2">
					<div class="flex items-center gap-2 mb-1 px-1">
						<Bot class="w-4 h-4 text-primary" />
						<span class="text-xs font-mono text-muted-foreground">Analytica is thinking...</span>
					</div>
					<div class="bg-card border border-border p-4 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-3">
						<Loader2 class="w-5 h-5 animate-spin text-primary" />
						<span class="text-sm text-muted-foreground italic">Processing data refinery...</span>
					</div>
				</div>
			{/if}
		</div>
	</div>

	<!-- Bottom Input Area -->
	<div class="p-4 bg-gradient-to-t from-background via-background to-transparent border-t mt-auto">
		<div class="max-w-2xl mx-auto relative group">
			<InputGroup.Root class="bg-card border-border focus-within:border-primary/50 transition-all rounded-xl shadow-lg p-0.5">
				<InputGroup.Addon>
					<Button variant="ghost" size="icon" class="text-muted-foreground hover:text-foreground">
						<PlusCircle class="w-5 h-5" />
					</Button>
				</InputGroup.Addon>
				<InputGroup.Textarea
					bind:value={currentPrompt}
					onkeydown={handleKeyDown}
					placeholder="Ask about the data..."
					class="min-h-[48px] py-3 text-sm bg-transparent border-none focus-visible:ring-0 resize-none"
				/>
				<InputGroup.Addon align="inline-end">
					<Button 
						variant="default" 
						size="icon" 
						class="rounded-lg h-9 w-9 bg-primary text-primary-foreground hover:opacity-90 transition-all"
						disabled={!currentPrompt.trim() || isThinking}
						onclick={handleSubmit}
					>
						<SendHorizontal class="w-4 h-4" />
					</Button>
				</InputGroup.Addon>
			</InputGroup.Root>
			<div class="mt-2 flex justify-center">
				<span class="text-[10px] text-muted-foreground font-mono uppercase tracking-widest opacity-60">
					Shift + Enter for new line
				</span>
			</div>
		</div>
	</div>
</div>
