import { setMode } from "mode-watcher";

/**
 * Handles the View Transition API for theme switching.
 * @param isDark - The target theme state.
 * @param event - The mouse event to extract coordinates from (null if keyboard).
 */

export function toggleThemeWithTransition(isDark: boolean, event: MouseEvent | null) {

    const applyTheme = () => {
        const root = document.documentElement;
        console.log(`Applying theme: ${isDark ? 'dark' : 'light'}`);
        if (isDark) {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }
        setMode(isDark ? 'dark' : 'light');
    };

    // Fallback: If View Transitions aren't supported, OR if the user triggered 
    // the switch via keyboard (no X/Y coordinates), just switch instantly.
    if (!document.startViewTransition || !event) {
        applyTheme();
        return;
    }

    const x = event.clientX;
    const y = event.clientY;

    // 1. Start transition and update DOM inside the callback
    const transition = document.startViewTransition(() => applyTheme());

    // 2. Animate the new pseudo-element
    transition.ready.then(() => {
        const radius = Math.hypot(
            Math.max(x, innerWidth - x),
            Math.max(y, innerHeight - y)
        );

        document.documentElement.animate(
            {
                clipPath: [
                    `circle(0px at ${x}px ${y}px)`,
                    `circle(${radius}px at ${x}px ${y}px)`
                ]
            },
            {
                duration: 500,
                easing: 'ease-in-out',
                pseudoElement: '::view-transition-new(root)'
            }
        );
    });
}
