import type { CompletionPayload, OutputType, StepEvent } from "@/types/agent";


type StreamRequest = {
  message: string;
  outputType?: OutputType;
  sessionId?: string;
};

type StreamHandlers = {
  onStep: (event: StepEvent) => void;
  onComplete: (payload: CompletionPayload) => void;
  onError: (error: Event) => void;
};

const STREAM_STALL_TIMEOUT_MS = 120_000;

export function openChatStream(request: StreamRequest, handlers: StreamHandlers) {
  const params = new URLSearchParams({ q: request.message });
  if (request.outputType) {
    params.set("output_type", request.outputType);
  }
  if (request.sessionId) {
    params.set("session_id", request.sessionId);
  }

  const source = new EventSource(`/api/chat?${params.toString()}`);
  let stallTimer: number | null = null;

  function close() {
    if (stallTimer) {
      window.clearTimeout(stallTimer);
      stallTimer = null;
    }
    source.close();
  }

  function resetStallTimer() {
    if (stallTimer) {
      window.clearTimeout(stallTimer);
    }
    stallTimer = window.setTimeout(() => {
      handlers.onError(new Event("timeout"));
      close();
    }, STREAM_STALL_TIMEOUT_MS);
  }

  resetStallTimer();
  source.addEventListener("open", resetStallTimer);

  source.addEventListener("step", (event) => {
    resetStallTimer();
    const parsed = JSON.parse((event as MessageEvent).data) as StepEvent;
    if (parsed.step === "complete") {
      handlers.onComplete(parsed.payload as CompletionPayload);
      close();
      return;
    }
    handlers.onStep(parsed);
  });

  source.onerror = (event) => {
    handlers.onError(event);
    close();
  };

  return close;
}
