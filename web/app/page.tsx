"use client";

import { useEffect, useRef, useState } from "react";

type Role = "user" | "assistant";
type Message = { role: Role; content: string };
type Status = "idle" | "listening" | "thinking" | "speaking";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [voiceOn, setVoiceOn] = useState(true);
  const [listening, setListening] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    const recognition = new SpeechRecognition();
    recognition.lang = "de-DE";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
  }, []);

  function toggleMic() {
    if (!recognitionRef.current) return;
    if (listening) {
      recognitionRef.current.stop();
      setListening(false);
    } else {
      recognitionRef.current.start();
      setListening(true);
      setStatus("listening");
    }
  }

  function speak(text: string) {
    if (!voiceOn || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "de-DE";
    utterance.onstart = () => setStatus("speaking");
    utterance.onend = () => setStatus("idle");
    window.speechSynthesis.speak(utterance);
  }

  async function sendMessage() {
    const text = input.trim();
    if (!text || status === "thinking") return;

    const nextMessages: Message[] = [...messages, { role: "user", content: text }];
    setMessages(nextMessages);
    setInput("");
    setStatus("thinking");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: nextMessages }),
      });
      if (!res.body) throw new Error("Kein Antwort-Stream");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let full = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        full += decoder.decode(value, { stream: true });
        setMessages((prev) => {
          const copy = [...prev];
          copy[copy.length - 1] = { role: "assistant", content: full };
          return copy;
        });
      }

      setStatus("idle");
      speak(full);
    } catch (err) {
      setMessages((prev) => {
        const copy = [...prev];
        copy[copy.length - 1] = {
          role: "assistant",
          content: "Entschuldigung, da ist etwas schiefgelaufen.",
        };
        return copy;
      });
      setStatus("idle");
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function autoGrow(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  }

  const statusLabel: Record<Status, string> = {
    idle: "bereit",
    listening: "hört zu",
    thinking: "denkt nach",
    speaking: "spricht",
  };

  return (
    <div className="app-shell">
      <div className="aura" />

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" />
          <div>
            <div className="brand-name">Jarvis</div>
            <div className="brand-sub">Persönlicher Assistent</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            className={`icon-btn mute ${voiceOn ? "on" : ""}`}
            onClick={() => setVoiceOn((v) => !v)}
            title={voiceOn ? "Sprachausgabe an" : "Sprachausgabe aus"}
          >
            {voiceOn ? "🔊" : "🔇"}
          </button>
          <div className="status-pill">
            <span className={`status-dot ${status !== "idle" ? status : ""}`} />
            {statusLabel[status]}
          </div>
        </div>
      </header>

      <main className="chat-area">
        <div className="chat-inner">
          {messages.length === 0 && (
            <div className="empty-state">
              <h1>Wie kann ich helfen?</h1>
              <p>Frag mich etwas oder tippe auf das Mikrofon.</p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`msg-row ${m.role}`}>
              <div className={`avatar ${m.role}`}>{m.role === "user" ? "Du" : "J"}</div>
              <div className="bubble">
                {m.content ? (
                  m.content
                ) : (
                  <span className="typing">
                    <span />
                    <span />
                    <span />
                  </span>
                )}
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>
      </main>

      <div className="composer-wrap">
        <div className="composer">
          <textarea
            ref={textareaRef}
            rows={1}
            placeholder="Nachricht an Jarvis…"
            value={input}
            onChange={autoGrow}
            onKeyDown={handleKeyDown}
          />
          <button
            className={`icon-btn mic ${listening ? "active" : ""}`}
            onClick={toggleMic}
            title="Spracheingabe"
          >
            🎙️
          </button>
          <button
            className="icon-btn send"
            onClick={sendMessage}
            disabled={!input.trim() || status === "thinking"}
            title="Senden"
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}
