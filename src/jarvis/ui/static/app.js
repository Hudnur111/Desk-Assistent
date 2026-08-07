const STATUS_LABELS = {
  idle: "BEREIT",
  listening: "HÖRT ZU",
  thinking: "DENKT NACH",
  speaking: "SPRICHT",
};

const body = document.body;
const statusEl = document.getElementById("status");
const connEl = document.getElementById("conn");
const connTextEl = document.getElementById("conn-text");
const logEl = document.getElementById("log");
const toolcallEl = document.getElementById("toolcall");
const reticleEl = document.getElementById("reticle");
const clockEl = document.getElementById("clock");
const statsEl = document.getElementById("stats");
const bootEl = document.getElementById("boot");

let toolcallTimer = null;
let reticleTimer = null;

function setStatus(state) {
  body.dataset.state = state;
  statusEl.textContent = STATUS_LABELS[state] || state.toUpperCase();
}

function formatTime(date) {
  return date.toLocaleTimeString("de-DE", { hour12: false });
}

function addLogEntry(who, text) {
  const entry = document.createElement("div");
  entry.className = `log-entry ${who}`;

  const timeEl = document.createElement("span");
  timeEl.className = "time";
  timeEl.textContent = formatTime(new Date());

  const whoEl = document.createElement("span");
  whoEl.className = "who";
  whoEl.textContent = who === "assistant" ? "jarvis" : who;

  const textEl = document.createElement("span");
  textEl.className = "text";
  textEl.textContent = text;

  entry.append(timeEl, whoEl, textEl);
  logEl.appendChild(entry);
  logEl.scrollTop = logEl.scrollHeight;
}

function showToolCall(name) {
  toolcallEl.textContent = `⚙ ${name}`;
  toolcallEl.classList.add("show");
  clearTimeout(toolcallTimer);
  toolcallTimer = setTimeout(() => toolcallEl.classList.remove("show"), 2500);

  reticleEl.classList.remove("flash");
  // Reflow erzwingen, damit die Animation bei wiederholtem Trigger neu startet
  void reticleEl.offsetWidth;
  reticleEl.classList.add("flash");
  clearTimeout(reticleTimer);
  reticleTimer = setTimeout(() => reticleEl.classList.remove("flash"), 700);
}

function showResourceStats(payload) {
  if (typeof payload.rss_mb === "number") {
    statsEl.textContent = `RSS ${payload.rss_mb.toFixed(1)} MB`;
  }
}

function handleEvent(event) {
  const { type, payload } = event;
  switch (type) {
    case "status":
      setStatus(payload.state);
      break;
    case "user_message":
      addLogEntry("user", payload.text);
      break;
    case "assistant_message":
      addLogEntry("assistant", payload.text);
      break;
    case "tool_call":
      showToolCall(payload.name);
      addLogEntry("tool", `${payload.name}(${JSON.stringify(payload.input)})`);
      break;
    case "resource":
      showResourceStats(payload);
      break;
    default:
      console.warn("Unbekanntes Event:", type);
  }
}

function connect() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${window.location.host}/ws`);

  ws.addEventListener("open", () => {
    connTextEl.textContent = "verbunden";
    connEl.className = "conn online";
  });

  ws.addEventListener("message", (event) => {
    try {
      handleEvent(JSON.parse(event.data));
    } catch (err) {
      console.error("Ungueltiges Event", err);
    }
  });

  ws.addEventListener("close", () => {
    connTextEl.textContent = "getrennt - erneuter Versuch…";
    connEl.className = "conn offline";
    setTimeout(connect, 2000);
  });

  ws.addEventListener("error", () => ws.close());
}

function tickClock() {
  clockEl.textContent = formatTime(new Date());
}

tickClock();
setInterval(tickClock, 1000);
setTimeout(() => bootEl.remove(), 2200);

connect();
