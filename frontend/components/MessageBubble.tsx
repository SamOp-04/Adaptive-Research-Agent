"use client";

import { useEffect, useState } from "react";
import {
  BarChart3,
  Check,
  ClipboardCopy,
  ExternalLink,
  FileDown,
  FileText,
  Sparkles,
  SlidersHorizontal,
  Table2,
  Type,
} from "lucide-react";
import Markdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/cjs/styles/prism";
import remarkGfm from "remark-gfm";

import { FileDownloadCard } from "@/components/FileDownloadCard";
import { StepTrace } from "@/components/StepTrace";
import { ChartArtifact } from "@/components/artifacts/ChartArtifact";
import { TableArtifact } from "@/components/artifacts/TableArtifact";
import type { ChatMessage, FileArtifact } from "@/types/agent";

function formatLabel(outputType?: ChatMessage["output_type"]) {
  switch (outputType) {
    case "chart":
      return "Chart";
    case "table":
      return "Table";
    case "docx":
      return "DOCX";
    case "pdf":
      return "PDF";
    case "text":
    default:
      return "Text";
  }
}

function formatIcon(outputType?: ChatMessage["output_type"]) {
  switch (outputType) {
    case "chart":
      return BarChart3;
    case "table":
      return Table2;
    case "docx":
      return FileText;
    case "pdf":
      return FileDown;
    case "text":
    default:
      return Type;
  }
}

function isFileArtifact(artifact: ChatMessage["artifact"]): artifact is FileArtifact {
  return artifact?.type === "docx" || artifact?.type === "pdf" || artifact?.type === "file";
}

function buildCopyText(message: ChatMessage) {
  const chunks = [message.content.trim()];

  if (message.artifact?.type === "table") {
    const columns = message.artifact.columns ?? Object.keys(message.artifact.rows[0] ?? {});
    const header = columns.join(" | ");
    const separator = columns.map(() => "---").join(" | ");
    const rows = message.artifact.rows.map((row) =>
      columns.map((column) => String(row[column] ?? "")).join(" | "),
    );
    chunks.push([header, separator, ...rows].join("\n"));
  }

  if (isFileArtifact(message.artifact)) {
    chunks.push(`${message.artifact.fileName ?? "Generated file"}: ${message.artifact.href}`);
  }

  return chunks.filter(Boolean).join("\n\n");
}

