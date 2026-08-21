"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  BarChart3,
  Check,
  ChevronDown,
  FileDown,
  FileText,
  SquarePen,
  Sparkles,
  Square,
  Table2,
  Type,
  Wand2,
} from "lucide-react";

import { MessageBubble } from "@/components/MessageBubble";
import { openChatStream } from "@/lib/sse";
import type { ChatMessage, OutputType, StepEvent } from "@/types/agent";

type OutputOption = { label: string; value: OutputType | "auto"; icon: typeof Wand2; hint: string };

const outputOptions: OutputOption[] = [
  { label: "Auto", value: "auto", icon: Wand2, hint: "Let the agent choose" },
  { label: "Text", value: "text", icon: Type, hint: "Written answer" },
  { label: "Table", value: "table", icon: Table2, hint: "Structured rows" },
  { label: "Chart", value: "chart", icon: BarChart3, hint: "Visual comparison" },
  { label: "PDF", value: "pdf", icon: FileDown, hint: "Formatted document" },
  { label: "DOCX", value: "docx", icon: FileText, hint: "Editable document" },
];

function mergeStep(current: StepEvent[], incoming: StepEvent): StepEvent[] {
  const index = current.findIndex((step) => step.step === incoming.step);
  if (index === -1) return [...current, incoming];
  const next = [...current];
  next[index] = incoming;
  return next;
}

function makeId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

const emptyPrompts = [
  "Compare the credibility of recent AI regulations in the US and EU.",
  "Turn the latest findings on battery recycling into a concise table.",
  "Write a short synthesis of the top sources on indoor air quality.",
  "Chart global renewable energy adoption over the last decade.",
];

