(function () {
  "use strict";

  const CT = window.CT = window.CT || {};

  CT.renderIcons = renderIcons;
  CT.escapeHtml = escapeHtml;
  CT.openModal = openModal;
  CT.closeModal = closeModal;
  CT.setButtonLoading = setButtonLoading;
  CT.loadingHtml = loadingHtml;

  document.addEventListener("DOMContentLoaded", function () {
    renderIcons();
    bindAutoResizeTextareas();
    bindExampleButtons();
    bindConfirmForms();
    bindToastLifetime();
    bindModals();
  });

  // Renders every icon placeholder on the page.
  function renderIcons() {
    document.querySelectorAll("[data-icon]").forEach(function (target) {
      const name = target.getAttribute("data-icon");

      if (name) {
        CT.renderIcon(target);
      }
    });
  }

  // Keeps textareas sized to their content.
  function bindAutoResizeTextareas() {
    document.querySelectorAll("textarea[data-autoresize]").forEach(function (textarea) {
      resizeTextarea(textarea);

      textarea.addEventListener("input", function () {
        resizeTextarea(textarea);
      });
    });
  }

  // Resizes one textarea to fit its content.
  function resizeTextarea(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = textarea.scrollHeight + "px";
  }

  // Fills example values into their target fields.
  function bindExampleButtons() {
    document.querySelectorAll("[data-example-target]").forEach(function (button) {
      button.addEventListener("click", function () {
        const target = document.getElementById(button.getAttribute("data-example-target"));

        if (!target) {
          return;
        }

        target.value = button.getAttribute("data-example-value") || "";
        resizeTextarea(target);
        target.focus();
      });
    });
  }

  // Shows confirmation prompts before risky form submits.
  function bindConfirmForms() {
    document.querySelectorAll("form:not([data-bulk-form])").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        const submitter = event.submitter;

        if (!submitter || !submitter.hasAttribute("data-confirm")) {
          return;
        }

        if (!window.confirm(submitter.getAttribute("data-confirm"))) {
          event.preventDefault();
        }
      });
    });
  }

  // Removes toast messages after a short delay.
  function bindToastLifetime() {
    window.setTimeout(function () {
      document.querySelectorAll(".toast").forEach(function (toast) {
        toast.remove();
      });
    }, 3500);
  }

  // Escapes text before inserting it as HTML.
  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Wires every modal on the page: [data-modal-open="<id>"] opens the modal
  // with that id, [data-modal-close] / a backdrop click / Escape closes it.
  // Markup contract: <div id="…" class="modal-backdrop" data-modal hidden>.
  function bindModals() {
    document.querySelectorAll("[data-modal-open]").forEach(function (button) {
      button.addEventListener("click", function () {
        openModal(button.getAttribute("data-modal-open"));
      });
    });

    document.querySelectorAll("[data-modal]").forEach(function (modal) {
      // A modal can be declared anywhere in the template, but position:fixed
      // only covers the viewport if no ancestor has a transform/filter/etc
      // (e.g. an animated card). Moving it to <body> sidesteps that entirely.
      document.body.appendChild(modal);

      modal.querySelectorAll("[data-modal-close]").forEach(function (button) {
        button.addEventListener("click", function () {
          closeModal(modal.id);
        });
      });

      modal.addEventListener("click", function (event) {
        if (event.target === modal) {
          closeModal(modal.id);
        }
      });
    });

    document.addEventListener("keydown", function (event) {
      const openedModal = document.querySelector("[data-modal]:not([hidden])");

      if (event.key === "Escape" && openedModal) {
        closeModal(openedModal.id);
      }
    });
  }

  // Shows the modal with the given id and moves focus to its close button.
  function openModal(id) {
    const modal = document.getElementById(id);

    if (!modal) {
      return;
    }

    modal.hidden = false;
    document.body.classList.add("modal-open");

    const closeButton = modal.querySelector("[data-modal-close]");

    if (closeButton) {
      closeButton.focus();
    }
  }

  // Hides the modal with the given id (or the currently open one, if omitted).
  function closeModal(id) {
    const modal = id
      ? document.getElementById(id)
      : document.querySelector("[data-modal]:not([hidden])");

    if (!modal) {
      return;
    }

    modal.hidden = true;
    document.body.classList.remove("modal-open");
  }

  // Toggles a button into/out of a disabled, spinning "loading" state.
  function setButtonLoading(button, isLoading) {
    if (!button) {
      return;
    }

    if (isLoading) {
      if (button.dataset.loadingOriginal === undefined) {
        button.dataset.loadingOriginal = button.innerHTML;
      }

      button.disabled = true;
      button.innerHTML = (
        '<span class="spinner" data-icon="Loader" data-icon-size="16"></span> ' +
        escapeHtml(button.getAttribute("data-loading-label") || "Chargement…")
      );
      renderIcons();
      return;
    }

    button.disabled = false;

    if (button.dataset.loadingOriginal !== undefined) {
      button.innerHTML = button.dataset.loadingOriginal;
      delete button.dataset.loadingOriginal;
    }
  }

  // Markup for an inline "loading" line (spinner + label), e.g. inside a
  // modal body while its content is being fetched.
  function loadingHtml(label) {
    return (
      '<div class="loading-inline">' +
      '<span class="spinner" data-icon="Loader" data-icon-size="14"></span> ' +
      escapeHtml(label || "Chargement…") +
      "</div>"
    );
  }
})();
