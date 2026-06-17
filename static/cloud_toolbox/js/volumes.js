(function () {
  "use strict";

  const CT = window.CT = window.CT || {};

  CT.toggleDetail = toggleDetail;

  document.addEventListener("DOMContentLoaded", function () {
    bindDetailButtons();
    bindStatusFilters();
    bindBulkActions();
  });

  // Opens or closes one volume detail row.
  function toggleDetail(detailId, button) {
    const detailRow = document.getElementById(detailId);

    if (!detailRow) {
      return;
    }

    const isOpen = !detailRow.hidden;
    detailRow.hidden = isOpen;

    if (button) {
      button.classList.toggle("active", !isOpen);
    }
  }

  // Wires buttons that show volume details.
  function bindDetailButtons() {
    document.addEventListener("click", function (event) {
      const button = event.target.closest("[data-toggle-detail]");

      if (button && !button.hasAttribute("onclick")) {
        toggleDetail(button.getAttribute("data-toggle-detail"), button);
      }
    });
  }

  // Filters volume rows without calling the backend.
  function bindStatusFilters() {
    const buttons = Array.from(document.querySelectorAll("[data-volume-filter]"));
    const rows = Array.from(document.querySelectorAll("[data-volume-row]"));
    const visibleCount = document.querySelector("[data-volume-visible-count]");
    const filterNote = document.querySelector("[data-volume-filter-note]");
    const emptyState = document.querySelector("[data-volume-filter-empty]");
    const results = document.querySelector("[data-volume-results]");
    const selectedStatuses = new Set();

    if (!buttons.length || !rows.length) {
      return;
    }

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        const status = button.getAttribute("data-volume-filter") || "";
        toggleStatus(status);
        applyStatusFilter();
      });
    });

    // Adds or removes one active status filter.
    function toggleStatus(status) {
      if (!status) {
        selectedStatuses.clear();
      } else if (selectedStatuses.has(status)) {
        selectedStatuses.delete(status);
      } else {
        selectedStatuses.add(status);
      }
    }

    // Applies active status filters to visible rows.
    function applyStatusFilter() {
      let visibleRows = 0;

      buttons.forEach(function (button) {
        const status = button.getAttribute("data-volume-filter") || "";
        const active = status ? selectedStatuses.has(status) : selectedStatuses.size === 0;
        button.classList.toggle("active", active);
      });

      rows.forEach(function (row) {
        const visible = rowMatchesFilter(row, selectedStatuses);

        row.hidden = !visible;
        closeDetailRow(row);

        if (visible) {
          visibleRows += 1;
        } else {
          uncheckVolumeRow(row);
        }
      });

      if (visibleCount) {
        visibleCount.textContent = String(visibleRows);
      }

      if (filterNote) {
        filterNote.hidden = selectedStatuses.size === 0;
      }

      if (emptyState) {
        emptyState.hidden = visibleRows > 0;
      }

      if (results) {
        results.hidden = visibleRows === 0;
      }

      document.dispatchEvent(new CustomEvent("volume-filter-change"));
    }
  }

  // Wires bulk actions for visible volume rows.
  function bindBulkActions() {
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
        setVisibleCheckboxes(checkboxes, selectAll.checked);
        clearHiddenCheckboxes(checkboxes);
        clearBlockedCheckboxes(checkboxes);
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
        clearAllCheckboxes(checkboxes);
        removeTemporaryInputs(form);
        addTemporaryInput(form, "selected_ids", button.getAttribute("data-single-id"));
      });
    });

    form.addEventListener("submit", function (event) {
      const submitter = event.submitter;
      clearHiddenCheckboxes(checkboxes);
      clearBlockedCheckboxes(checkboxes);

      if (submitter && submitter.hasAttribute("data-confirm")) {
        const confirmed = window.confirm(submitter.getAttribute("data-confirm"));

        if (!confirmed) {
          event.preventDefault();
        }
      }

      if (submitter && submitter.getAttribute("data-bulk-submit") === "bulk_delete") {
        const selectedVisible = selectedCheckboxes(visibleCheckboxes(checkboxes));
        const confirmed = window.confirm(
          "Supprimer définitivement " + selectedVisible.length + " volume(s) ?"
        );

        if (!confirmed) {
          event.preventDefault();
        }
      }
    });

    refreshBulkState();
    document.addEventListener("volume-filter-change", refreshBulkState);

    // Refreshes bulk buttons and selection counters.
    function refreshBulkState() {
      clearBlockedCheckboxes(checkboxes);

      const visible = visibleActionableCheckboxes(checkboxes);
      const selected = selectedCheckboxes(visible);
      const hasBlockedVolume = selected.some(function (checkbox) {
        return checkbox.getAttribute("data-deletable") !== "true";
      });

      if (bulkBar) {
        bulkBar.hidden = selected.length === 0;
      }

      if (selectedCount) {
        selectedCount.textContent = String(selected.length);
      }

      if (bulkWarning) {
        bulkWarning.hidden = !hasBlockedVolume;
      }

      if (bulkDeleteButton) {
        bulkDeleteButton.disabled = hasBlockedVolume || selected.length === 0;
      }

      if (selectAll) {
        selectAll.checked = selected.length === visible.length && visible.length > 0;
        selectAll.indeterminate = selected.length > 0 && selected.length < visible.length;
        selectAll.disabled = visible.length === 0;
      }
    }
  }

  // Checks whether a row matches the active filters.
  function rowMatchesFilter(row, selectedStatuses) {
    if (selectedStatuses.size === 0) {
      return true;
    }

    return selectedStatuses.has(row.getAttribute("data-volume-status"));
  }

  // Closes the detail row attached to a volume row.
  function closeDetailRow(row) {
    const nextRow = row.nextElementSibling;

    if (nextRow && nextRow.hasAttribute("data-volume-detail")) {
      nextRow.hidden = true;
    }
  }

  // Clears the checkbox inside one volume row.
  function uncheckVolumeRow(row) {
    const checkbox = row.querySelector("[data-row-checkbox]");

    if (checkbox) {
      checkbox.checked = false;
    }
  }

  // Sets only visible volume checkboxes.
  function setVisibleCheckboxes(checkboxes, checked) {
    visibleActionableCheckboxes(checkboxes).forEach(function (checkbox) {
      checkbox.checked = checked;
    });
  }

  // Clears all volume checkboxes.
  function clearAllCheckboxes(checkboxes) {
    checkboxes.forEach(function (checkbox) {
      checkbox.checked = false;
    });
  }

  // Clears checkboxes hidden by filters.
  function clearHiddenCheckboxes(checkboxes) {
    hiddenCheckboxes(checkboxes).forEach(function (checkbox) {
      checkbox.checked = false;
    });
  }

  // Clears checkboxes that are not allowed in actions.
  function clearBlockedCheckboxes(checkboxes) {
    checkboxes.forEach(function (checkbox) {
      if (!checkboxIsActionable(checkbox)) {
        checkbox.checked = false;
      }
    });
  }

  // Returns checkboxes from visible rows.
  function visibleCheckboxes(checkboxes) {
    return checkboxes.filter(function (checkbox) {
      return checkboxIsVisible(checkbox);
    });
  }

  // Returns visible checkboxes that can be used in actions.
  function visibleActionableCheckboxes(checkboxes) {
    return checkboxes.filter(function (checkbox) {
      return checkboxIsVisible(checkbox) && checkboxIsActionable(checkbox);
    });
  }

  // Returns checkboxes from hidden rows.
  function hiddenCheckboxes(checkboxes) {
    return checkboxes.filter(function (checkbox) {
      return !checkboxIsVisible(checkbox);
    });
  }

  // Checks whether a checkbox belongs to a visible row.
  function checkboxIsVisible(checkbox) {
    const row = checkbox.closest("[data-volume-row]");

    return !row || !row.hidden;
  }

  // Checks whether a checkbox can be sent in an action.
  function checkboxIsActionable(checkbox) {
    return !checkbox.disabled && checkbox.getAttribute("data-actionable") === "true";
  }

  // Returns checked checkboxes.
  function selectedCheckboxes(checkboxes) {
    return checkboxes.filter(function (checkbox) {
      return checkbox.checked;
    });
  }

  // Adds a temporary hidden input to a form.
  function addTemporaryInput(form, name, value) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    input.setAttribute("data-temporary-input", "true");
    form.appendChild(input);
  }

  // Removes temporary hidden inputs from a form.
  function removeTemporaryInputs(form) {
    form.querySelectorAll("[data-temporary-input]").forEach(function (input) {
      input.remove();
    });
  }
})();
