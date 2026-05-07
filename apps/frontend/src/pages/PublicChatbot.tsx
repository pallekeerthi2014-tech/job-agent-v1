import { useEffect, useRef, useState } from "react";
import { AlertCircle, Bot, Loader2, MessageCircle, Send, User, X } from "lucide-react";

type ChatMessage = {
  id: string;
  text: string;
  sender: "user" | "bot";
  timestamp: Date;
  isError?: boolean;
};

const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY || "";
const GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent";

function formatInline(text: string) {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let currentIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > currentIndex) parts.push(text.slice(currentIndex, match.index));
    const value = match[0];
    if (value.startsWith("**")) {
      parts.push(<strong key={match.index}>{value.slice(2, -2)}</strong>);
    } else {
      parts.push(<code key={match.index}>{value.slice(1, -1)}</code>);
    }
    currentIndex = match.index + value.length;
  }

  if (currentIndex < text.length) parts.push(text.slice(currentIndex));
  return parts.length ? parts : text;
}

function formatMessage(text: string) {
  return text.split("\n").map((line, index) => {
    if (line.startsWith("## ")) {
      return <h4 key={index}>{formatInline(line.replace("## ", ""))}</h4>;
    }
    if (/^[•-]\s/.test(line)) {
      return <p className="public-chat-bullet" key={index}><span>•</span>{formatInline(line.replace(/^[•-]\s/, ""))}</p>;
    }
    if (/^\d+\.\s/.test(line)) {
      return <p className="public-chat-bullet" key={index}><span>{line.match(/^(\d+)\./)?.[1]}.</span>{formatInline(line.replace(/^\d+\.\s/, ""))}</p>;
    }
    if (!line.trim()) return <br key={index} />;
    return <p key={index}>{formatInline(line)}</p>;
  });
}

export function PublicChatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "1",
      text: "Hello! I'm your **AI Career Assistant** specializing in Business and Data Analyst positions. I can help with resumes, LinkedIn, interview prep, career transitions, and job search strategy.",
      sender: "bot",
      timestamp: new Date()
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    if (isOpen) window.setTimeout(() => inputRef.current?.focus(), 100);
  }, [isOpen]);

  async function sendToGemini(userMessage: string) {
    if (!GEMINI_API_KEY) {
      return "I'm sorry, but the AI service isn't configured right now. Please contact our team directly for personalized **Business and Data Analyst** career help.";
    }

    const prompt = `You are an expert career consultant specializing in Business Analyst and Data Analyst career guidance for Think Success Consulting.

Help with resume optimization, LinkedIn profile improvement, interview prep, technical skills, salary negotiation, job search strategy, and career transitions.
Keep responses professional, encouraging, concise, and actionable. Use **bold** text, ## headings, and bullet points where useful.

User question: ${userMessage}`;

    const response = await fetch(`${GEMINI_API_URL}?key=${GEMINI_API_KEY}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.7, topK: 40, topP: 0.95, maxOutputTokens: 1024 }
      })
    });

    if (!response.ok) {
      return "I'm having trouble accessing the AI service right now. Please try again in a moment, or contact our team directly for immediate career assistance.";
    }

    const data = await response.json();
    return data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "I could not generate a response. Please try rephrasing your question.";
  }

  async function handleSendMessage() {
    const trimmed = inputText.trim();
    if (!trimmed || isLoading) return;

    setMessages((current) => [...current, { id: Date.now().toString(), text: trimmed, sender: "user", timestamp: new Date() }]);
    setInputText("");
    setIsLoading(true);

    try {
      const response = await sendToGemini(trimmed);
      window.setTimeout(() => {
        setMessages((current) => [...current, { id: `${Date.now()}-bot`, text: response, sender: "bot", timestamp: new Date() }]);
        setIsLoading(false);
      }, Math.min(response.length * 14, 1500));
    } catch {
      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-error`,
          text: "I'm experiencing a temporary connection issue. Please try again in a moment.",
          sender: "bot",
          timestamp: new Date(),
          isError: true
        }
      ]);
      setIsLoading(false);
    }
  }

  function clearChat() {
    setMessages([
      {
        id: "1",
        text: "Chat cleared. I'm still here to help with your **Business and Data Analyst** career questions.",
        sender: "bot",
        timestamp: new Date()
      }
    ]);
  }

  return (
    <div className="public-chatbot">
      {!isOpen ? (
        <button className="public-chat-toggle" onClick={() => setIsOpen(true)} type="button" aria-label="Open career chat assistant">
          <MessageCircle size={24} />
          <span />
        </button>
      ) : (
        <section className="public-chat-window" aria-label="AI Career Assistant">
          <header>
            <div>
              <Bot size={24} />
              <span>
                <strong>AI Career Assistant</strong>
                <small>{isLoading ? "Typing..." : "Online - Business & Data Analyst Expert"}</small>
              </span>
            </div>
            <div>
              <button onClick={clearChat} type="button">Clear</button>
              <button onClick={() => setIsOpen(false)} type="button" aria-label="Close chat"><X size={18} /></button>
            </div>
          </header>

          <div className="public-chat-messages">
            {messages.map((message) => (
              <article className={`public-chat-message public-chat-${message.sender}`} key={message.id}>
                <div className={message.isError ? "public-chat-avatar public-chat-error-avatar" : "public-chat-avatar"}>
                  {message.sender === "user" ? <User size={15} /> : message.isError ? <AlertCircle size={15} /> : <Bot size={15} />}
                </div>
                <div>
                  <div className={message.isError ? "public-chat-bubble public-chat-error" : "public-chat-bubble"}>
                    {message.sender === "user" ? message.text : formatMessage(message.text)}
                  </div>
                  <small>{message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small>
                </div>
              </article>
            ))}

            {isLoading ? (
              <article className="public-chat-message public-chat-bot">
                <div className="public-chat-avatar"><Bot size={15} /></div>
                <div className="public-chat-bubble public-chat-loading">
                  <Loader2 size={16} />
                  <span>Thinking</span>
                </div>
              </article>
            ) : null}
            <div ref={messagesEndRef} />
          </div>

          <footer>
            <input
              ref={inputRef}
              value={inputText}
              onChange={(event) => setInputText(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void handleSendMessage();
                }
              }}
              maxLength={500}
              disabled={isLoading}
              placeholder="Ask about your career..."
            />
            <button onClick={handleSendMessage} disabled={!inputText.trim() || isLoading} type="button" aria-label="Send message">
              <Send size={17} />
            </button>
          </footer>
          <div className="public-chat-count">{inputText.length}/500</div>
        </section>
      )}
    </div>
  );
}
