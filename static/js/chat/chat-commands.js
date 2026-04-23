(() => {
  const ui = window.ChatUI;

  /**
   * navigateTo — replaces the old fragile spaNavigate fetch/DOM-swap.
   *
   * Why the old approach broke CSS:
   *   - fetch() + innerHTML swap re-inserts <link> tags but browsers often
   *     don't re-request them, so page-specific CSS from the new page never loads.
   *   - <script> tags inserted via innerHTML never execute, so page JS breaks too.
   *
   * New approach: window.location.assign() for full page loads every time.
   *   - Every page loads its own CSS/JS correctly, no exceptions.
   *   - Section targeting is preserved via URL hash (#section-id).
   *   - Same-page section scrolling still uses smooth scroll (no reload).
   */
  function navigateTo(url, section) {
    if (!url) return;

    const targetPath = url.endsWith("/") ? url : url + "/";
    const currentPath = window.location.pathname;
    const isSamePage = currentPath === targetPath;

    if (isSamePage) {
      // Already on this page — just scroll to the section if provided
      if (section) {
        scrollToSelector(section);
      }
      return;
    }

    // Different page — full navigation (preserves CSS + JS on every page)
    if (section) {
      // Append hash so browser scrolls to section after page loads
      window.location.assign(targetPath + section);
    } else {
      window.location.assign(targetPath);
    }
  }

  /**
   * scrollToSelector — smooth scroll to a CSS selector on the current page.
   * Briefly highlights the element with a ring so the user knows where they landed.
   */
  function scrollToSelector(selector) {
    const el = document.querySelector(selector);
    if (!el) return;

    el.scrollIntoView({ behavior: "smooth", block: "start" });

    // Subtle highlight ring — uses inline style to avoid Tailwind dependency
    el.style.outline = "2px solid #6C5CE7";
    el.style.outlineOffset = "4px";
    setTimeout(() => {
      el.style.outline = "";
      el.style.outlineOffset = "";
    }, 2000);
  }

  /**
   * On page load, if there's a hash in the URL (e.g. from a chatbot navigate+section),
   * scroll to that element smoothly once the page has fully rendered.
   */
  function handleHashOnLoad() {
    const hash = window.location.hash;
    if (!hash) return;

    // Small delay to let the page finish rendering before scrolling
    setTimeout(() => scrollToSelector(hash), 350);
  }

  // Run hash scroll on every page load
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", handleHashOnLoad);
  } else {
    handleHashOnLoad();
  }

  function showSuggestion(content, button) {
    ui.typeMessage(content, { role: "assistant", preserveLines: true });
    if (button) ui.addSuggestion(button.label, button.page);
  }

  function showQuickReplies(items) {
    ui.addQuickReplies(items);
  }

  window.ChatCommands = {
    execute(action) {
      if (!action || !action.type) return;

      switch (action.type) {
        case "navigate":
          // action.section is optional — passed when bot also wants to scroll
          navigateTo(action.page, action.section || null);
          break;

        case "scroll":
          scrollToSelector(action.selector);
          break;

        case "message":
          ui.typeMessage(action.content, { role: "assistant", preserveLines: true });
          break;

        case "suggest":
          showSuggestion(action.content, action.button);
          break;

        case "quick_replies":
          showQuickReplies(action.items);
          break;

        default:
          console.warn("[ChatCommands] Unknown action type:", action.type);
      }
    },
  };
})();