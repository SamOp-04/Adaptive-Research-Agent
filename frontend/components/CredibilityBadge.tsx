"use client";

type CredibilityTier = {
  label: "High" | "Medium" | "Low";
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
  const numericScore = typeof score === "number" && Number.isFinite(score) ? score : 0;
  const tier = tierForScore(numericScore);

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-[var(--app-border)] bg-[var(--app-bg)] px-2 py-0.5 text-xs font-medium"
      style={{ color: tier.colorVar }}
      title={`Credibility score: ${numericScore.toFixed(2)}`}
      aria-label={`${tier.label} credibility`}
    >
      <span aria-hidden="true">●</span>
      {tier.label}
    </span>
  );
}
