(function (CT) {
  "use strict";

  const ICONS = {
    AlertTriangle: "alert-triangle",
    ArrowRight: "arrow-right",
    Calendar: "calendar",
    CheckCircle: "check-circle",
    ChevronDown: "chevron-down",
    Cloud: "cloud",
    HardDrive: "hard-drive",
    Home: "home",
    Link: "link",
    Loader: "loader",
    LogIn: "log-in",
    LogOut: "log-out",
    RotateCcw: "rotate-ccw",
    RotateCw: "rotate-cw",
    Search: "search",
    Server: "server",
    Sparkles: "sparkles",
    Trash: "trash",
    Unlink: "unlink",
    Unplug: "unplug",
    X: "x",
  };

  const cache = {};

  CT.iconUrl = function (name) {
    const fileName = ICONS[name];

    if (!fileName) {
      return "";
    }

    return staticUrl() + "cloud_toolbox/icons/" + fileName + ".svg";
  };

  CT.renderIcon = function (target) {
    const name = target.getAttribute("data-icon");
    const url = CT.iconUrl(name);

    if (!url) {
      target.textContent = "";
      return;
    }

    loadIcon(url)
      .then(function (markup) {
        target.innerHTML = markup;
        resizeIcon(target);
      })
      .catch(function () {
        target.textContent = "";
      });
  };

  function loadIcon(url) {
    if (!cache[url]) {
      cache[url] = fetch(url).then(function (response) {
        if (!response.ok) {
          throw new Error("Icon not found");
        }

        return response.text();
      });
    }

    return cache[url];
  }

  function resizeIcon(target) {
    const svg = target.querySelector("svg");

    if (!svg) {
      return;
    }

    const size = target.getAttribute("data-icon-size") || 20;
    const stroke = target.getAttribute("data-icon-stroke") || 2;

    svg.setAttribute("width", size);
    svg.setAttribute("height", size);
    svg.setAttribute("stroke-width", stroke);
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
  }

  function staticUrl() {
    return document.body.getAttribute("data-static-url") || "/static/";
  }
})(window.CT = window.CT || {});