export function ChatWindow() {
  const [input, setInput] = useState("");
  const [outputType, setOutputType] = useState<OutputType | "auto">("auto");
  const [formatMenuOpen, setFormatMenuOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [liveSteps, setLiveSteps] = useState<StepEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [stuckToBottom, setStuckToBottom] = useState(true);

  const closeStreamRef = useRef<(() => void) | null>(null);
  const messageListRef = useRef<HTMLDivElement | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const formatMenuRef = useRef<HTMLDivElement | null>(null);
  const shouldStickToBottomRef = useRef(true);
  const turnStartRef = useRef<number | null>(null);

  const selectedOption = outputOptions.find((option) => option.value === outputType) ?? outputOptions[0];

  function scrollToBottom(behavior: ScrollBehavior = "smooth") {
    if (!shouldStickToBottomRef.current) return;
    messageEndRef.current?.scrollIntoView({ block: "end", behavior });
  }

  function resizeTextarea() {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const nextHeight = Math.max(24, Math.min(textarea.scrollHeight, 200));
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > 200 ? "auto" : "hidden";
  }

  useEffect(() => {
    scrollToBottom();
  }, [messages, liveSteps, isStreaming]);

  useEffect(() => {
    resizeTextarea();
  }, [input]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (formatMenuRef.current && !formatMenuRef.current.contains(event.target as Node)) {
        setFormatMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => () => closeStreamRef.current?.(), []);

  function submitMessage(message: string) {
    if (!message || isStreaming) return;

    closeStreamRef.current?.();
    setInput("");
    setLiveSteps([]);
    setIsStreaming(true);
    setStuckToBottom(true);
    shouldStickToBottomRef.current = true;
    turnStartRef.current = Date.now();

    setMessages((current) => [...current, { id: makeId(), role: "user", content: message }]);

    closeStreamRef.current = openChatStream(
      {
        message,
        outputType: outputType === "auto" ? undefined : outputType,
        sessionId: sessionId ?? undefined,
      },
      {
        onStep: (event) => setLiveSteps((current) => mergeStep(current, event)),
        onComplete: (payload) => {
          if (payload.session_id) setSessionId(payload.session_id);
          const durationMs = turnStartRef.current ? Date.now() - turnStartRef.current : undefined;

          setMessages((current) => {
            let finalSteps: StepEvent[] = [];
            setLiveSteps((steps) => {
              finalSteps = steps;
              return steps;
            });
            return [
              ...current,
              {
                id: makeId(),
                role: "assistant",
                content: payload.answer || "No answer returned.",
                output_type: payload.output_type ?? (outputType === "auto" ? undefined : outputType),
                outputMode: outputType === "auto" ? "auto" : "explicit",
                artifact: payload.artifact ?? null,
                sources: payload.sources ?? [],
                steps: finalSteps,
                durationMs,
              },
            ];
          });
          setIsStreaming(false);
          closeStreamRef.current?.();
          closeStreamRef.current = null;
        },
        onError: () => {
          const durationMs = turnStartRef.current ? Date.now() - turnStartRef.current : undefined;
          setMessages((current) => {
            let finalSteps: StepEvent[] = [];
            setLiveSteps((steps) => {
              finalSteps = steps;
              return steps;
            });
            return [
              ...current,
              {
                id: makeId(),
                role: "assistant",
                content: "The research stream stopped unexpectedly. Check that the FastAPI backend is running.",
                steps: finalSteps,
                durationMs,
                isError: true,
              },
            ];
          });
          setIsStreaming(false);
          closeStreamRef.current?.();
          closeStreamRef.current = null;
        },
      },
    );
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitMessage(input.trim());
  }

  function handleStopStreaming() {
    closeStreamRef.current?.();
    closeStreamRef.current = null;
    setIsStreaming(false);
    const durationMs = turnStartRef.current ? Date.now() - turnStartRef.current : undefined;
    setMessages((current) => [
      ...current,
      {
        id: makeId(),
        role: "assistant",
        content: "Stopped by user.",
        steps: liveSteps,
        durationMs,
        isError: true,
      },
    ]);
    setLiveSteps([]);
  }

  function handleNewChat() {
    closeStreamRef.current?.();
    closeStreamRef.current = null;
    setInput("");
    setMessages([]);
    setLiveSteps([]);
    setSessionId(null);
    setIsStreaming(false);
  }

  function handleTextareaKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  function handleScroll() {
    const container = messageListRef.current;
    if (!container) return;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    const stuck = distanceFromBottom < 96;
    shouldStickToBottomRef.current = stuck;
    setStuckToBottom(stuck);
  }

  const hasMessages = messages.length > 0 || isStreaming;

  return (
    <div className="mx-auto flex h-dvh max-w-[1000px] flex-col">
      <header className="flex shrink-0 items-center justify-between px-4 py-3.5 sm:px-6">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--app-accent)] text-[var(--app-accent-text)]">
            <Sparkles className="h-4 w-4" />
          </span>
          <span className="text-sm font-medium text-[var(--app-text-primary)]">Adaptive Research Agent</span>
        </div>
        <button
          type="button"
          onClick={handleNewChat}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-3 py-1.5 text-xs font-medium text-[var(--app-text-secondary)] transition hover:border-[var(--app-accent)]/50 hover:text-[var(--app-text-primary)]"
        >
          <SquarePen className="h-3.5 w-3.5" />
          New chat
        </button>
      </header>

      <div className="relative flex min-h-0 flex-1 flex-col">
        {hasMessages ? (
          <div
            ref={messageListRef}
            onScroll={handleScroll}
            className="min-h-0 flex-1 overflow-y-auto px-4 pb-4 sm:px-6"
          >
            <div className="mx-auto flex max-w-[760px] flex-col gap-5 pb-6 pt-2">
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              {isStreaming ? (
                <MessageBubble
                  message={{
                    id: "streaming",
                    role: "assistant",
                    content: "",
                    steps: liveSteps,
                    isStreaming: true,
                  }}
                />
              ) : null}
              <div ref={messageEndRef} />
            </div>
          </div>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center px-4 pb-24">
            <div className="w-full max-w-[640px]">
              <div className="mb-8 flex flex-col items-center text-center">
                <span className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--app-accent)] text-[var(--app-accent-text)]">
                  <Sparkles className="h-5 w-5" />
                </span>
                <h1 className="text-[26px] font-semibold text-[var(--app-text-primary)]">
                  What should we look into?
                </h1>
                <p className="mt-2 max-w-md text-sm leading-6 text-[var(--app-text-secondary)]">
                  Ask for a quick brief, deep research, a comparison table, or a chart — watch the agent
                  plan, search, and synthesize in real time.
                </p>
              </div>

              <form onSubmit={handleSubmit}>
                <ChatInputBar
                  input={input}
                  setInput={setInput}
                  textareaRef={textareaRef}
                  onKeyDown={handleTextareaKeyDown}
                  isStreaming={isStreaming}
                  onStop={handleStopStreaming}
                  formatMenuOpen={formatMenuOpen}
                  setFormatMenuOpen={setFormatMenuOpen}
                  formatMenuRef={formatMenuRef}
                  selectedOption={selectedOption}
                  outputType={outputType}
                  setOutputType={setOutputType}
                />
              </form>

              <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
                {emptyPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => submitMessage(prompt)}
                    className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-3.5 py-3 text-left text-sm leading-5 text-[var(--app-text-secondary)] transition hover:border-[var(--app-accent)]/50 hover:bg-[var(--app-surface)] hover:text-[var(--app-text-primary)]"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {!stuckToBottom && hasMessages ? (
          <button
            type="button"
            onClick={() => {
              shouldStickToBottomRef.current = true;
              setStuckToBottom(true);
              messageEndRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
            }}
            className="absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full border border-[var(--app-border)] bg-[var(--app-panel)] p-2 text-[var(--app-text-secondary)] shadow-floating transition hover:text-[var(--app-text-primary)]"
            aria-label="Jump to latest"
          >
            <ChevronDown className="h-4 w-4" />
          </button>
        ) : null}
      </div>

      {hasMessages ? (
        <div className="relative z-20 shrink-0 px-4 pb-4 pt-1 sm:px-6">
          <form onSubmit={handleSubmit} className="mx-auto max-w-[760px]">
            <ChatInputBar
              input={input}
              setInput={setInput}
              textareaRef={textareaRef}
              onKeyDown={handleTextareaKeyDown}
              isStreaming={isStreaming}
              onStop={handleStopStreaming}
              formatMenuOpen={formatMenuOpen}
              setFormatMenuOpen={setFormatMenuOpen}
              formatMenuRef={formatMenuRef}
              selectedOption={selectedOption}
              outputType={outputType}
              setOutputType={setOutputType}
            />
          </form>
          <p className="mx-auto mt-2 max-w-[760px] text-center text-[11px] text-[var(--app-text-tertiary)]">
            Responses may include sourced findings — verify anything important.
          </p>
        </div>
      ) : null}
    </div>
  );
}

