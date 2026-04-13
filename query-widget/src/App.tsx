import { useState, useRef, useEffect, FormEvent } from "react";
import "./styles.css";

interface Message {
  role: "user" | "assistant";
  text: string;
}

const API_BASE = window.location.origin;

export function App() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setLoading(true);

    try {
      let res: Response;
      try {
        res = await fetch(`${API_BASE}/ask`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question }),
        });
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: "К сожалению, консультант сейчас недоступен. Пожалуйста, попробуйте позже или обратитесь к администратору." },
        ]);
        return;
      }

      if (!res.ok) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: "Не удалось получить ответ. Пожалуйста, попробуйте позже или обратитесь к администратору." },
        ]);
        return;
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: data.answer ?? "Нет ответа" },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже или обратитесь к администратору." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button className="widget-fab" onClick={() => setOpen(true)} aria-label="Открыть чат">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </button>
    );
  }

  return (
    <div className="widget-container">
      <div className="widget-header">
        <span className="widget-title">Консультант</span>
        <button className="widget-close" onClick={() => setOpen(false)} aria-label="Свернуть чат">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div className="widget-messages">
        {messages.length === 0 && (
          <div className="widget-empty">Задайте вопрос, и я постараюсь помочь.</div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`widget-msg widget-msg--${msg.role}`}>
            <div className="widget-msg-bubble">{msg.text}</div>
          </div>
        ))}
        {loading && (
          <div className="widget-msg widget-msg--assistant">
            <div className="widget-msg-bubble widget-typing">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="widget-input-area" onSubmit={handleSubmit}>
        <input
          className="widget-input"
          type="text"
          placeholder="Задайте вопрос..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          autoFocus
        />
        <button className="widget-send" type="submit" disabled={loading || !input.trim()} aria-label="Отправить">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>
    </div>
  );
}
