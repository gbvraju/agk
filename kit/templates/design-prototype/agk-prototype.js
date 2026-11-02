// agk-prototype 1
// The kit's prototype runtime (SPEC-0037 rule 5), copied unchanged into each version folder and
// loaded by one script element at the end of each page. It reads only the page's own links and the
// data-demo attribute of its demo links; it makes no request, keeps no data and changes none. The
// only thing it carries from page to page is the #demo mark of the address.
// Keys: in the state bar the arrow keys, Home and End move between the states, and anywhere the
// digits 1 to 9 open a state of the bar. d turns the demo mode on or off; in demo mode n or the
// right arrow opens the next step of the flow, p or the left arrow the previous one, and the
// presenter's sentence of the step is shown.
(function () {
  "use strict";
  var doc = document;
  var bar = doc.getElementById("states");
  var demo = doc.querySelector("nav[data-demo]");
  var on = window.location.hash === "#demo";
  var note = null;

  function linksOf(root) {
    return root ? Array.prototype.slice.call(root.querySelectorAll("a[href]")) : [];
  }

  function open(link) {
    if (!link) {
      return;
    }
    var target = link.getAttribute("href").split("#")[0];
    window.location.href = on ? target + "#demo" : target;
  }

  function show() {
    if (!demo) {
      return;
    }
    if (!note) {
      note = doc.createElement("p");
      note.className = "alert alert-info";
      note.setAttribute("role", "status");
      demo.appendChild(note);
    }
    note.textContent = demo.getAttribute("data-demo");
    note.hidden = !on;
  }

  function typing(target) {
    var name = target && target.tagName;
    return (
      name === "INPUT" ||
      name === "TEXTAREA" ||
      name === "SELECT" ||
      Boolean(target && target.isContentEditable)
    );
  }

  function moveInBar(key, states) {
    var at = states.indexOf(doc.activeElement);
    if (at < 0) {
      return false;
    }
    var next = at;
    if (key === "Home") {
      next = 0;
    } else if (key === "End") {
      next = states.length - 1;
    } else if (key === "ArrowRight" || key === "ArrowDown") {
      next = (at + 1) % states.length;
    } else if (key === "ArrowLeft" || key === "ArrowUp") {
      next = (at + states.length - 1) % states.length;
    } else {
      return false;
    }
    states[next].focus();
    return true;
  }

  doc.addEventListener("keydown", function (event) {
    if (event.altKey || event.ctrlKey || event.metaKey || typing(event.target)) {
      return;
    }
    var key = event.key;
    var states = linksOf(bar);
    if (moveInBar(key, states)) {
      event.preventDefault();
      return;
    }
    if (/^[1-9]$/.test(key) && states[Number(key) - 1]) {
      event.preventDefault();
      open(states[Number(key) - 1]);
      return;
    }
    if (key === "d") {
      event.preventDefault();
      on = !on;
      window.location.hash = on ? "demo" : "";
      show();
      return;
    }
    if (on && demo && (key === "n" || key === "ArrowRight")) {
      event.preventDefault();
      open(demo.querySelector('a[rel="next"]'));
      return;
    }
    if (on && demo && (key === "p" || key === "ArrowLeft")) {
      event.preventDefault();
      open(demo.querySelector('a[rel="prev"]'));
    }
  });

  // In demo mode a click on a link of the page keeps the demo mode on the page it opens.
  doc.addEventListener("click", function (event) {
    var link = on && event.target.closest ? event.target.closest("a[href]") : null;
    if (link && link.getAttribute("href").indexOf("#") < 0) {
      event.preventDefault();
      open(link);
    }
  });

  show();
})();