function ChatInputBar({
  input,
  setInput,
  textareaRef,
  onKeyDown,
  isStreaming,
  onStop,
  formatMenuOpen,
  setFormatMenuOpen,
  formatMenuRef,
  selectedOption,
  outputType,
  setOutputType,
}: {
  input: string;
  setInput: (value: string) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement>;
  onKeyDown: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  isStreaming: boolean;
  onStop: () => void;
  formatMenuOpen: boolean;
  setFormatMenuOpen: (value: boolean | ((v: boolean) => boolean)) => void;
  formatMenuRef: React.RefObject<HTMLDivElement>;
  selectedOption: OutputOption;
  outputType: OutputType | "auto";
  setOutputType: (value: OutputType | "auto") => void;
}) {
  const SelectedIcon = selectedOption.icon;

  return (
    <div className="rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel)] shadow-panel transition focus-within:border-[var(--app-accent)]/50">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(event) => setInput(event.target.value)}
        onKeyDown={onKeyDown}
        rows={1}
        disabled={isStreaming}
        placeholder="Ask for a quick brief, deep research, a comparison table, or a chart..."
        className="max-h-[200px] w-full resize-none bg-transparent px-4 pb-2 pt-3.5 text-[15px] leading-6 text-[var(--app-text-primary)] outline-none placeholder:text-[var(--app-text-tertiary)] disabled:cursor-not-allowed"
      />

      <div className="flex items-center justify-between gap-2 px-2.5 pb-2.5 pt-1">
        <div ref={formatMenuRef} className="relative">
          <button
            type="button"
            onClick={() => setFormatMenuOpen((value) => !value)}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition ${
              outputType === "auto"
                ? "border-[var(--app-border)] bg-[var(--app-surface)] text-[var(--app-text-secondary)] hover:text-[var(--app-text-primary)]"
                : "border-[var(--app-accent)]/40 bg-[var(--app-accent-soft)] text-[var(--app-accent)]"
            }`}
          >
            <SelectedIcon className="h-3.5 w-3.5" />
            {selectedOption.label}
            <ChevronDown className={`h-3 w-3 transition-transform ${formatMenuOpen ? "rotate-180" : ""}`} />
          </button>

          {formatMenuOpen ? (
            <div
              style={{ backgroundColor: "#242220" }}
              className="absolute bottom-full left-0 z-50 mb-2 w-56 overflow-hidden rounded-xl border border-[var(--app-border)] p-1 shadow-floating"
            >
              {outputOptions.map((option) => {
                const Icon = option.icon;
                const active = option.value === outputType;
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => {
                      setOutputType(option.value);
                      setFormatMenuOpen(false);
                    }}
                    className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition ${
                      active
                        ? "bg-[var(--app-accent-soft)] text-[var(--app-accent)]"
                        : "text-[var(--app-text-primary)] hover:bg-[var(--app-surface-hover)]"
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="flex-1">
                      <span className="block font-medium">{option.label}</span>
                      <span className={`block text-xs ${active ? "text-[var(--app-accent)]" : "text-[var(--app-text-secondary)]"}`}>
                        {option.hint}
                      </span>
                    </span>
                    {active ? <Check className="h-3.5 w-3.5 shrink-0" /> : null}
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>

        {isStreaming ? (
          <button
            type="button"
            onClick={onStop}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--app-text-primary)] text-[var(--app-bg)] transition hover:opacity-90"
            aria-label="Stop generating"
          >
            <Square className="h-3.5 w-3.5" fill="currentColor" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim()}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--app-accent)] text-[var(--app-accent-text)] transition hover:bg-[var(--app-accent-hover)] disabled:cursor-not-allowed disabled:bg-[var(--app-surface)] disabled:text-[var(--app-text-tertiary)]"
            aria-label="Send message"
          >
            <ArrowUp className="h-4 w-4" strokeWidth={2.5} />
          </button>
        )}
      </div>
    </div>
  );
}
