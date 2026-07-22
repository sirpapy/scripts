(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    bindExampleButton();
    bindBucketToggles();
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

  // Opens or closes one bucket result panel.
  function bindBucketToggles() {
    const buttons = Array.from(document.querySelectorAll("[data-bucket-toggle]"));
    const expandButton = document.querySelector("[data-buckets-expand]");
    const collapseButton = document.querySelector("[data-buckets-collapse]");

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        const body = document.getElementById(button.getAttribute("aria-controls"));

        if (!body) {
          return;
        }

        setBucketOpen(button, body, body.hidden);
      });
    });

    if (expandButton) {
      expandButton.addEventListener("click", function () {
        setAllBuckets(buttons, true);
      });
    }

    if (collapseButton) {
      collapseButton.addEventListener("click", function () {
        setAllBuckets(buttons, false);
      });
    }
  }

  // Wires the policy expand and collapse controls.
  function bindPolicyToggles() {
    document.querySelectorAll("[data-policy-scope]").forEach(function (scope) {
      const cards = Array.from(scope.querySelectorAll("[data-policy-card]"));
      const expandButton = scope.querySelector("[data-policies-expand]");
      const collapseButton = scope.querySelector("[data-policies-collapse]");

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

  // Applies the visible state for one bucket result panel.
  function setBucketOpen(button, body, open) {
    const openLabel = button.getAttribute("data-open-label") || "Déplier";
    const closeLabel = button.getAttribute("data-close-label") || "Replier";
    const label = open ? closeLabel : openLabel;

    body.hidden = !open;
    button.classList.toggle("open", open);
    button.setAttribute("aria-expanded", open ? "true" : "false");
    button.setAttribute("aria-label", label);
  }

  // Opens or closes every bucket result panel.
  function setAllBuckets(buttons, open) {
    buttons.forEach(function (button) {
      const body = document.getElementById(button.getAttribute("aria-controls"));

      if (body) {
        setBucketOpen(button, body, open);
      }
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
