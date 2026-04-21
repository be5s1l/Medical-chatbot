/** Minimal Anthropic Messages API client for the triage chatbot. */

export type AnthropicMessage = {
  role: "user" | "assistant";
  content: string;
};

type AnthropicResponse = {
  content: Array<{ type: string; text?: string }>;
};

const API_URL = "https://api.anthropic.com/v1/messages";

const SYSTEM_PROMPT = `You are a medical triage assistant.

Follow this conversation flow strictly:
1) Opening: greet and ask the patient to describe what they're feeling.
2) Symptom collection: ask follow-up questions when the patient's answer is vague. Keep asking until you have enough information to make a confident triage assessment. If unsure, explicitly ask for more details rather than guessing.
3) Triage response: ONLY when enough info is collected, provide a structured triage answer with three parts:
   - What you might have (non-diagnostic, plain-language, use may/could/possible)
   - Next steps (what to do now)
   - If symptoms worsen (clear escalation instructions)

Safety rules:
- DO NOT provide a diagnosis.
- Use non-diagnostic language ("may", "could", "possible").
- Never skip straight to a triage response without gathering enough symptoms first.

When you decide you have enough information, end with:
"This is not a medical diagnosis. Please consult a healthcare professional."
`;

function getApiKey() {
  // NOTE: for production you should NOT call Anthropic directly from the browser.
  // Your backend teammate can later replace this with a secure proxy.
  return import.meta.env.VITE_ANTHROPIC_API_KEY as string | undefined;
}

export async function sendToAnthropic(params: {
  messages: AnthropicMessage[];
  model?: string;
}): Promise<string> {
  const apiKey = getApiKey();
  if (!apiKey) throw new Error("Missing VITE_ANTHROPIC_API_KEY");

  const res = await fetch(API_URL, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01"
    },
    body: JSON.stringify({
      model: params.model ?? (import.meta.env.VITE_ANTHROPIC_MODEL as string) ?? "claude-3-5-sonnet-latest",
      max_tokens: 700,
      system: SYSTEM_PROMPT,
      messages: params.messages
    })
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Anthropic error ${res.status}: ${text || res.statusText}`);
  }

  const data = (await res.json()) as AnthropicResponse;
  const textParts = (data.content || [])
    .filter((p) => p.type === "text" && typeof p.text === "string")
    .map((p) => p.text as string);
  return textParts.join("\n").trim();
}

