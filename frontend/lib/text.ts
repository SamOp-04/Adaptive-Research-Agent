/**
 * Strips literal markdown control characters from text that will be rendered
 * as plain text (table cells, chart tooltips, etc.) rather than through the
 * markdown renderer, so `**bold**` / `*italic*` / `` `code` `` don't leak
 * through as raw asterisks/backticks in the UI.
 */
export function stripMarkdown(value: string): string {
  if (!value) return value;
  return value
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/\*([^*\s][^*]*)\*/g, "$1")
    .replace(/_([^_\s][^_]*)_/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .trim();
}
