/* ============================================================
   app.js

   Small browser behaviours for Django-rendered pages:
     - load static SVG icons;
     - keep textareas comfortable while typing;
     - open/close volume detail rows;
     - filter volume rows without reloading;
     - fetch mock account details from the backend;
     - handle row and bulk volume actions.
   ============================================================ */
(function (CT) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    renderIcons();
    bindAutoResizeTextareas();
    bindExampleButtons();
    bindQuotaExampleButtons();
    bindDetailToggles();
    bindVolumeFilters();
    bindAccountLookups();
    bindModalClose();
    bindStandaloneConfirmForms();
    bindBulkForm();
    bindToastLifetime();
  });

  CT.toggleDetail = function (detailId, button) {
    const detailRow = document.getElementById(detailId);

    if (!detailRow) {
      return;
    }

    const isOpen = !detailRow.hidden;
    detailRow.hidden = isOpen;

    if (button) {
      button.classList.toggle("active", !isOpen);
    }
  };

  CT.openAccount = function (projectId) {
    const modalBody = document.querySelector("[data-account-modal-body]");

    if (!projectId || !modalBody) {
      return;
    }

    openAccountModal();
    modalBody.innerHTML = '<div class="loading-inline">Chargement du compte...</div>';

    fetch("/api/accounts/" + encodeURIComponent(projectId) + "/")
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Account API error");
        }

        return response.json();
      })
      .then(function (account) {
        modalBody.innerHTML = renderAccountDetails(account);
      })
      .catch(function () {
        modalBody.innerHTML = (
          '<div class="alert alert-amber">' +
          '<span class="alert-icon"><span data-icon="AlertTriangle" data-icon-size="18"></span></span>' +
          '<div class="alert-body"><strong>Impossible de charger le compte.</strong> Reessayez plus tard.</div>' +
          '</div>'
        );
        renderIcons();
      });
  };


  function renderIcons() {
    document.querySelectorAll("[data-icon]").forEach(function (target) {
      const name = target.getAttribute("data-icon");

      if (name) {
        CT.renderIcon(target);
      }
    });
  }


  function bindAutoResizeTextareas() {
    document.querySelectorAll("textarea[data-autoresize]").forEach(function (textarea) {
      resizeTextarea(textarea);

      textarea.addEventListener("input", function () {
        resizeTextarea(textarea);
      });
    });
  }


  function resizeTextarea(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = textarea.scrollHeight + "px";
  }


  function bindExampleButtons() {
    document.querySelectorAll("[data-example-target]").forEach(function (button) {
      button.addEventListener("click", function () {
        const targetId = button.getAttribute("data-example-target");
        const target = document.getElementById(targetId);

        if (!target) {
          return;
        }

        target.value = button.getAttribute("data-example-value") || "";
        resizeTextarea(target);
        target.focus();
      });
    });
  }


  function bindQuotaExampleButtons() {
    document.querySelectorAll("[data-quota-example]").forEach(function (button) {
      button.addEventListener("click", function () {
        setFieldValue("project_id", button.getAttribute("data-project-id"));
      });
    });
  }


  function setFieldValue(id, value) {
    const field = document.getElementById(id);

    if (field) {
      field.value = value || "";
    }
  }


  function bindDetailToggles() {
    document.addEventListener("click", function (event) {
      const button = event.target.closest("[data-toggle-detail]");

      if (button && !button.hasAttribute("onclick")) {
        const detailId = button.getAttribute("data-toggle-detail");
        CT.toggleDetail(detailId, button);
      }
    });
  }


  function bindVolumeFilters() {
    const buttons = Array.from(document.querySelectorAll("[data-volume-filter]"));
    const rows = Array.from(document.querySelectorAll("[data-volume-row]"));
    const visibleCount = document.querySelector("[data-volume-visible-count]");
    const filterNote = document.querySelector("[data-volume-filter-note]");
    const emptyState = document.querySelector("[data-volume-filter-empty]");
    const results = document.querySelector("[data-volume-results]");

    if (!buttons.length || !rows.length) {
      return;
    }

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        applyVolumeFilter(button.getAttribute("data-volume-filter") || "");
      });
    });

    function applyVolumeFilter(status) {
      let count = 0;

      buttons.forEach(function (button) {
        button.classList.toggle(
          "active",
          (button.getAttribute("data-volume-filter") || "") === status
        );
      });

      rows.forEach(function (row) {
        const visible = !status || row.getAttribute("data-volume-status") === status;
        const detailRow = nextDetailRow(row);

        row.hidden = !visible;

        if (detailRow) {
          detailRow.hidden = true;
        }

        if (!visible) {
          uncheckRow(row);
        } else {
          count += 1;
        }
      });

      if (visibleCount) {
        visibleCount.textContent = String(count);
      }

      if (filterNote) {
        filterNote.hidden = !status;
      }

      if (emptyState) {
        emptyState.hidden = count > 0;
      }

      if (results) {
        results.hidden = count === 0;
      }

      document.dispatchEvent(new CustomEvent("volume-filter-change"));
    }
  }


  function nextDetailRow(row) {
    const nextRow = row.nextElementSibling;

    if (nextRow && nextRow.hasAttribute("data-volume-detail")) {
      return nextRow;
    }

    return null;
  }


  function uncheckRow(row) {
    const checkbox = row.querySelector("[data-row-checkbox]");

    if (checkbox) {
      checkbox.checked = false;
    }
  }


  function bindAccountLookups() {
    document.addEventListener("click", function (event) {
      const button = event.target.closest("[data-account-id]");

      if (button && !button.hasAttribute("onclick")) {
        const projectId = button.getAttribute("data-account-id");
        CT.openAccount(projectId);
      }
    });
  }


  function bindModalClose() {
    const modal = document.querySelector("[data-account-modal]");

    if (!modal) {
      return;
    }

    modal.querySelectorAll("[data-modal-close]").forEach(function (button) {
      button.addEventListener("click", closeAccountModal);
    });

    modal.addEventListener("click", function (event) {
      if (event.target === modal) {
        closeAccountModal();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !modal.hidden) {
        closeAccountModal();
      }
    });
  }


  function openAccountModal() {
    const modal = document.querySelector("[data-account-modal]");

    if (!modal) {
      return;
    }

    modal.hidden = false;
    document.body.classList.add("modal-open");
    renderIcons();
  }


  function closeAccountModal() {
    const modal = document.querySelector("[data-account-modal]");

    if (!modal) {
      return;
    }

    modal.hidden = true;
    document.body.classList.remove("modal-open");
  }


  function renderAccountDetails(account) {
    return (
      "<h4>Account details</h4>" +
      '<div class="account-grid">' +
      accountItem("Project name", account.project_name) +
      accountItem("Domain", account.domain) +
      accountItem("Project ID", account.project_id, true) +
      "</div>"
    );
  }


  function accountItem(label, value, mono) {
    const valueClass = mono ? "v mono" : "v";

    return (
      '<div class="account-item">' +
      '<div class="k">' + escapeHtml(label) + "</div>" +
      '<div class="' + valueClass + '">' + escapeHtml(value) + "</div>" +
      "</div>"
    );
  }


  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }


  function bindStandaloneConfirmForms() {
    document.querySelectorAll("form:not([data-bulk-form])").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        const submitter = event.submitter;

        if (!submitter || !submitter.hasAttribute("data-confirm")) {
          return;
        }

        const confirmed = window.confirm(submitter.getAttribute("data-confirm"));

        if (!confirmed) {
          event.preventDefault();
        }
      });
    });
  }


  function bindBulkForm() {
    const form = document.querySelector("[data-bulk-form]");

    if (!form) {
      return;
    }

    const checkboxes = Array.from(form.querySelectorAll("[data-row-checkbox]"));
    const selectAll = form.querySelector("[data-select-all]");
    const bulkBar = form.querySelector("[data-bulk-bar]");
    const selectedCount = form.querySelector("[data-selected-count]");
    const bulkWarning = form.querySelector("[data-bulk-warning]");
    const bulkAction = form.querySelector("[data-bulk-action]");
    const bulkDeleteButton = form.querySelector('[data-bulk-submit="bulk_delete"]');

    checkboxes.forEach(function (checkbox) {
      checkbox.addEventListener("change", refreshBulkState);
    });

    if (selectAll) {
      selectAll.addEventListener("change", function () {
        checkboxes.forEach(function (checkbox) {
          checkbox.checked = selectAll.checked;
        });

        refreshBulkState();
      });
    }

    form.querySelectorAll("[data-bulk-submit]").forEach(function (button) {
      button.addEventListener("click", function () {
        bulkAction.value = button.getAttribute("data-bulk-submit");
      });
    });

    form.querySelectorAll("[data-single-id]").forEach(function (button) {
      button.addEventListener("click", function () {
        checkboxes.forEach(function (checkbox) {
          checkbox.checked = false;
        });

        removeTemporaryInputs(form);
        addTemporaryInput(form, "selected_ids", button.getAttribute("data-single-id"));
      });
    });

    form.addEventListener("submit", function (event) {
      const submitter = event.submitter;

      if (submitter && submitter.hasAttribute("data-confirm")) {
        const confirmed = window.confirm(submitter.getAttribute("data-confirm"));

        if (!confirmed) {
          event.preventDefault();
        }
      }

      if (submitter && submitter.getAttribute("data-bulk-submit") === "bulk_delete") {
        const count = selectedCheckboxes(checkboxes).length;
        const confirmed = window.confirm("Supprimer définitivement " + count + " volume(s) ?");

        if (!confirmed) {
          event.preventDefault();
        }
      }
    });

    refreshBulkState();
    document.addEventListener("volume-filter-change", refreshBulkState);

    function refreshBulkState() {
      const selected = selectedCheckboxes(checkboxes);
      const blocked = selected.some(function (checkbox) {
        return checkbox.getAttribute("data-deletable") !== "true";
      });

      if (bulkBar) {
        bulkBar.hidden = selected.length === 0;
      }

      if (selectedCount) {
        selectedCount.textContent = String(selected.length);
      }

      if (bulkWarning) {
        bulkWarning.hidden = !blocked;
      }

      if (bulkDeleteButton) {
        bulkDeleteButton.disabled = blocked || selected.length === 0;
      }

      if (selectAll) {
        selectAll.checked = selected.length === checkboxes.length && checkboxes.length > 0;
        selectAll.indeterminate = selected.length > 0 && selected.length < checkboxes.length;
      }
    }
  }


  function selectedCheckboxes(checkboxes) {
    return checkboxes.filter(function (checkbox) {
      return checkbox.checked;
    });
  }


  function addTemporaryInput(form, name, value) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    input.setAttribute("data-temporary-input", "true");
    form.appendChild(input);
  }


  function removeTemporaryInputs(form) {
    form.querySelectorAll("[data-temporary-input]").forEach(function (input) {
      input.remove();
    });
  }


  function bindToastLifetime() {
    window.setTimeout(function () {
      document.querySelectorAll(".toast").forEach(function (toast) {
        toast.remove();
      });
    }, 3500);
  }
})(window.CT = window.CT || {});
