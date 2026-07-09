(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    bindExampleButton();
    bindPolicyToggles();
    bindCopyButtons();
  });

  // Fills the form with a realistic account example.
  function bindExampleButton() {
    const button = document.querySelector("[data-account-details-example]");

    if (!button) {
      return;
    }

    button.addEventListener("click", function () {
      const accountId = document.getElementById("account_id");

      if (accountId) {
        accountId.value = button.getAttribute("data-account-id") || "";
        accountId.focus();
      }
    });
  }

  // Wires the policy expand and collapse controls.
  function bindPolicyToggles() {
    const cards = Array.from(document.querySelectorAll("[data-policy-card]"));
    const expandButton = document.querySelector("[data-policies-expand]");
    const collapseButton = document.querySelector("[data-policies-collapse]");

    cards.forEach(function (card) {
      const toggle = card.querySelector("[data-policy-toggle]");

      if (!toggle) {
        return;
      }

      toggle.addEventListener("click", function () {
        setPolicyOpen(card, !policyIsOpen(card));
      });
    });

    if (expandButton) {
      expandButton.addEventListener("click", function () {
        setAllPolicies(cards, true);
      });
    }

    if (collapseButton) {
      collapseButton.addEventListener("click", function () {
        setAllPolicies(cards, false);
      });
    }
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

  // Opens or closes one policy card.
  function setPolicyOpen(card, open) {
    const body = card.querySelector("[data-policy-body]");
    const toggle = card.querySelector("[data-policy-toggle]");

    if (body) {
      body.hidden = !open;
    }

    if (toggle) {
      toggle.classList.toggle("open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    }
  }

  // Opens or closes every policy card.
  function setAllPolicies(cards, open) {
    cards.forEach(function (card) {
      setPolicyOpen(card, open);
    });
  }

  // Checks whether one policy card is open.
  function policyIsOpen(card) {
    const body = card.querySelector("[data-policy-body]");

    return Boolean(body && !body.hidden);
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
