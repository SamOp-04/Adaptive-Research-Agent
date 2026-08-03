"use client";

import { useEffect, useState } from "react";
import {
  BarChart3,
  Check,
  ClipboardCopy,
  FileDown,
  FileText,
  SlidersHorizontal,
  Sparkles,
  Table2,
  Type,
} from "lucide-react";
import Markdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/cjs/styles/prism";
import remarkGfm from "remark-gfm";

import { FileDownloadCard } from "@/components/FileDownloadCard";
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

function isFileArtifact(artifact: ChatMessage["artifact"]): artifact is FileArtifact {
  return artifact?.type === "docx" || artifact?.type === "pdf" || artifact?.type === "file";
}

function isLongTextContent(content: string) {
  const paragraphs = content
    .trim()
    .split(/\n\s*\n/)
    .filter(Boolean);

  // Follow-up option: move this heuristic to a backend text_length subtype if client-side rendering ever drifts.
  return content.trim().length > 500 || paragraphs.length > 1;
}

function MarkdownContent({ content, isLongText }: { content: string; isLongText?: boolean }) {
  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      components={{
        h2: ({ children }) => (
          <h2 className="mt-5 text-lg font-semibold text-[var(--app-accent)] first:mt-0">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="mt-4 text-base font-semibold text-[var(--app-accent)] first:mt-0">{children}</h3>
        ),
        p: ({ children }) => (
          <p className={`whitespace-pre-wrap text-inherit ${isLongText ? "leading-relaxed" : "leading-7"}`}>
            {children}
          </p>
        ),
        a: ({ children, ...props }) => (
          <a className="underline underline-offset-2 transition hover:text-[var(--app-accent)]" target="_blank" rel="noreferrer" {...props}>
            {children}
          </a>
        ),
        ul: ({ children }) => <ul className="my-3 list-disc space-y-1 pl-5">{children}</ul>,
        ol: ({ children }) => <ol className="my-3 list-decimal space-y-1 pl-5">{children}</ol>,
        li: ({ children }) => <li className="leading-7">{children}</li>,
        blockquote: ({ children }) => (
          <blockquote className="my-3 border-l-4 border-[var(--app-border)] pl-4 text-[var(--app-text-secondary)]">{children}</blockquote>
        ),
        code: ({ inline, className, children, ...props }: any) => {
          const match = /language-(\w+)/.exec(className || "");
          const text = String(children).replace(/\n$/, "");

          if (inline) {
            return (
              <code className="rounded bg-[var(--app-panel)] px-1.5 py-0.5 font-mono text-[0.95em] text-[var(--app-text-primary)]" {...props}>
                {children}
              </code>
            );
          }

          return (
            <SyntaxHighlighter
              style={vscDarkPlus}
              language={match?.[1] ?? "text"}
              PreTag="div"
              customStyle={{ marginTop: "0.75rem", marginBottom: "0.75rem", borderRadius: "0.75rem" }}
              codeTagProps={{
                style: {
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
                },
              }}
              {...props}
            >
              {text}
            </SyntaxHighlighter>
          );
        },
      }}
    >
      {content}
    </Markdown>
  );
}


export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const OutputIcon = formatIcon(message.output_type);
  const isAssistantText = !isUser && !message.artifact;
  const isLongText = isAssistantText && isLongTextContent(message.content);
  const visibleSources = !isUser && !message.artifact ? (message.sources ?? []) : [];
  const bubbleClass = isUser
    ? "max-w-[min(760px,100%)] rounded-2xl bg-[var(--app-accent)] px-4 py-3 text-sm leading-6 text-[var(--app-bg)] sm:max-w-[min(760px,90%)]"
    : isLongText
      ? "max-w-2xl rounded-md border border-[var(--app-border)] bg-[var(--app-bg)] p-6 text-base leading-relaxed text-[var(--app-text-primary)]"
      : isAssistantText
        ? "max-w-[min(760px,100%)] rounded-2xl bg-[var(--app-panel)] px-4 py-3 text-base leading-relaxed text-[var(--app-text-primary)] sm:max-w-[min(760px,90%)]"
        : "max-w-[min(760px,100%)] rounded-2xl border border-[var(--app-border)] bg-[var(--app-bg)] px-4 py-3 text-sm leading-6 text-[var(--app-text-primary)] sm:max-w-[min(760px,90%)]";

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

  return (
    <article className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={bubbleClass}>
        {!isUser ? (
          <div className="mb-3 flex items-start justify-between gap-3">
            <div
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${
                message.outputMode === "auto"
                  ? "border-[var(--app-border)] bg-[var(--app-panel)] text-[var(--app-text-secondary)]"
                  : "border-[var(--app-border)] bg-[var(--app-panel)] text-[var(--app-accent)]"
              }`}
            >
              {message.outputMode === "auto" ? <Sparkles className="h-3.5 w-3.5" /> : <SlidersHorizontal className="h-3.5 w-3.5" />}
              <OutputIcon className="h-3.5 w-3.5" />
              <span>{message.outputMode === "auto" ? `Auto-selected: ${formatLabel(message.output_type)}` : formatLabel(message.output_type)}</span>
            </div>

            {(message.content || message.artifact?.type === "table") && message.content !== "Working through the research steps..." ? (
              <button
                type="button"
                onClick={handleCopy}
                className="inline-flex items-center gap-2 rounded-full border border-[var(--app-border)] bg-[var(--app-bg)] px-3 py-1 text-xs font-medium text-[var(--app-text-secondary)] transition hover:border-[var(--app-accent)] hover:text-[var(--app-accent)]"
                aria-label="Copy response"
              >
                {copied ? <Check className="h-3.5 w-3.5" /> : <ClipboardCopy className="h-3.5 w-3.5" />}
                {copied ? "Copied" : "Copy"}
              </button>
            ) : null}
          </div>
        ) : null}

        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <MarkdownContent content={message.content} isLongText={isLongText} />
        )}

        {message.artifact?.type === "chart" ? (
          <ChartArtifact data={message.artifact.data} />
        ) : null}

        {message.artifact?.type === "table" ? (
          <TableArtifact rows={message.artifact.rows} columns={message.artifact.columns} />
        ) : null}

        {isFileArtifact(message.artifact) ? (
          <div className="mt-4">
            <FileDownloadCard
              fileName={message.artifact.fileName ?? "Generated report"}
              fileType={message.artifact.type}
              href={message.artifact.href}
            />
          </div>
        ) : null}

        {visibleSources.length ? (
          <div className="mt-3 border-t border-current/15 pt-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide opacity-70">Sources</p>
            <ul className="space-y-1">
              {visibleSources.slice(0, 5).map((source) => (
                <li key={source.url} className="truncate">
                  <a className="underline underline-offset-2" href={source.url} target="_blank" rel="noreferrer">
                    {source.title || source.url}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </article>
  );
}
