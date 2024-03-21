"use strict";
(async () => {
  const { ipcRenderer } = require("electron");
  ipcRenderer.on("theme:use", (_, theme) => {
    document.body.dataset.icalinguaTheme = theme;
  });

  const style = document.head.appendChild(document.createElement("style"));
  new MutationObserver((muts) => {
    /** @type Set<HTMLElement> */
    const targets = new Set();
    for (const mut of muts) {
      /** @type HTMLElement */
      const elem = mut.target;
      if (!targets.has(elem) && elem.classList.contains("icalingua-theme-holder")) {
        targets.add(elem);
      }
    }
    if (!targets.size) {
      return;
    }
    const theme = targets.values().next().value.style;
    const variables = Array.from(theme).filter((prop) => prop.startsWith("--"));
    if (!variables.length) {
      return; // Variables already removed.
    }
    console.log("Got", variables.length, "CSS variables");
    style.textContent = `:root{${variables.map((prop) => `${prop}:${theme.getPropertyValue(prop)}`).join(";")}}`;
    targets.forEach((holder) => variables.forEach((prop) => holder.style.removeProperty(prop)));
  }).observe(document.documentElement, {
    attributes: true,
    subtree: true,
    attributeFilter: ["style"],
  });

  const page = location.hash.split("/", 2)[1].split("?", 1)[0];
  document.body.dataset.icalinguaPage = page;

  if (page === "main") {
    let origGotOnlineData = ipcRenderer._events.gotOnlineData;
    ipcRenderer._events.gotOnlineData = (event, data) => {
      origGotOnlineData?.(event, data);
      document.querySelector(".vac-col-messages ~ pre").dataset.nickname = data.nick;
    };
    const origOn = ipcRenderer.on.bind(ipcRenderer);
    ipcRenderer.on = (event, func) => {
      if (event === "gotOnlineData") {
        origGotOnlineData = func;
        return;
      }
      return origOn(event, func);
    };
    document.querySelector(".multipane-resizer").addEventListener("dblclick", () => {
      const panel = document.querySelector(".rooms-panel");
      panel.style.width = "300px";
      panel.classList.remove("avatar-only");
      panel.querySelector(".head").style.removeProperty("display");
      ipcRenderer.send("setRoomPanelSetting", false, 300);
    });
  }

  if (page !== "main" && page !== "history") {
    console.log("Manually fetching theme");
    const origSend = ipcRenderer.send;
    ipcRenderer.send = (channel, ...args) => {
      if (page === "login" && channel === "theme:set-complete") {
        return;
      }
      return origSend(channel, ...args);
    };
    const theme = await (async () => {
      if (page === "cardSource") {
        return "dark";
      }
      const settings = await ipcRenderer.invoke("getSettings");
      if (settings.theme === "auto") {
        const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        return prefersDark ? "dark" : "light";
      }
      return settings.theme;
    })();
    ipcRenderer.emit("theme:use", null, theme);
  }
})();
