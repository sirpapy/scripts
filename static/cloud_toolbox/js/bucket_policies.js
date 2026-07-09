(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    bindExampleButton();
    bindPolicyModal();
    bindPolicyToggles();
    bindCopyButtons();
  });

  // Fills the form with a realistic bucket example.
  function bindExampleButton() {
    const button = document.querySelector("[data-bucket-policy-example]");

    if (!button) {
      return;
    }

    button.addEventListener("click", function () {
      const ring = document.getElementById("ring");
      const bucketName = document.getElementById("bucket_name");

      if (ring) {
        ring.value = button.getAttribute("data-ring") || ring.value;
      }

      if (bucketName) {
        bucketName.value = button.getAttribute("data-bucket-name") || "";
        bucketName.focus();
      }
    });
  }

  // Opens the account IAM policy modal from owner controls.
  function bindPolicyModal() {
    const modal = document.querySelector("[data-policy-modal]");

    if (!modal) {
      return;
    }

    document.querySelectorAll("[data-policy-modal-open]").forEach(function (button) {
      button.addEventListener("click", function () {
        openPolicyModal(modal);
      });
    });

    modal.querySelectorAll("[data-policy-modal-close]").forEach(function (button) {
      button.addEventListener("click", function () {
        closePolicyModal(modal);
      });
    });

    modal.addEventListener("click", function (event) {
      if (event.target === modal) {
        closePolicyModal(modal);
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !modal.hidden) {
        closePolicyModal(modal);
      }
    });
  }

  // Shows the account IAM policy modal.
  function openPolicyModal(modal) {
    modal.hidden = false;
    document.body.classList.add("modal-open");

    const closeButton = modal.querySelector("[data-policy-modal-close]");

    if (closeButton) {
      closeButton.focus();
    }
  }

  // Hides the account IAM policy modal.
  function closePolicyModal(modal) {
    modal.hidden = true;
    document.body.classList.remove("modal-open");
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
