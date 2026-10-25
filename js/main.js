/*
 * main.js — small homepage behavior.
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
})();
