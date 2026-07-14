import type { CompletionPayload, OutputType } from "@/types/agent";


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
