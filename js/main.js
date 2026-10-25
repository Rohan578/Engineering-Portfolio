/*
 * main.js — the "Copy" button next to my email in the contact section.
 * Any <button data-copy="text"> copies its text and briefly says "Copied!".
 */
(function () {
  "use strict";

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    // fallback for older browsers / non-https previews
    return new Promise(function (resolve, reject) {
      var field = document.createElement("textarea");
      field.value = text;
      field.setAttribute("readonly", "");
      field.style.position = "fixed";
      field.style.opacity = "0";
      document.body.appendChild(field);
      field.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      document.body.removeChild(field);
      ok ? resolve() : reject();
    });
  }

  document.querySelectorAll("[data-copy]").forEach(function (button) {
    var label = button.textContent;
    var status = document.getElementById("copy-status");

    button.addEventListener("click", function () {
      copyText(button.getAttribute("data-copy")).then(function () {
        button.textContent = "Copied!";
        button.classList.add("is-copied");
        if (status) status.textContent = "Email address copied to clipboard";
      }, function () {
        button.textContent = "Press Ctrl+C";
      });
      setTimeout(function () {
        button.textContent = label;
        button.classList.remove("is-copied");
        if (status) status.textContent = "";
      }, 1800);
    });
  });
})();
