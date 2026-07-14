import type { StepEvent } from "@/types/agent";


const statusClass: Record<StepEvent["status"], string> = {
  running: "border-[var(--app-border)] bg-[var(--app-panel)] text-[var(--app-text-primary)]",
  completed: "border-[var(--app-border)] bg-[var(--app-panel)] text-[var(--app-text-primary)]",
  // Red is reserved for actual errors in DESIGN.md, but no error token exists yet.
  failed: "border-red-200 bg-red-50 text-red-950",
};

const statusDotClass: Record<StepEvent["status"], string> = {
  running: "bg-[var(--app-accent)]",
  completed: "bg-[var(--cred-high)]",
  failed: "bg-red-600",
};

const statusLabel: Record<StepEvent["status"], string> = {
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};

export function StepTrace({ steps }: { steps: StepEvent[] }) {
  return (
    <section className="rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel)] p-4">
      <h2 className="text-sm font-semibold text-[var(--app-text-primary)]">Step trace</h2>
      <div className="mt-3 space-y-2" aria-live="polite" aria-atomic="false">
        {steps.length === 0 ? (
          <p className="text-sm text-[var(--app-text-secondary)]">Research steps will appear while a query runs.</p>
        ) : (
          steps.map((step, index) => (
            <div
              key={`${step.step}-${index}`}
              className={`rounded-xl border px-3 py-2 text-sm ${statusClass[step.status]}`}
            >
              <div className="flex items-start gap-2">
                <span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${statusDotClass[step.status]}`} aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="font-medium capitalize">{step.step}</div>
                    <span className="rounded-full border border-current/10 bg-[var(--app-bg)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] opacity-80">
                      {statusLabel[step.status]}
                    </span>
                  </div>
                  <div className="mt-1 text-xs leading-5 opacity-80">{step.message}</div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
