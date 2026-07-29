const STATUS_LABELS = {
  idle: "BEREIT",
  listening: "HÖRT ZU",
  thinking: "DENKT NACH",
  speaking: "SPRICHT",
};

const body = document.body;
const statusEl = document.getElementById("status");
const connEl = document.getElementById("conn");
const logEl = document.getElementById("log");
const toolcallEl = document.getElementById("toolcall");

let toolcallTimer = null;

function setStatus(state) {
  body.dataset.state = state;
  statusEl.textContent = STATUS_LABELS[state] || state.toUpperCase();
}

function addLogEntry(who, text) {
  const entry = document.createElement("div");
  entry.className = `log-entry ${who}`;

  const whoEl = document.createElement("span");
  whoEl.className = "who";
  whoEl.textContent = who === "assistant" ? "jarvis" : who;

  const textEl = document.createElement("span");
  textEl.className = "text";
  textEl.textContent = text;

  entry.append(whoEl, textEl);
  logEl.appendChild(entry);
  logEl.scrollTop = logEl.scrollHeight;
}

function showToolCall(name) {
  toolcallEl.textContent = `⚙ ${name}`;
  toolcallEl.classList.add("show");
  clearTimeout(toolcallTimer);
  toolcallTimer = setTimeout(() => toolcallEl.classList.remove("show"), 2500);
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
    default:
      console.warn("Unbekanntes Event:", type);
  }
}

function connect() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${window.location.host}/ws`);

  ws.addEventListener("open", () => {
    connEl.textContent = "verbunden";
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
    connEl.textContent = "getrennt - erneuter Versuch…";
    connEl.className = "conn offline";
    setTimeout(connect, 2000);
  });

  ws.addEventListener("error", () => ws.close());
}

connect();
