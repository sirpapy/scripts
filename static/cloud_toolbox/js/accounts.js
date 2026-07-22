(function () {
  "use strict";

  const CT = window.CT = window.CT || {};

  CT.openAccount = openAccount;

  document.addEventListener("DOMContentLoaded", function () {
    bindAccountButtons();
    bindAccountExampleButton();
  });

  // Opens the account modal from account ID buttons.
  function bindAccountButtons() {
    document.addEventListener("click", function (event) {
      const button = event.target.closest("[data-account-id]");

      if (button && !button.hasAttribute("onclick")) {
        openAccount(button.getAttribute("data-account-id"));
      }
    });
  }

  // Fills the account form with the example project ID.
  function bindAccountExampleButton() {
    document.querySelectorAll("[data-account-example]").forEach(function (button) {
      button.addEventListener("click", function () {
        const projectIdField = document.getElementById("project_id");

        if (projectIdField) {
          projectIdField.value = button.getAttribute("data-project-id") || "";
        }
      });
    });
  }

  // Fetches and displays account details.
  function openAccount(projectId) {
    const modalBody = document.querySelector("[data-account-modal-body]");

    if (!projectId || !modalBody) {
      return;
    }

    CT.openModal("account-modal");
    modalBody.innerHTML = CT.loadingHtml("Chargement du compte...");

    fetch("/api/accounts/" + encodeURIComponent(projectId) + "/")
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Account API error");
        }

        return response.json();
      })
      .then(function (account) {
        modalBody.innerHTML = accountDetailsHtml(account);
      })
      .catch(function () {
        modalBody.innerHTML = (
          '<div class="alert alert-amber">' +
          '<span class="alert-icon"><span data-icon="AlertTriangle" data-icon-size="18"></span></span>' +
          '<div class="alert-body"><strong>Impossible de charger le compte.</strong> Reessayez plus tard.</div>' +
          '</div>'
        );
        CT.renderIcons();
      });
  }

  // Builds the account details markup.
  function accountDetailsHtml(account) {
    return (
      "<h4>Account details</h4>" +
      '<div class="account-grid">' +
      accountItemHtml("Project name", account.project_name) +
      accountItemHtml("Domain", account.domain) +
      accountItemHtml("Project ID", account.project_id, true) +
      "</div>"
    );
  }

  // Builds one account field row.
  function accountItemHtml(label, value, mono) {
    const valueClass = mono ? "v mono" : "v";

    return (
      '<div class="account-item">' +
      '<div class="k">' + CT.escapeHtml(label) + "</div>" +
      '<div class="' + valueClass + '">' + CT.escapeHtml(value) + "</div>" +
      "</div>"
    );
  }
})();
