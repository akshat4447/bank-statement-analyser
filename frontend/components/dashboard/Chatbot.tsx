"use client";
import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2 } from "lucide-react";
import { sendChatMessage } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const DEFAULT_CHIPS = [
  "Am I eligible for a home loan?",
  "Where am I spending the most?",
  "What is my FOIR and is it healthy?",
  "What are my biggest financial risks?",
  "How much can I save each month?",
];

interface Props { analysisId: string }

export default function Chatbot({ analysisId }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hi! I've analysed your bank statement. Ask me anything about your finances — income, expenses, loan eligibility, risk factors, or saving potential.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await sendChatMessage(analysisId, text, history);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I couldn't process that. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card flex flex-col h-[580px]">
      {/* Header */}
      <div className="flex items-center gap-3 pb-4 border-b border-[#1e2d45]">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: "linear-gradient(135deg, rgba(0,212,170,0.2) 0%, rgba(59,130,246,0.2) 100%)", border: "1px solid rgba(0,212,170,0.3)" }}>
          <Bot className="w-5 h-5 text-[#00d4aa]" />
        </div>
        <div>
          <p className="font-semibold text-slate-200">Financial AI Analyst</p>
          <p className="text-xs text-slate-500">Contextual analysis · Ask anything about this statement</p>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <span className="w-2 h-2 bg-[#00d4aa] rounded-full animate-pulse" />
          <span className="text-xs text-slate-500">Ready</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
            <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
              msg.role === "user" ? "bg-[#1e2d45]" : "bg-[rgba(0,212,170,0.15)]"
            }`}>
              {msg.role === "user"
                ? <User className="w-3.5 h-3.5 text-slate-400" />
                : <Bot className="w-3.5 h-3.5 text-[#00d4aa]" />}
            </div>
            <div className={`max-w-[82%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
              msg.role === "user"
                ? "bg-[#1e2d45] text-slate-200 rounded-tr-sm"
                : "bg-[#111827] text-slate-300 border border-[#1e2d45] rounded-tl-sm"
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-[rgba(0,212,170,0.15)] flex items-center justify-center flex-shrink-0">
              <Bot className="w-3.5 h-3.5 text-[#00d4aa]" />
            </div>
            <div className="bg-[#111827] border border-[#1e2d45] px-4 py-3 rounded-2xl rounded-tl-sm">
              <Loader2 className="w-4 h-4 animate-spin text-[#00d4aa]" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggested chips */}
      {messages.length <= 1 && (
        <div className="pb-3">
          <p className="text-xs text-slate-600 mb-2">Suggested questions:</p>
          <div className="flex flex-wrap gap-2">
            {DEFAULT_CHIPS.map((chip) => (
              <button key={chip} onClick={() => send(chip)} disabled={loading}
                className="text-xs px-3 py-1.5 rounded-full border border-[#1e2d45] text-slate-400 hover:border-[#00d4aa] hover:text-[#00d4aa] transition-all disabled:opacity-50">
                {chip}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="pt-3 border-t border-gray-100">
        <div className="flex gap-2">
          <input type="text" value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send(input)}
            placeholder="Ask about income, risk, eligibility..."
            disabled={loading}
            className="input-dark flex-1" />
          <button onClick={() => send(input)} disabled={!input.trim() || loading}
            className="btn-primary !px-3 !py-2.5 flex items-center justify-center">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
