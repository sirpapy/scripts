(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    bindQuotaExampleButton();
  });

  // Fills the quota form with the example project ID.
  function bindQuotaExampleButton() {
    document.querySelectorAll("[data-quota-example]").forEach(function (button) {
      button.addEventListener("click", function () {
        const projectIdField = document.getElementById("project_id");

        if (projectIdField) {
          projectIdField.value = button.getAttribute("data-project-id") || "";
        }
      });
    });
  }
})();
