<script lang="ts">
	import ThemeToggle from './ThemeToggle.svelte';
</script>

<header class="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
	<div class="container mx-auto flex h-14 items-center justify-between px-4 sm:px-8">
		<div class="flex items-center gap-2">
			<a href="/" class="flex items-center space-x-2">
				<span class="inline-block font-bold sm:inline-block">
					Entropy
				</span>
			</a>
		</div>
		<div class="flex items-center gap-2">
			<ThemeToggle />
		</div>
	</div>
</header>