function displayDomain(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function normalizeMarkdown(content: string) {
  return content
    .replace(/\\\*\*/g, "**")
    .replace(/\\\*/g, "*")
    .replace(/\\_/g, "_")
    .replace(/\\`/g, "`");
}

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 1400);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="group/code relative my-3">
      <button
        type="button"
        onClick={handleCopy}
        className="absolute right-2 top-2 z-10 inline-flex items-center gap-1.5 rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-2 py-1 text-xs font-medium text-[var(--app-text-secondary)] opacity-0 shadow-floating transition hover:text-[var(--app-text-primary)] group-hover/code:opacity-100 focus-visible:opacity-100"
        aria-label="Copy code"
      >
        {copied ? <Check className="h-3.5 w-3.5" /> : <ClipboardCopy className="h-3.5 w-3.5" />}
        {copied ? "Copied" : "Copy"}
      </button>
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={language}
        PreTag="div"
        customStyle={{
          margin: 0,
          borderRadius: "0.75rem",
          border: "1px solid var(--app-border)",
          background: "var(--app-panel)",
        }}
        codeTagProps={{
          style: {
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
          },
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="mt-5 text-xl font-semibold text-[var(--app-text-primary)] first:mt-0">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="mt-5 text-lg font-semibold text-[var(--app-text-primary)] first:mt-0">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="mt-4 text-base font-semibold text-[var(--app-text-primary)] first:mt-0">{children}</h3>
        ),
        p: ({ children }) => (
          <p className="whitespace-pre-wrap leading-7 text-[var(--app-text-primary)]">{children}</p>
        ),
        strong: ({ children }) => <strong className="font-semibold text-[var(--app-text-primary)]">{children}</strong>,
        a: ({ children, ...props }) => (
          <a
            className="break-all text-[var(--app-accent)] underline decoration-[var(--app-accent)]/40 underline-offset-2 transition hover:decoration-[var(--app-accent)]"
            target="_blank"
            rel="noreferrer"
            {...props}
          >
            {children}
          </a>
        ),
        ul: ({ children }) => <ul className="my-3 list-disc space-y-1.5 pl-5 marker:text-[var(--app-text-tertiary)]">{children}</ul>,
        ol: ({ children }) => <ol className="my-3 list-decimal space-y-1.5 pl-5 marker:text-[var(--app-text-tertiary)]">{children}</ol>,
        li: ({ children }) => <li className="leading-7 text-[var(--app-text-primary)]">{children}</li>,
        hr: () => <hr className="my-5 border-[var(--app-border)]" />,
        blockquote: ({ children }) => (
          <blockquote className="my-3 border-l-2 border-[var(--app-accent)]/40 pl-4 text-[var(--app-text-secondary)]">
            {children}
          </blockquote>
        ),
        table: ({ children }) => (
          <div className="my-3 max-w-full overflow-x-auto rounded-lg border border-[var(--app-border)]">
            <table className="w-full table-fixed text-left text-sm">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-[var(--app-surface)]/60">{children}</thead>,
        th: ({ children }) => (
          <th className="break-words px-3 py-2 text-xs font-medium uppercase tracking-wide text-[var(--app-text-secondary)]">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="break-words border-t border-[var(--app-border-soft)] px-3 py-2 align-top text-[var(--app-text-primary)]">
            {children}
          </td>
        ),
        code: ({ inline, className, children, ...props }: any) => {
          const match = /language-(\w+)/.exec(className || "");
          const text = String(children).replace(/\n$/, "");

          if (inline) {
            return (
              <code
                className="rounded bg-[var(--app-surface)] px-1.5 py-0.5 font-mono text-[0.9em] text-[var(--app-text-primary)]"
                {...props}
              >
                {children}
              </code>
            );
          }

          return <CodeBlock language={match?.[1] ?? "text"} code={text} />;
        },
      }}
    >
      {normalizeMarkdown(content)}
    </Markdown>
  );
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const OutputIcon = formatIcon(message.output_type);
  const hasArtifact = Boolean(message.artifact);
  const visibleSources = !isUser ? (message.sources ?? []) : [];
  const showCopy =
    !isUser && message.content && !message.isStreaming && !message.isError;

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 1400);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(buildCopyText(message));
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  if (isUser) {
    return (
      <article className="group flex animate-fade-in-up items-center justify-end gap-2">
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex shrink-0 items-center gap-1.5 text-xs font-medium text-[var(--app-text-tertiary)] opacity-0 transition hover:text-[var(--app-text-primary)] group-hover:opacity-100 focus-visible:opacity-100"
          aria-label="Copy sent message"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <ClipboardCopy className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
        <div className="max-w-[min(680px,85%)] rounded-2xl rounded-br-md bg-[var(--app-message-user)] px-5 py-3 text-[15px] leading-6 text-[var(--app-text-primary)]">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </article>
    );
  }

  return (
    <article className="group flex animate-fade-in-up justify-start gap-3">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--app-accent-soft)] text-[var(--app-accent)]">
        <Sparkles className="h-3.5 w-3.5" />
      </div>

      <div className="min-w-0 max-w-[min(760px,90%)] flex-1">
        {message.steps && message.steps.length > 0 ? (
          <StepTrace
            steps={message.steps}
            isLive={message.isStreaming}
            durationMs={message.durationMs}
          />
        ) : null}

        {message.isError ? (
          <p className="text-[15px] leading-7 text-[var(--app-danger)]">{message.content}</p>
        ) : message.content && !message.isStreaming ? (
          <div className="rounded-2xl rounded-bl-md bg-[var(--app-message-assistant)] px-5 py-3 text-[15px]">
            <MarkdownContent content={message.content} />
          </div>
        ) : null}

        {message.artifact?.type === "chart" ? <ChartArtifact data={message.artifact.data} /> : null}

        {message.artifact?.type === "table" ? (
          <TableArtifact rows={message.artifact.rows} columns={message.artifact.columns} />
        ) : null}

        {isFileArtifact(message.artifact) ? (
          <div className="mt-3 max-w-sm">
            <FileDownloadCard
              fileName={message.artifact.fileName ?? "Generated report"}
              fileType={message.artifact.type}
              href={message.artifact.href}
            />
          </div>
        ) : null}

        {visibleSources.length ? (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {visibleSources.slice(0, 6).map((source, index) => (
              <a
                key={`${source.url}-${index}`}
                href={source.url}
                target="_blank"
                rel="noreferrer"
                title={source.title || source.url}
                className="inline-flex max-w-[220px] items-center gap-1.5 rounded-full border border-[var(--app-border)] bg-[var(--app-panel)] px-2.5 py-1 text-xs text-[var(--app-text-secondary)] transition hover:border-[var(--app-accent)]/50 hover:text-[var(--app-text-primary)]"
              >
                <span className="truncate">{displayDomain(source.url)}</span>
                <ExternalLink className="h-3 w-3 shrink-0 opacity-60" />
              </a>
            ))}
          </div>
        ) : null}

        {!message.isStreaming && !message.isError && (message.content || hasArtifact) ? (
          <div className="mt-2 flex items-center gap-3 opacity-0 transition group-hover:opacity-100 focus-within:opacity-100">
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--app-text-tertiary)]">
              <OutputIcon className="h-3 w-3" />
              {message.outputMode === "explicit" ? (
                <SlidersHorizontal className="h-3 w-3" />
              ) : null}
              {formatLabel(message.output_type)}
            </span>
            {showCopy ? (
              <button
                type="button"
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--app-text-tertiary)] transition hover:text-[var(--app-accent)]"
                aria-label="Copy response"
              >
                {copied ? <Check className="h-3.5 w-3.5" /> : <ClipboardCopy className="h-3.5 w-3.5" />}
                {copied ? "Copied" : "Copy"}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </article>
  );
}