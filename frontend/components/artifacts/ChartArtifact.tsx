"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CredibilityBadge } from "@/components/CredibilityBadge";
import { stripMarkdown } from "@/lib/text";

type ChartDatum = Record<string, string | number | null | undefined>;
const APP_ACCENT_FALLBACK = "#d97757"; // Mirrors globals.css --app-accent for SVG props before CSS variables resolve.
const TEXT_SECONDARY_FALLBACK = "#a8a196"; // Mirrors globals.css --app-text-secondary for SVG tick props.

function useCssToken(name: string, fallback: string) {
  const [value, setValue] = useState(fallback);

  useEffect(() => {
    const token = window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    if (token) {
      setValue(token);
    }
  }, [name]);

  return value;
}

function chooseValueKey(data: ChartDatum[]) {
  return data.some((item) => typeof item.value === "number") ? "value" : "credibility";
}

function chooseLabelKey(data: ChartDatum[]) {
  if (data.some((item) => item.date || item.year)) {
    return data.some((item) => item.date) ? "date" : "year";
  }
  if (data.some((item) => item.label)) {
    return "label";
  }
  return "name";
}

function hasYearLikeLabels(data: ChartDatum[]) {
  return data.length > 0 && data.every((item) => /^\d{4}$/.test(String(item.label ?? "")));
}

function alphanumericRatio(text: string) {
  if (!text.length) {
    return 0;
  }
  const alphanumericCount = (text.match(/[a-z0-9]/gi) || []).length;
  return alphanumericCount / text.length;
}

function summarizeFindingText(value: unknown, fallbackTitle: unknown) {
  const text = stripMarkdown(String(value || "Source").replace(/\s+/g, " ").trim());
  const firstSentence = text.match(/^.*?[.!?](?:\s|$)/)?.[0]?.trim() || text;
  if (alphanumericRatio(firstSentence) < 0.5) {
    return stripMarkdown(String(fallbackTitle || "Source").replace(/\s+/g, " ").trim());
  }
  const summary = firstSentence.length <= 150 ? firstSentence : text.slice(0, 150).trim();
  return summary.length < text.length ? `${summary}...` : summary;
}

function ChartTooltip({ active, payload, valueKey }: any) {
  if (!active || !payload?.length) {
    return null;
  }

  const item = payload[0].payload as ChartDatum;
  const text = item.findingText || item.snippet || item.title || item.label || item.name || "Source";
  const credibility = typeof item.credibility === "number" ? item.credibility : Number(item.credibility);

  return (
    <div className="max-w-[18rem] rounded-md border border-[var(--app-border)] bg-[var(--app-panel)] p-3 text-xs leading-5 text-[var(--app-text-primary)]">
      <p className="whitespace-normal">{summarizeFindingText(text, item.title || item.name || item.label)}</p>
      {Number.isFinite(credibility) ? (
        <div className="mt-2">
          <CredibilityBadge score={credibility} />
        </div>
      ) : null}
      {valueKey !== "credibility" ? (
        <p className="mt-2 text-[var(--app-text-secondary)]">Value: {String(payload[0].value)}</p>
      ) : null}
    </div>
  );
}

export function ChartArtifact({ data }: { data: ChartDatum[] }) {
  const accentColor = useCssToken("--app-accent", APP_ACCENT_FALLBACK);
  const axisColor = useCssToken("--app-text-secondary", TEXT_SECONDARY_FALLBACK);
  const valueKey = useMemo(() => chooseValueKey(data), [data]);
  const labelKey = useMemo(() => chooseLabelKey(data), [data]);
  const isTimeSeries = labelKey === "date" || labelKey === "year" || hasYearLikeLabels(data);

  if (!data.length) {
    return <p className="mt-3 text-sm text-[var(--app-text-secondary)]">No chart data returned.</p>;
  }

  return (
    <div className="mt-4 rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] p-4">
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        {isTimeSeries ? (
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 32, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--app-border)" />
            <XAxis dataKey={labelKey} interval={0} tick={{ fontSize: 12, fill: axisColor }} />
            <YAxis domain={valueKey === "credibility" ? [0, 1] : undefined} tick={{ fontSize: 12, fill: axisColor }} />
            <Tooltip content={<ChartTooltip valueKey={valueKey} />} />
            <Line type="monotone" dataKey={valueKey} stroke={accentColor} strokeWidth={2} dot={{ r: 3, fill: accentColor }} />
          </LineChart>
        ) : (
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 32, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--app-border)" />
            <XAxis dataKey={labelKey} interval={0} tick={{ fontSize: 12, fill: axisColor }} />
            <YAxis domain={valueKey === "credibility" ? [0, 1] : undefined} tick={{ fontSize: 12, fill: axisColor }} />
            <Tooltip content={<ChartTooltip valueKey={valueKey} />} />
            <Bar dataKey={valueKey} fill={accentColor} radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
    </div>
  );
}
