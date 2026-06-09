"use client";

import { createContext, useContext, useState } from "react";
import type { AskResponse, Paper } from "./types";

export type Message = {
  id: number;
  question: string;
  pinnedPapers: Paper[];
  response: AskResponse;
};

type ChatContextValue = {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
};

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([]);
  return (
    <ChatContext.Provider value={{ messages, setMessages }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChatHistory() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatHistory must be used inside ChatProvider");
  return ctx;
}
