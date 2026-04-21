/** WhatsApp-style triage chat UI + session limiting + Anthropic-driven conversation flow. */
import { useEffect, useMemo, useRef, useState } from "react";
import styles from "./triageChat.module.css";
import { sendChat, type ChatMessage } from "../../services/chatClient";
import { TypingIndicator } from "./TypingIndicator";

type ChatMsg = {
  id: string;
  role: "user" | "assistant";
  text: string;
  createdAt: number;
};

function nowTs() {
  return Date.now();
}

function formatTime(ts: number) {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function uid() {
  return Math.random().toString(16).slice(2) + "-" + Math.random().toString(16).slice(2);
}

const OPENING =
  "Hi there! 👋 I'm MediBot, your personal health assistant.\n\n" +
  "I'm here to help you understand your symptoms and guide you toward the right care.\n\n" +
  "🩺 Tell me what you're feeling — describe your symptoms, how long you've had them, and anything else that feels relevant.\n\n" +
  "I'll do my best to help you. Let's get started 💙";

export function TriageChat() {
  const [messages, setMessages] = useState<ChatMsg[]>(() => [
    { id: uid(), role: "assistant", text: OPENING, createdAt: nowTs() },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // Smooth scroll to bottom on new message/typing changes
    const el = listRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages.length, isTyping]);

  const apiMessages: ChatMessage[] = useMemo(() => {
    return messages.map((m) => ({ role: m.role, content: m.text }));
  }, [messages]);

  async function onSend() {
    const text = input.trim();
    if (!text || isTyping) return;

    const userMsg: ChatMsg = { id: uid(), role: "user", text, createdAt: nowTs() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    setIsTyping(true);
    try {
      const reply = await sendChat({ messages: [...apiMessages, { role: "user", content: text }] });
      const botMsg: ChatMsg = { id: uid(), role: "assistant", text: reply, createdAt: nowTs() };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          text:
            "Sorry — I ran into an error contacting the triage service. " +
            "Please try again in a moment.\n\nDetails: " +
            msg,
          createdAt: nowTs(),
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void onSend();
    }
  }

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.avatar} aria-hidden />
          <div>
            <div className={styles.title}>MediBot</div>
            <div className={styles.subtitle}>
              <span className={styles.dot} /> Online
            </div>
          </div>
        </div>
        <div className={styles.headerRight}>
        </div>
      </header>

      <main className={styles.messages} ref={listRef}>

        {messages.map((m) => (
          <div
            key={m.id}
            className={`${styles.row} ${m.role === "user" ? styles.rowUser : styles.rowBot}`}
          >
            <div className={`${styles.bubble} ${m.role === "user" ? styles.user : styles.bot}`}>
              <div className={styles.text}>{m.text}</div>
              <div className={styles.time}>{formatTime(m.createdAt)}</div>
            </div>
          </div>
        ))}

        {isTyping ? (
          <div className={`${styles.row} ${styles.rowBot}`}>
            <TypingIndicator />
          </div>
        ) : null}
      </main>

      <footer className={styles.inputBar}>
        <textarea
          className={styles.input}
          placeholder="Type a message"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={isTyping}
          rows={1}
        />
        <button className={styles.send} onClick={() => void onSend()} disabled={isTyping || !input.trim()}>
          Send
        </button>
      </footer>
    </div>
  );
}

