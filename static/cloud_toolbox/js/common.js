(function () {
  "use strict";

  const CT = window.CT = window.CT || {};

  CT.renderIcons = renderIcons;
  CT.escapeHtml = escapeHtml;

  document.addEventListener("DOMContentLoaded", function () {
    renderIcons();
    bindAutoResizeTextareas();
    bindExampleButtons();
    bindConfirmForms();
    bindToastLifetime();
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
})();
