import type { ChatMessage, ChatSession, CompletionPayload, OutputType } from "@/types/agent";

export async function getChatSessions(): Promise<ChatSession[]> {
  const response = await fetch("/api/sessions", { cache: "no-store" });
  if (!response.ok) throw new Error(`Sessions request failed with ${response.status}`);
  return response.json();
}

export async function getChatMessages(sessionId: string): Promise<ChatMessage[]> {
  const response = await fetch(`/api/sessions/${sessionId}/messages`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Messages request failed with ${response.status}`);
  return response.json();
}


export async function sendChat(message: string, outputType?: OutputType): Promise<CompletionPayload> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, output_type: outputType }),
  });

  if (!response.ok) {
    throw new Error(`Chat request failed with ${response.status}`);
  }

  return response.json();
}
