import type { CompletionPayload, OutputType, StepEvent } from "@/types/agent";


type StreamRequest = {
  message: string;
  outputType?: OutputType;
};

type StreamHandlers = {
  onStep: (event: StepEvent) => void;
  onComplete: (payload: CompletionPayload) => void;
  onError: (error: Event) => void;
};

export function openChatStream(request: StreamRequest, handlers: StreamHandlers) {
  const params = new URLSearchParams({ q: request.message });
  if (request.outputType) {
    params.set("output_type", request.outputType);
  }

  const source = new EventSource(`/api/chat?${params.toString()}`);

  source.addEventListener("step", (event) => {
    const parsed = JSON.parse((event as MessageEvent).data) as StepEvent;
    if (parsed.step === "complete") {
      handlers.onComplete(parsed.payload as CompletionPayload);
      source.close();
      return;
    }
    handlers.onStep(parsed);
  });

  source.onerror = (event) => {
    handlers.onError(event);
    source.close();
  };

  return () => source.close();
}
