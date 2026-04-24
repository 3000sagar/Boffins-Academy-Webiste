(() => {
  const CHAT_RESTORE_ONCE_KEY = "chat_restore_once_v1";
  const CHAT_OPEN_KEY = "chat_open_v1";
  const ui = window.ChatUI;

  function navigate(url) {
    if (!url) return;
    localStorage.setItem(CHAT_RESTORE_ONCE_KEY, "1");
    localStorage.setItem(CHAT_OPEN_KEY, "1");
    window.location.assign(url);
  }

  function scrollToSelector(selector) {
    if (!selector) return;

    const el = document.querySelector(selector);
    if (!el) return;

    el.scrollIntoView({ behavior: "smooth", block: "start" });
    el.classList.add("ring-2", "ring-[#6C5CE7]");
    setTimeout(() => {
      el.classList.remove("ring-2", "ring-[#6C5CE7]");
    }, 2000);
  }

  function showSuggestion(content, button) {
    ui.typeMessage(content, { role: "assistant", preserveLines: true });
    if (button) {
      ui.addSuggestion(button.label, button.page);
    }
  }

  function showQuickReplies(items) {
    ui.addQuickReplies(items);
  }

  window.ChatCommands = {
    execute(action) {
      if (!action || !action.type) return;

      switch (action.type) {
        case "navigate":
          navigate(action.page);
          break;
        case "scroll":
          scrollToSelector(action.selector);
          break;
        case "message":
          ui.typeMessage(
            (action.content && String(action.content).trim()) ||
              "I am here to help. Please tell me what you want to know.",
            { role: "assistant", preserveLines: true }
          );
          break;
        case "suggest":
          showSuggestion(action.content, action.button);
          break;
        case "quick_replies":
          showQuickReplies(action.items);
          break;
        default:
          console.warn("Unknown action:", action);
      }
    },
  };
})();
