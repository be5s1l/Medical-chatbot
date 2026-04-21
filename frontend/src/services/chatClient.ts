/** Chat transport that can use Anthropic directly (dev) or a backend proxy (recommended). */

import { sendToAnthropic, type AnthropicMessage } from "./anthropic";

export type ChatMessage = AnthropicMessage;

type ProxyResponse =
  | { reply: string }
  | { message: string }
  | { content: string }
  | { text: string }
  | { summary: string; possible_causes: string[]; advice: string; urgency: string };

function mode() {
  return (import.meta.env.VITE_CHAT_MODE as string | undefined) ?? "anthropic";
}

function proxyUrl() {
  return (import.meta.env.VITE_CHAT_PROXY_URL as string | undefined) ?? "";
}

let sessionId = "";

export async function sendChat(params: { messages: ChatMessage[] }): Promise<string> {
  if (!sessionId) {
    sessionId = globalThis.crypto?.randomUUID?.() || Date.now().toString(36);
  }

  if (mode() === "proxy") {
    const url = proxyUrl();
    if (!url) throw new Error("Missing VITE_CHAT_PROXY_URL (proxy mode)");

    // Convert messages array to a single query for the backend
    const userRoleMessages = params.messages.filter((m) => m.role === "user");
    const lastUserMessage = userRoleMessages[userRoleMessages.length - 1];
    const query = lastUserMessage ? lastUserMessage.content : "";

    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, query }),
    });
    if (!res.ok) {
      const t = await res.text().catch(() => "");
      throw new Error(`Proxy error ${res.status}: ${t || res.statusText}`);
    }
    const data = await res.json();

    // Always use the pre-formatted message from the backend.
    // The backend assembles the complete, clean, emoji-structured response.
    const reply =
      typeof data.message === "string" && data.message.trim()
        ? data.message
        : "I'm having trouble processing that right now.";
    return reply.trim();
  }

  return sendToAnthropic({ messages: params.messages });
}

