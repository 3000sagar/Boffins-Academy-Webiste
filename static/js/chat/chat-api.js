(() => {
  const CHAT_RESTORE_ONCE_KEY = "chat_restore_once_v1";
  const CHAT_OPEN_KEY = "chat_open_v1";
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

      if (Array.isArray(data.actions)) {
        const navigateAction = data.actions.find((a) => a && a.type === "navigate");
        const nonNavigateActions = data.actions.filter((a) => {
          if (!a || a.type === "navigate") return false;
          if (navigateAction && a.type === "scroll") return false;
          return true;
        });

        if (navigateAction) {
          for (const action of nonNavigateActions) {
            if (action.type === "message") {
              ui.pushHistoryMessage(
                "assistant",
                (action.content && String(action.content).trim()) ||
                  "I am here to help. Please tell me what you want to know.",
                true,
                true
              );
              continue;
            }
            window.ChatCommands.execute(action);
          }

          localStorage.setItem(CHAT_RESTORE_ONCE_KEY, "1");
          localStorage.setItem(CHAT_OPEN_KEY, "1");
          window.ChatCommands.execute(navigateAction);
        } else {
          for (const action of nonNavigateActions) {
            window.ChatCommands.execute(action);
          }
        }
        return;
      }

      if (data.type === "text") {
        ui.typeMessage(data.content, { role: "assistant", preserveLines: true });
        return;
      }

      ui.addMessage("assistant", "I did not understand that.");
    } catch (err) {
      console.error("[ChatAPI] Error:", err);
      ui.hideTyping();
      ui.addMessage("assistant", "Something went wrong. Please try again.");
    } finally {
      ui.disableInput(false);
    }
  }

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
