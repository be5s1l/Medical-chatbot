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
    
    // Check if it's the final structured response
    if (data.is_final && data.summary) {
      let reply = `*${data.empathy || "Thank you for sharing."}*\n\n`;
      reply += `**Summary:** ${data.summary}\n\n`;
      
      if (data.possible_causes && data.possible_causes.length > 0) {
        reply += `**Possible Causes:**\n- ${data.possible_causes.join("\n- ")}\n\n`;
      }
      
      if (data.what_you_can_do) {
        reply += `**What You Can Do:**\n${data.what_you_can_do}\n\n`;
      }
      
      if (data.when_to_be_concerned) {
        reply += `**When To Be Concerned:**\n${data.when_to_be_concerned}\n\n`;
      }
      
      if (data.recommended_specialist) {
        reply += `**Recommended Specialist:** ${data.recommended_specialist}\n\n`;
      }
      
      reply += `---\n_${data.disclaimer || "This is not medical advice. Consult a doctor."}_\n`;
      
      if (data.risk_level) {
        reply += `**Risk Level:** ${data.risk_level.toUpperCase()}`;
      }
      
      return reply.trim();
    }

    // Default or follow-up question
    const reply = data.message || "I'm having trouble processing that right now.";
    return reply.trim();
  }

  return sendToAnthropic({ messages: params.messages });
}

