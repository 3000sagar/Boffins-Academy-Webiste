(() => {
  const ui = window.ChatUI;
  if (!ui) {
    console.error("[ChatAPI] ChatUI not found");
    return;
  }

  let sessionId = localStorage.getItem("chat_session_id");

  async function sendMessage(text) {
    if (!text) return;

    ui.addMessage("user", text);
    ui.inputEl.value = "";
    ui.disableInput(true);
    ui.showTyping();

    // Navigate early based on client-side intent to create "thinking" aura
    try {
      if (window.ChatIntent && typeof window.ChatIntent.detect === "function") {
        const intent = window.ChatIntent.detect(text);
        if (intent && intent.action === "navigate" && intent.path) {
          window.ChatCommands.execute({ type: "navigate", page: intent.path });
        }
      }
    } catch (err) {
      console.warn("[ChatAPI] Pre-nav intent failed:", err);
    }

    try {
      const res = await fetch("/api/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
        }),
      });

      const data = await res.json();

      if (data.session_id) {
        sessionId = data.session_id;
        localStorage.setItem("chat_session_id", sessionId);
      }

      ui.hideTyping();

      // ✅ NEW: action-based response
      if (Array.isArray(data.actions)) {
        for (const action of data.actions) {
          window.ChatCommands.execute(action);
        }
        return;
      }

      // 🔁 Backward compatibility
      if (data.type === "text") {
        ui.typeMessage(data.content, { role: "assistant", preserveLines: true });
        return;
      }

      ui.addMessage("assistant", "I didn’t understand that.");
    } catch (err) {
      console.error("[ChatAPI] Error:", err);
      ui.hideTyping();
      ui.addMessage("assistant", "Something went wrong. Please try again.");
    } finally {
      ui.disableInput(false);
    }
  }

  // expose globally
  window.ChatSend = sendMessage;

  ui.sendBtn.addEventListener("click", () => {
    const text = ui.inputEl.value.trim();
    if (text) sendMessage(text);
  });

  ui.inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const text = ui.inputEl.value.trim();
      if (text) sendMessage(text);
    }
  });
})();
