"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ChevronDown, Loader2, Plus, Square } from "lucide-react";

import { FileDownloadCard } from "@/components/FileDownloadCard";
import { MessageBubble } from "@/components/MessageBubble";
import { StepTrace } from "@/components/StepTrace";
import { openChatStream } from "@/lib/sse";
import type { ChatMessage, FileArtifact, OutputType, StepEvent } from "@/types/agent";

const outputOptions: Array<{ label: string; value: OutputType | "auto" }> = [
  { label: "Auto", value: "auto" },
  { label: "Text", value: "text" },
  { label: "Table", value: "table" },
  { label: "Chart", value: "chart" },
  { label: "PDF", value: "pdf" },
  { label: "DOCX", value: "docx" },
];

function makeId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

function isFileArtifact(artifact: ChatMessage["artifact"]): artifact is FileArtifact {
  return artifact?.type === "docx" || artifact?.type === "pdf" || artifact?.type === "file";
}

const emptyPrompts = [
  "Compare the credibility of recent AI regulations in the US and EU.",
  "Turn the latest findings on battery recycling into a concise table.",
  "Write a short synthesis of the top sources on indoor air quality.",
];

export function ChatWindow() {
  const [input, setInput] = useState("");
  const [outputType, setOutputType] = useState<OutputType | "auto">("auto");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [steps, setSteps] = useState<StepEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const closeStreamRef = useRef<(() => void) | null>(null);
  const messageListRef = useRef<HTMLDivElement | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const shouldStickToBottomRef = useRef(true);

  function scrollToBottom() {
    if (!shouldStickToBottomRef.current) return;
    messageEndRef.current?.scrollIntoView({ block: "end" });
  }

  function resizeTextarea() {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    const nextHeight = Math.max(56, Math.min(textarea.scrollHeight, 240));
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > 240 ? "auto" : "hidden";
  }

  useEffect(() => {
    scrollToBottom();
  }, [messages, steps, isStreaming]);

  useEffect(() => {
    resizeTextarea();
  }, [input]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = input.trim();
    if (!message || isStreaming) return;

    closeStreamRef.current?.();
    setInput("");
    setSteps([]);
    setIsStreaming(true);
    setMessages((current) => [
      ...current,
      { id: makeId(), role: "user", content: message },
    ]);

    closeStreamRef.current = openChatStream(
      {
        message,
        outputType: outputType === "auto" ? undefined : outputType,
        sessionId: sessionId ?? undefined,
      },
      {
        onStep: (event) => setSteps((current) => [...current, event]),
        onComplete: (payload) => {
          if (payload.session_id) {
            setSessionId(payload.session_id);
          }
          setMessages((current) => [
            ...current,
            {
              id: makeId(),
              role: "assistant",
              content: payload.answer || "No answer returned.",
              output_type: payload.output_type ?? (outputType === "auto" ? undefined : outputType),
              outputMode: outputType === "auto" ? "auto" : "explicit",
              artifact: payload.artifact ?? null,
              sources: payload.sources ?? [],
            },
          ]);
          setIsStreaming(false);
          closeStreamRef.current?.();
          closeStreamRef.current = null;
        },
        onError: () => {
          setMessages((current) => [
            ...current,
            {
              id: makeId(),
              role: "assistant",
              content: "The research stream stopped unexpectedly. Check that the FastAPI backend is running.",
            },
          ]);
          setIsStreaming(false);
          closeStreamRef.current?.();
          closeStreamRef.current = null;
        },
      },
    );
  }

  function handleStopStreaming() {
    closeStreamRef.current?.();
    closeStreamRef.current = null;
    setIsStreaming(false);
    setSteps((current) => [
      ...current,
      {
        step: "client",
        status: "failed",
        message: "Stream stopped by user",
        timestamp: new Date().toISOString(),
      },
    ]);
  }

  function handleNewChat() {
    closeStreamRef.current?.();
    closeStreamRef.current = null;
    setInput("");
    setMessages([]);
    setSteps([]);
    setSessionId(null);
    setIsStreaming(false);
  }

  function handleTextareaKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  const latestFileArtifact = [...messages]
    .reverse()
    .map((message) => message.artifact)
    .find(isFileArtifact);

  return (
    <div className="mx-auto flex min-h-full min-h-0 max-w-7xl flex-col gap-4 px-4 py-4 md:grid md:h-full md:grid-cols-[minmax(0,1fr)_320px] md:px-6">
      <section className="flex min-h-[calc(100dvh-2rem)] flex-1 flex-col overflow-hidden rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel)] md:h-full md:min-h-0">
        <header className="border-b border-[var(--app-border)] px-4 py-4">
          <p className="text-sm font-medium text-[var(--app-accent)]">Adaptive Research Agent</p>
          <div className="mt-1 flex items-center justify-between gap-3">
            <h1 className="text-2xl font-semibold tracking-normal text-[var(--app-text-primary)]">Research workspace</h1>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <button
                type="button"
                onClick={handleNewChat}
                className="inline-flex items-center gap-2 rounded-full border border-[var(--app-border)] bg-[var(--app-bg)] px-3 py-1 text-xs font-medium text-[var(--app-text-secondary)] transition hover:border-[var(--app-accent)] hover:text-[var(--app-accent)]"
              >
                <Plus className="h-3.5 w-3.5" />
                New chat
              </button>
              {isStreaming ? (
                <button
                  type="button"
                  onClick={handleStopStreaming}
                  className="inline-flex items-center gap-2 rounded-full border border-[var(--app-border)] bg-[var(--app-bg)] px-3 py-1 text-xs font-medium text-[var(--app-text-secondary)] transition hover:border-[var(--app-accent)] hover:text-[var(--app-accent)]"
                >
                  <Square className="h-3.5 w-3.5" />
                  Stop
                </button>
              ) : null}
              <span className="inline-flex items-center gap-2 rounded-full border border-[var(--app-border)] bg-[var(--app-bg)] px-3 py-1 text-xs font-medium text-[var(--app-text-secondary)]">
                <ChevronDown className="h-3.5 w-3.5" />
                Auto-scroll active
              </span>
            </div>
          </div>
        </header>

        <div
          ref={messageListRef}
          onScroll={() => {
            const container = messageListRef.current;
            if (!container) return;
            const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
            shouldStickToBottomRef.current = distanceFromBottom < 96;
          }}
          className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4"
        >
          {messages.length === 0 && !isStreaming ? (
            <div className="flex min-h-full items-center justify-center py-10">
              <div className="w-full max-w-2xl rounded-2xl border border-dashed border-[var(--app-border)] bg-[var(--app-panel)] p-6 text-[var(--app-text-primary)]">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--app-accent)]">Start here</p>
                <h2 className="mt-2 text-2xl font-semibold text-[var(--app-text-primary)]">Ask a question or force a format.</h2>
                <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--app-text-secondary)]">
                  Use Auto to watch the agent choose a format, or override it with Text, Table, Chart, PDF, or DOCX.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {emptyPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => setInput(prompt)}
                      className="rounded-full border border-[var(--app-border)] bg-[var(--app-bg)] px-3 py-2 text-left text-sm text-[var(--app-text-secondary)] transition hover:border-[var(--app-accent)] hover:text-[var(--app-accent)]"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {isStreaming ? (
            <MessageBubble
              message={{
                id: "streaming",
                role: "assistant",
                content: "Working through the research steps...",
                output_type: outputType === "auto" ? undefined : outputType,
                outputMode: outputType === "auto" ? "auto" : "explicit",
              }}
            />
          ) : null}
          <div ref={messageEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="shrink-0 border-t border-[var(--app-border)] p-4">
          <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <label className="flex w-full flex-col gap-1 text-xs font-medium uppercase tracking-[0.18em] text-[var(--app-text-secondary)] sm:max-w-48">
              Output mode
              <select
                value={outputType}
                onChange={(event) => setOutputType(event.target.value as OutputType | "auto")}
                className="h-11 rounded-md border border-[var(--app-border)] bg-[var(--app-bg)] px-3 text-sm text-[var(--app-text-primary)] outline-none focus:border-[var(--app-accent)] focus:ring-2 focus:ring-[var(--app-accent)]/15"
              >
                {outputOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="inline-flex items-center gap-2 rounded-full border border-[var(--app-border)] bg-[var(--app-bg)] px-3 py-2 text-sm text-[var(--app-text-secondary)]">
              {isStreaming ? <Loader2 className="h-4 w-4 animate-spin text-[var(--app-accent)]" /> : null}
              <span>{isStreaming ? "Thinking: streaming steps and drafting the answer" : "Ready to research"}</span>
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleTextareaKeyDown}
              rows={1}
              disabled={isStreaming}
              placeholder="Ask for a quick brief, deep research, a comparison table, or a chart..."
              className="min-h-14 flex-1 resize-none rounded-md border border-[var(--app-border)] bg-[var(--app-bg)] px-3 py-3 text-sm text-[var(--app-text-primary)] outline-none transition placeholder:text-[var(--app-text-secondary)] focus:border-[var(--app-accent)] focus:ring-2 focus:ring-[var(--app-accent)]/15 disabled:cursor-not-allowed disabled:bg-[var(--app-panel)]"
            />
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              className="h-11 rounded-md bg-[var(--app-accent)] px-5 text-sm font-semibold text-[var(--app-bg)] transition hover:bg-[var(--app-accent-hover)] disabled:cursor-not-allowed disabled:bg-[var(--app-border)] disabled:text-[var(--app-text-secondary)]"
            >
              Send
            </button>
          </div>
        </form>
      </section>

      <aside className="flex flex-col gap-4 md:h-full md:min-h-0 md:overflow-hidden">
        <div className="md:min-h-0 md:flex-1 md:overflow-y-auto">
          <StepTrace steps={steps} />
        </div>
        {latestFileArtifact ? (
          <FileDownloadCard
            fileName={latestFileArtifact.fileName ?? "Generated report"}
            fileType={latestFileArtifact.type}
            href={latestFileArtifact.href}
          />
        ) : (
          <FileDownloadCard
            fileName="Generated reports appear here"
            fileType="docx/pdf"
            href="#"
            disabled
          />
        )}
      </aside>
    </div>
  );
}
