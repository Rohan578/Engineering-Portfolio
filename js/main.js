/*
 * main.js — small homepage behavior: equal-height Quest Log cards and the
 * copy-email button.
 *
 * Equal-height Quest Log cards:
 * The three cards should line up at the same height. The RU HART card has a
 * "View the Motor Driver" extension that expands, and only that card should
 * grow when it does.
 * So we measure the cards with every expander closed, set that height as each
 * card's minimum, then restore any expanders the visitor had open.
 */
(function () {
  "use strict";

  var SINGLE_COLUMN = window.matchMedia("(max-width: 900px)");

  function equalizeQuestCards() {
    var cards = document.querySelectorAll(".quest-card");
    if (!cards.length) return;

    // reset, then stop here on phones where cards stack in one column
    cards.forEach(function (card) { card.style.minHeight = ""; });
    if (SINGLE_COLUMN.matches) return;

    // measure with expanders closed
    var openExpanders = document.querySelectorAll(".quest-card__more[open]");
    openExpanders.forEach(function (d) { d.open = false; });

    var tallest = 0;
    cards.forEach(function (card) { tallest = Math.max(tallest, card.offsetHeight); });
    cards.forEach(function (card) { card.style.minHeight = tallest + "px"; });

    openExpanders.forEach(function (d) { d.open = true; });
  }

  // run after images and fonts load (they change card heights), and on resize
  window.addEventListener("load", function () { requestAnimationFrame(equalizeQuestCards); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(equalizeQuestCards);
  window.addEventListener("resize", equalizeQuestCards);

  /*
   * Copy-to-clipboard buttons (the "Copy" button next to my email).
   * Any <button data-copy="text"> copies its text and briefly says "Copied!".
   */
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
