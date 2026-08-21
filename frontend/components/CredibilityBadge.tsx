"use client";

type CredibilityTier = {
  label: "High" | "Medium" | "Low" | "Unknown";
  colorVar: string;
};

function tierForScore(score: number): CredibilityTier {
  if (score >= 0.75) {
    return { label: "High", colorVar: "var(--cred-high)" };
  }
  if (score >= 0.5) {
    return { label: "Medium", colorVar: "var(--cred-medium)" };
  }
  return { label: "Low", colorVar: "var(--cred-low)" };
}

export function CredibilityBadge({ score }: { score: number | null | undefined }) {
  const hasScore = typeof score === "number" && Number.isFinite(score);
  const numericScore = hasScore ? score : null;
  const tier = hasScore
    ? tierForScore(score)
    : { label: "Unknown" as const, colorVar: "var(--cred-unknown)" };

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-[var(--app-border)] bg-[var(--app-bg)]/60 px-2 py-0.5 text-xs font-medium"
      style={{ color: tier.colorVar }}
      title={numericScore === null ? "Credibility score unavailable" : `Credibility score: ${numericScore.toFixed(2)}`}
      aria-label={`${tier.label} credibility`}
    >
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: tier.colorVar }} />
      {tier.label}
    </span>
  );
}
