(() => {
  const CHAT_OPEN_KEY = "chat_open_v1";
  const CHAT_RESTORE_ONCE_KEY = "chat_restore_once_v1";
  const notch = document.getElementById("chat-notch");
  const panel = document.getElementById("chat-panel");
  const backdrop = document.getElementById("chat-backdrop");
  const closeBtn = document.getElementById("chat-close");
  const root = document.getElementById("chat-root");

  if (!notch || !panel || !backdrop || !closeBtn || !root) {
    console.error("[ChatToggle] Missing DOM elements");
    return;
  }

  function openChat() {
    root.classList.add("open");
    notch.setAttribute("aria-expanded", "true");
    localStorage.setItem(CHAT_OPEN_KEY, "1");
    panel.classList.remove(
      "opacity-0",
      "scale-75",
      "translate-y-6",
      "pointer-events-none"
    );
    backdrop.classList.remove("opacity-0", "pointer-events-none");
    backdrop.classList.add("pointer-events-auto");
  }

  function restoreChatInstantly() {
    root.classList.add("open");
    notch.setAttribute("aria-expanded", "true");
    localStorage.setItem(CHAT_OPEN_KEY, "1");

    // Suppress the usual open animation during redirect restore so
    // the panel feels continuous across pages instead of popping in.
    panel.style.transition = "none";
    backdrop.style.transition = "none";

    panel.classList.remove(
      "opacity-0",
      "scale-75",
      "translate-y-6",
      "pointer-events-none"
    );
    backdrop.classList.remove("opacity-0", "pointer-events-none");
    backdrop.classList.add("pointer-events-auto");

    requestAnimationFrame(() => {
      panel.style.transition = "";
      backdrop.style.transition = "";
    });
  }

  function closeChat() {
    root.classList.remove("open");
    notch.setAttribute("aria-expanded", "false");
    localStorage.setItem(CHAT_OPEN_KEY, "0");
    panel.classList.add(
      "opacity-0",
      "scale-75",
      "translate-y-6",
      "pointer-events-none"
    );
    backdrop.classList.add("opacity-0", "pointer-events-none");
    backdrop.classList.remove("pointer-events-auto");
  }

  notch.addEventListener("click", openChat);
  closeBtn.addEventListener("click", closeChat);
  backdrop.addEventListener("click", closeChat);

  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeChat();
  });

  if (
    localStorage.getItem(CHAT_RESTORE_ONCE_KEY) === "1" &&
    localStorage.getItem(CHAT_OPEN_KEY) === "1"
  ) {
    restoreChatInstantly();
    localStorage.setItem(CHAT_RESTORE_ONCE_KEY, "0");
  } else {
    closeChat();
  }
})();
