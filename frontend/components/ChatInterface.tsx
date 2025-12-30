"use client";

import { ChatMessage } from "@/components/ChatMessage";
import { Message, narrateStream } from "@/lib/api";
import { useEffect, useRef, useState } from "react";

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setStreamingMessage("");

    try {
      let fullResponse = "";

      for await (const chunk of narrateStream({ action: userMessage.content })) {
        fullResponse += chunk;
        setStreamingMessage(fullResponse);
      }

      const assistantMessage: Message = {
        role: "assistant",
        content: fullResponse,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setStreamingMessage("");
    } catch (error) {
      console.error("Error getting narration:", error);
      const errorMessage: Message = {
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      setStreamingMessage("");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-gradient-to-b from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-900/50 backdrop-blur-sm">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white">
              Mistral <span className="text-purple-400">Realms</span>
            </h1>
            <span className="rounded-full bg-green-500/20 px-2 py-1 text-xs font-medium text-green-400">
              Online
            </span>
          </div>
          <button
            onClick={() => setMessages([])}
            className="rounded-lg bg-slate-800 px-3 py-1.5 text-sm text-gray-300 transition-colors hover:bg-slate-700"
          >
            New Adventure
          </button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-4xl">
          {messages.length === 0 && !streamingMessage && (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <div className="max-w-md space-y-4">
                <h2 className="text-3xl font-bold text-white">
                  Welcome, Adventurer!
                </h2>
                <p className="text-gray-300">
                  Your AI Dungeon Master awaits. Describe your action to begin
                  your adventure.
                </p>
                <div className="flex flex-wrap justify-center gap-2 pt-4">
                  <button
                    onClick={() =>
                      setInput("I enter the tavern and look around")
                    }
                    className="rounded-lg bg-slate-800 px-4 py-2 text-sm text-gray-300 transition-colors hover:bg-slate-700"
                  >
                    Enter the tavern
                  </button>
                  <button
                    onClick={() =>
                      setInput("I search for clues in the forest")
                    }
                    className="rounded-lg bg-slate-800 px-4 py-2 text-sm text-gray-300 transition-colors hover:bg-slate-700"
                  >
                    Explore the forest
                  </button>
                  <button
                    onClick={() => setInput("I cast a detection spell")}
                    className="rounded-lg bg-slate-800 px-4 py-2 text-sm text-gray-300 transition-colors hover:bg-slate-700"
                  >
                    Cast a spell
                  </button>
                </div>
              </div>
            </div>
          )}

          {messages.map((message, index) => (
            <ChatMessage key={index} message={message} />
          ))}

          {streamingMessage && (
            <ChatMessage
              message={{
                role: "assistant",
                content: streamingMessage,
                timestamp: new Date(),
              }}
              isStreaming
            />
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-slate-700 bg-slate-900/50 backdrop-blur-sm">
        <div className="mx-auto max-w-4xl px-4 py-4">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe your action..."
              disabled={isLoading}
              className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-white placeholder-gray-400 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="rounded-lg bg-purple-600 px-6 py-3 font-medium text-white transition-colors hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "..." : "Send"}
            </button>
          </form>
          <p className="mt-2 text-center text-xs text-gray-500">
            Powered by Mistral AI • Press Enter to send
          </p>
        </div>
      </div>
    </div>
  );
}
