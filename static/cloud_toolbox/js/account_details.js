(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    bindExampleButton();
    bindDetailToggles();
    bindGroupToggles();
    bindConflictLinks();
    bindCopyButtons();
  });

  // Fills the form with a deterministic example that produces conflicts.
  function bindExampleButton() {
    const button = document.querySelector("[data-iam-debug-example]");

    if (!button) {
      return;
    }

    button.addEventListener("click", function () {
      setFieldValue("igg", button.getAttribute("data-igg"));
      setFieldValue("account_id", button.getAttribute("data-account-id"));
      setFieldValue("access_key", button.getAttribute("data-access-key"));

      const igg = document.getElementById("igg");

      if (igg) {
        igg.focus();
      }
    });
  }

  function setFieldValue(id, value) {
    const field = document.getElementById(id);

    if (field) {
      field.value = value || "";
    }
  }

  // Wires the "Voir les détails" toggles on the check cards.
  function bindDetailToggles() {
    document.querySelectorAll("[data-detail-toggle]").forEach(function (toggle) {
      toggle.addEventListener("click", function () {
        const body = toggle.parentElement.querySelector("[data-detail-body]");
        const open = toggle.getAttribute("aria-expanded") === "true";

        toggle.setAttribute("aria-expanded", open ? "false" : "true");

        if (body) {
          body.hidden = open;
        }
      });
    });
  }

  // Wires the group expand and collapse controls (tree open by default).
  function bindGroupToggles() {
    const cards = Array.from(document.querySelectorAll("[data-group-card]"));
    const expandButton = document.querySelector("[data-groups-expand]");
    const collapseButton = document.querySelector("[data-groups-collapse]");

    cards.forEach(function (card) {
      const toggle = card.querySelector("[data-group-toggle]");

      if (!toggle) {
        return;
      }

      toggle.addEventListener("click", function () {
        setGroupOpen(card, !groupIsOpen(card));
      });
    });

    if (expandButton) {
      expandButton.addEventListener("click", function () {
        cards.forEach(function (card) {
          setGroupOpen(card, true);
        });
      });
    }

    if (collapseButton) {
      collapseButton.addEventListener("click", function () {
        cards.forEach(function (card) {
          setGroupOpen(card, false);
        });
      });
    }
  }

  function setGroupOpen(card, open) {
    const body = card.querySelector("[data-group-body]");
    const toggle = card.querySelector("[data-group-toggle]");

    if (body) {
      body.hidden = !open;
    }

    if (toggle) {
      toggle.classList.toggle("open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    }
  }

  function groupIsOpen(card) {
    const body = card.querySelector("[data-group-body]");

    return Boolean(body && !body.hidden);
  }

  // Anchor links from the conflict alert and "annulé par" chips: make sure the
  // target group is open, then flash the Deny statement.
  function bindConflictLinks() {
    document.querySelectorAll("[data-conflict-link]").forEach(function (link) {
      link.addEventListener("click", function () {
        const targetId = (link.getAttribute("href") || "").slice(1);
        const target = document.getElementById(targetId);

        if (!target) {
          return;
        }

        const card = target.closest("[data-group-card]");

        if (card) {
          setGroupOpen(card, true);
        }

        target.classList.remove("flash");
        window.requestAnimationFrame(function () {
          target.classList.add("flash");
        });
      });
    });
  }

  // Wires every JSON copy button.
  function bindCopyButtons() {
    document.querySelectorAll("[data-copy-from]").forEach(function (button) {
      button.addEventListener("click", function () {
        const source = document.getElementById(button.getAttribute("data-copy-from"));

        if (!source) {
          return;
        }

        copyText(source.textContent || "").then(function () {
          showCopiedState(button);
        });
      });
    });
  }

  // Copies text with a small fallback for older browsers.
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }

    return fallbackCopyText(text);
  }

  // Copies text through a temporary textarea.
  function fallbackCopyText(text) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "readonly");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();

    return Promise.resolve();
  }

  // Shows a short copied label on the clicked button.
  function showCopiedState(button) {
    const originalHtml = button.innerHTML;

    button.textContent = "Copié";

    window.setTimeout(function () {
      button.innerHTML = originalHtml;
    }, 1200);
  }
})();
