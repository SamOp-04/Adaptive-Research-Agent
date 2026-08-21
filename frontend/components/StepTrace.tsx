"use client";

import { useEffect, useState } from "react";
import {
  Brain,
  Check,
  ChevronDown,
  ClipboardList,
  Loader2,
  Route,
  Search,
  Sparkles,
  X,
} from "lucide-react";

import type { StepEvent, StepStatus } from "@/types/agent";

const STEP_META: Record<string, { label: string; icon: typeof Brain }> = {
  intent: { label: "Reading the request", icon: Brain },
  planning: { label: "Planning research", icon: ClipboardList },
  research: { label: "Searching sources", icon: Search },
  synthesis: { label: "Synthesizing findings", icon: Sparkles },
  output: { label: "Formatting the answer", icon: Route },
};

function metaFor(step: string) {
  return (
    STEP_META[step] ?? {
      label: step.charAt(0).toUpperCase() + step.slice(1).replace(/_/g, " "),
      icon: Sparkles,
    }
  );
}

function StatusIcon({ status }: { status: StepStatus }) {
  if (status === "completed") {
    return (
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--cred-high)]/15 text-[var(--cred-high)]">
        <Check className="h-3 w-3" strokeWidth={3} />
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--app-danger)]/15 text-[var(--app-danger)]">
        <X className="h-3 w-3" strokeWidth={3} />
      </span>
    );
  }
  return (
    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--app-accent)]/15 text-[var(--app-accent)]">
      <Loader2 className="h-3 w-3 animate-spin" strokeWidth={3} />
    </span>
  );
}

function formatDuration(ms?: number) {
  if (!ms || ms < 0) return null;
  const seconds = ms / 1000;
  if (seconds < 1) return "under a second";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes}m ${rest}s`;
}

export function StepTrace({
  steps,
  isLive = false,
  durationMs,
  defaultOpen,
}: {
  steps: StepEvent[];
  isLive?: boolean;
  durationMs?: number;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen ?? isLive);

  useEffect(() => {
    if (isLive) setOpen(true);
  }, [isLive]);

  const hasFailure = steps.some((step) => step.status === "failed");
  const latestRunning = [...steps].reverse().find((step) => step.status === "running");
  const duration = formatDuration(durationMs);

  const summary = isLive
    ? latestRunning
      ? metaFor(latestRunning.step).label
      : "Working…"
    : hasFailure
      ? "Ran into an issue"
      : duration
        ? `Thought for ${duration}`
        : "Research trace";

  if (steps.length === 0 && !isLive) {
    return null;
  }

  return (
    <div className="mb-3 rounded-xl border border-[var(--app-border)] bg-[var(--app-surface)]/60">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left transition hover:bg-[var(--app-surface-hover)]"
      >
        {isLive ? (
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="pulse-dot absolute inline-flex h-2 w-2 rounded-full bg-[var(--app-accent)]" />
          </span>
        ) : hasFailure ? (
          <span className="h-2 w-2 shrink-0 rounded-full bg-[var(--app-danger)]" />
        ) : (
          <span className="h-2 w-2 shrink-0 rounded-full bg-[var(--cred-high)]" />
        )}
        <span
          className={`flex-1 truncate text-sm font-medium ${
            isLive ? "shimmer-text" : "text-[var(--app-text-secondary)]"
          }`}
        >
          {summary}
        </span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-[var(--app-text-tertiary)] transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open ? (
        <div className="animate-collapse-in space-y-0 border-t border-[var(--app-border)] px-3 py-3">
          {steps.map((step, index) => {
            const { label, icon: Icon } = metaFor(step.step);
            const isLast = index === steps.length - 1;
            return (
              <div key={`${step.step}-${index}`} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <StatusIcon status={step.status} />
                  {!isLast ? <span className="my-0.5 w-px flex-1 bg-[var(--app-border)]" /> : null}
                </div>
                <div className={`min-w-0 flex-1 ${isLast ? "" : "pb-3"}`}>
                  <div className="flex items-center gap-1.5 text-sm text-[var(--app-text-primary)]">
                    <Icon className="h-3.5 w-3.5 text-[var(--app-text-tertiary)]" />
                    <span className="font-medium">{label}</span>
                  </div>
                  {step.status === "failed" ? (
                    <p className="mt-0.5 text-xs leading-5 text-[var(--app-danger)]">{step.message}</p>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
