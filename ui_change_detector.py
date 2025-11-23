"""UI change detector using DOM mutation observers."""

import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


class UIChangeDetector:
    """Detects UI state changes using MutationObserver injected into the page."""

    def __init__(self, browser_session: Any, change_callback: Callable[[], Any] | None = None):
        """Initialize the UI change detector.

        Args:
            browser_session: Browser-use BrowserSession instance
            change_callback: Async callback function to call when UI changes are detected
        """
        self.browser_session = browser_session
        self.change_callback = change_callback
        self._observer_script_injected = False
        self._last_dom_hash: str | None = None
        self._debounce_task: asyncio.Task | None = None
        self._debounce_delay = 0.3  # 300ms debounce to avoid too many captures

    async def start_monitoring(self):
        """Inject MutationObserver script and start monitoring for UI changes."""
        if self._observer_script_injected:
            return

        # JavaScript code to inject MutationObserver
        observer_script = """
        (function() {
            if (window.__uiChangeObserver) {
                return; // Already injected
            }

            let changeDetected = false;
            let debounceTimeout = null;
            const DEBOUNCE_MS = 300;

            function notifyChange() {
                changeDetected = true;
                if (debounceTimeout) {
                    clearTimeout(debounceTimeout);
                }
                debounceTimeout = setTimeout(() => {
                    // Signal change via custom event
                    window.dispatchEvent(new CustomEvent('__uiStateChanged', {
                        detail: { timestamp: Date.now() }
                    }));
                    changeDetected = false;
                }, DEBOUNCE_MS);
            }

            // Create MutationObserver
            const observer = new MutationObserver((mutations) => {
                // Check for significant changes
                for (const mutation of mutations) {
                    // Detect modal/overlay appearances
                    if (mutation.type === 'childList' || mutation.type === 'attributes') {
                        const target = mutation.target;
                        
                        // Check for common modal/overlay indicators
                        if (target.nodeType === 1) { // Element node
                            const style = window.getComputedStyle(target);
                            const display = style.display;
                            const visibility = style.visibility;
                            const opacity = style.opacity;
                            const zIndex = style.zIndex;
                            
                            // Detect modal/overlay appearance
                            if (display !== 'none' && 
                                visibility !== 'hidden' && 
                                parseFloat(opacity) > 0 &&
                                (zIndex === 'auto' || parseInt(zIndex) > 1000)) {
                                notifyChange();
                                break;
                            }
                            
                            // Check for class changes that might indicate state changes
                            if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                                const classList = target.classList;
                                // Common modal/overlay classes
                                if (classList.contains('modal') || 
                                    classList.contains('overlay') ||
                                    classList.contains('dialog') ||
                                    classList.contains('popup') ||
                                    classList.contains('open') ||
                                    classList.contains('active') ||
                                    classList.contains('visible')) {
                                    notifyChange();
                                    break;
                                }
                            }
                        }
                    }
                    
                    // Detect form field focus changes
                    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                        const target = mutation.target;
                        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') {
                            if (target.classList.contains('focused') || document.activeElement === target) {
                                notifyChange();
                                break;
                            }
                        }
                    }
                }
            });

            // Observe the entire document
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['class', 'style', 'display', 'visibility', 'opacity'],
                characterData: false
            });

            // Also listen for focus events on form elements
            document.addEventListener('focusin', (e) => {
                if (e.target.tagName === 'INPUT' || 
                    e.target.tagName === 'TEXTAREA' || 
                    e.target.tagName === 'SELECT') {
                    notifyChange();
                }
            }, true);

            // Listen for click events that might open modals
            document.addEventListener('click', (e) => {
                // Small delay to allow modal to appear
                setTimeout(() => notifyChange(), 100);
            }, true);

            window.__uiChangeObserver = observer;
            console.log('[UIChangeDetector] MutationObserver injected and monitoring');
        })();
        """

        try:
            # Wait for browser to be ready
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    # Get CDP session to inject script
                    cdp_session = await self.browser_session.get_or_create_cdp_session()
                    
                    # Check if CDP client is initialized
                    if not cdp_session.cdp_client:
                        raise RuntimeError("CDP client not initialized")
                    
                    # Inject the script using CDP
                    await cdp_session.cdp_client.send.Page.addScriptToEvaluateOnNewDocument(
                        source=observer_script,
                        session_id=cdp_session.session_id
                    )
                    
                    # Also evaluate it immediately for current page
                    await cdp_session.cdp_client.send.Runtime.evaluate(
                        expression=observer_script,
                        session_id=cdp_session.session_id
                    )

                    # Set up listener for the custom event
                    await self._setup_event_listener(cdp_session)

                    self._observer_script_injected = True
                    logger.info("UI change detector started and monitoring for DOM changes")
                    return
                except (RuntimeError, AttributeError) as e:
                    if "not initialized" in str(e).lower() or "Root CDP" in str(e):
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)  # Wait and retry
                            continue
                    raise
        except Exception as e:
            logger.warning(f"Failed to inject UI change detector: {e}")
            # Don't raise - this is non-critical functionality

    async def _setup_event_listener(self, cdp_session: Any):
        """Set up CDP event listener for UI change events."""
        # We'll poll for changes by checking for the event
        # Since CDP doesn't directly support custom DOM events, we'll use a polling approach
        # or inject a script that calls back via CDP
        
        # Alternative: Use a simpler approach - poll the page for changes
        # For now, we'll rely on the callback being triggered by action monitoring
        pass

    async def check_for_changes(self) -> bool:
        """Manually check if UI has changed (for polling-based approach).

        Returns:
            True if changes detected, False otherwise
        """
        try:
            cdp_session = await self.browser_session.get_or_create_cdp_session()
            
            # Get a simple hash of the DOM to detect changes
            dom_hash_script = """
            (function() {
                // Create a simple hash from visible elements
                const visibleElements = document.querySelectorAll('*');
                let hash = '';
                for (let i = 0; i < Math.min(visibleElements.length, 100); i++) {
                    const el = visibleElements[i];
                    const style = window.getComputedStyle(el);
                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                        hash += el.tagName + (el.className || '') + (el.id || '');
                    }
                }
                return hash.length.toString();
            })();
            """
            
            result = await cdp_session.cdp_client.send.Runtime.evaluate(
                expression=dom_hash_script,
                session_id=cdp_session.session_id
            )
            
            current_hash = result.get('result', {}).get('value', '')
            
            if current_hash != self._last_dom_hash:
                self._last_dom_hash = current_hash
                return True
            
            return False
        except Exception as e:
            logger.debug(f"Error checking for UI changes: {e}")
            return False

    async def trigger_capture(self):
        """Manually trigger a screenshot capture (called after actions)."""
        if self.change_callback:
            # Debounce the callback
            if self._debounce_task:
                self._debounce_task.cancel()
            
            async def debounced_callback():
                await asyncio.sleep(self._debounce_delay)
                if self.change_callback:
                    await self.change_callback()
            
            self._debounce_task = asyncio.create_task(debounced_callback())

    async def stop_monitoring(self):
        """Stop monitoring for UI changes."""
        if self._debounce_task:
            self._debounce_task.cancel()
            self._debounce_task = None
        
        self._observer_script_injected = False
        logger.info("UI change detector stopped")

