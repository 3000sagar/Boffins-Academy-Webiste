(() => {
  const ui = window.ChatUI;
  let fadeStylesInjected = false;

  function spaNavigate(url) {
    if (!url || window.location.pathname === url) {
      return;
    }

    if (!fadeStylesInjected) {
      const style = document.createElement("style");
      style.textContent = `
        .page-fade-enter { opacity: 0; transform: translateY(10px) scale(0.992); filter: blur(7px); }
        .page-fade-active {
          opacity: 1;
          transform: translateY(0) scale(1);
          filter: blur(0);
          transition:
            opacity 3s cubic-bezier(0.16, 1, 0.3, 1),
            transform 3s cubic-bezier(0.16, 1, 0.3, 1),
            filter 3s cubic-bezier(0.16, 1, 0.3, 1);
        }
      `;
      document.head.appendChild(style);
      fadeStylesInjected = true;
    }

    fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(res => res.text())
      .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");

        const newMain = doc.querySelector("main");
        const currentMain = document.querySelector("main");
        const head = document.head;
        const newPageCss = Array.from(
          doc.querySelectorAll('link[rel="stylesheet"][data-page-css]')
        );
        const currentPageCss = Array.from(
          document.querySelectorAll('link[rel="stylesheet"][data-page-css]')
        );

        if (newMain && currentMain) {
          if (newPageCss.length > 0) {
            currentPageCss.forEach((el) => el.remove());
            newPageCss.forEach((el) => head.appendChild(el));
          }

          currentMain.innerHTML = newMain.innerHTML;
          history.pushState({}, "", url);
          window.scrollTo(0, 0);

          currentMain.classList.add("page-fade-enter");
          requestAnimationFrame(() => {
            currentMain.classList.add("page-fade-active");
            currentMain.classList.remove("page-fade-enter");
            setTimeout(() => currentMain.classList.remove("page-fade-active"), 3200);
          });

          // 🔥 sync navbar state after SPA navigation
          if (window.updateNavbarActive) {
            window.updateNavbarActive(url);
          }

        } else {
          // fallback
          window.location.href = url;
        }
      })
      .catch(() => {
        window.location.href = url;
      });
  }

  function scrollToSelector(selector) {
    const el = document.querySelector(selector);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      el.classList.add("ring-2", "ring-[#6C5CE7]");
      setTimeout(() => el.classList.remove("ring-2", "ring-[#6C5CE7]"), 2000);
    }
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
          spaNavigate(action.page);
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
          console.warn("Unknown action:", action);
      }
    }
  };
})();


// REPLACE the entire spaNavigate function with this:
function navigateTo(url, section) {
    if (section) {
        // Same page — just scroll
        if (window.location.pathname === new URL(url, location.origin).pathname) {
            scrollToSelector(section);
            return;
        }
        // Different page — navigate then scroll via hash
        window.location.assign(url + section);
    } else {
        window.location.assign(url);
    }
}