window.ChatUI = (() => {
  const messagesEl = document.getElementById("chat-messages");
  const inputEl = document.getElementById("chat-input");
  const sendBtn = document.getElementById("chat-send");

  const CHAT_HISTORY_KEY = "chat_history_v1";
  const CHAT_RESTORE_ONCE_KEY = "chat_restore_once_v1";
  const CHAT_HISTORY_MAX = 80;
  let typingBubble = null;

  if (!messagesEl || !inputEl || !sendBtn) {
    console.error("[ChatUI] Required DOM elements not found");
    return null;
  }

  inputEl.placeholder = "Type a message...";

  const initialBubble = messagesEl.querySelector("div");
  if (initialBubble) {
    initialBubble.textContent = "Hi! How can I help you today?";
  }

  function loadHistory() {
    try {
      const raw = localStorage.getItem(CHAT_HISTORY_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function saveHistory(history) {
    try {
      const trimmed = history.slice(-CHAT_HISTORY_MAX);
      localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(trimmed));
    } catch {
      // Ignore storage failures.
    }
  }

  function pushHistoryMessage(role, text, preserveLines = false, animateOnRestore = false) {
    const history = loadHistory();
    history.push({
      type: "message",
      role,
      text: String(text ?? ""),
      preserveLines: Boolean(preserveLines),
      animateOnRestore: Boolean(animateOnRestore),
    });
    saveHistory(history);
  }

  function createMessageBubble(role, text, opts = {}) {
    const bubble = document.createElement("div");
    bubble.className =
      role === "user"
        ? "ml-auto max-w-[85%] rounded-xl bg-[#6C5CE7] text-white px-3 py-2"
        : "max-w-[85%] rounded-xl bg-white/70 px-3 py-2";

    const safeText = String(text ?? "");
    if (opts.preserveLines) {
      bubble.textContent = safeText;
      bubble.style.whiteSpace = "pre-line";
    } else {
      bubble.textContent = safeText;
    }
    messagesEl.appendChild(bubble);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return bubble;
  }

  function hydrateFromHistory() {
    const shouldRestore = localStorage.getItem(CHAT_RESTORE_ONCE_KEY) === "1";
    if (!shouldRestore) {
      saveHistory([]);
      return;
    }

    const history = loadHistory();
    if (history.length === 0) {
      const firstBubble = messagesEl.querySelector("div");
      if (firstBubble) {
        pushHistoryMessage("assistant", firstBubble.textContent || "", false);
      }
      return;
    }

    messagesEl.innerHTML = "";
    history.forEach((item) => {
      if (item && item.type === "message") {
        if (item.animateOnRestore) {
          typeMessage(item.text || "", {
            role: item.role || "assistant",
            preserveLines: Boolean(item.preserveLines),
            persist: false,
          });
          item.animateOnRestore = false;
          return;
        }

        createMessageBubble(item.role || "assistant", item.text || "", {
          preserveLines: Boolean(item.preserveLines),
        });
      }
    });
    saveHistory(history);
  }

  function addMessage(role, text, opts = {}) {
    const bubble = createMessageBubble(role, text, opts);
    if (opts.persist !== false) {
      pushHistoryMessage(
        role,
        text,
        Boolean(opts.preserveLines),
        Boolean(opts.animateOnRestore)
      );
    }
    return bubble;
  }

  function showTyping() {
    hideTyping();
    typingBubble = document.createElement("div");
    typingBubble.className = "chat-typing";
    typingBubble.setAttribute("aria-label", "Assistant is thinking");
    typingBubble.innerHTML = [
      '<span class="chat-typing__dot"></span>',
      '<span class="chat-typing__dot"></span>',
      '<span class="chat-typing__dot"></span>',
    ].join("");
    messagesEl.appendChild(typingBubble);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function hideTyping() {
    if (!typingBubble) return;
    typingBubble.remove();
    typingBubble = null;
  }

  function disableInput(state) {
    sendBtn.disabled = state;
    inputEl.disabled = state;
    inputEl.placeholder = state ? "Assistant is responding..." : "Type a message...";
  }

  function addSuggestion(label, page) {
    const btn = document.createElement("button");
    btn.className =
      "mt-2 inline-block rounded-xl bg-[#6C5CE7] text-white px-4 py-2 text-sm";
    btn.textContent = label;
    btn.onclick = () => {
      window.ChatCommands.execute({ type: "navigate", page });
    };
    messagesEl.appendChild(btn);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addQuickReplies(items = []) {
    if (!Array.isArray(items) || items.length === 0) return;
    const wrap = document.createElement("div");
    wrap.className = "mt-2 flex flex-wrap gap-2";

    items.forEach((item) => {
      const label = item && item.label ? item.label : "";
      if (!label) return;

      const btn = document.createElement("button");
      btn.className =
        "rounded-full border border-[#6C5CE7] text-[#6C5CE7] px-3 py-1.5 text-xs hover:bg-[#6C5CE7] hover:text-white transition";
      btn.textContent = label;
      btn.onclick = () => {
        if (item.action && window.ChatCommands) {
          window.ChatCommands.execute(item.action);
          return;
        }
        if (item.page && window.ChatCommands) {
          window.ChatCommands.execute({ type: "navigate", page: item.page });
          return;
        }
        if (item.message && window.ChatSend) {
          window.ChatSend(item.message);
        }
      };
      wrap.appendChild(btn);
    });

    if (wrap.children.length === 0) return;
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function clearMessages() {
    messagesEl.innerHTML = "";
    saveHistory([]);
  }

  function typeMessage(text, opts = {}) {
    const safeText = String(text ?? "");
    const role = opts.role || "assistant";
    const shouldPersist = opts.persist !== false;
    if (shouldPersist) {
      pushHistoryMessage(
        role,
        safeText,
        Boolean(opts.preserveLines),
        Boolean(opts.animateOnRestore)
      );
    }
    const bubble = createMessageBubble(role, "", {
      preserveLines: Boolean(opts.preserveLines),
    });

    let i = 0;
    const speed = Number.isFinite(opts.speed) ? opts.speed : 35;

    function tick() {
      if (!bubble) return;
      if (i >= safeText.length) {
        return;
      }
      bubble.textContent += safeText[i];
      i += 1;
      messagesEl.scrollTop = messagesEl.scrollHeight;
      setTimeout(tick, speed);
    }

    tick();
  }

  hydrateFromHistory();

  return {
    addMessage,
    typeMessage,
    pushHistoryMessage,
    addSuggestion,
    addQuickReplies,
    showTyping,
    hideTyping,
    disableInput,
    clearMessages,
    inputEl,
    sendBtn,
  };
})();
