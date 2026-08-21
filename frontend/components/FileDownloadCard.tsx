import { Download, FileSpreadsheet, FileText } from "lucide-react";

type FileDownloadCardProps = {
  fileName: string;
  fileType: string;
  href: string;
  disabled?: boolean;
};

function iconFor(fileType: string) {
  const normalized = fileType.toLowerCase();
  if (normalized.includes("pdf")) return FileText;
  if (normalized.includes("docx")) return FileText;
  return FileSpreadsheet;
}

export function FileDownloadCard({ fileName, fileType, href, disabled = false }: FileDownloadCardProps) {
  const displayType = fileType.toUpperCase();
  const Icon = iconFor(fileType);

  return (
    <a
      href={disabled ? undefined : href}
      aria-disabled={disabled}
      target={disabled ? undefined : "_blank"}
      rel={disabled ? undefined : "noreferrer"}
      className={`group flex items-center gap-3 rounded-xl border px-3.5 py-3 transition ${
        disabled
          ? "cursor-not-allowed border-[var(--app-border)] bg-[var(--app-panel)]/60"
          : "border-[var(--app-border)] bg-[var(--app-panel)] hover:border-[var(--app-accent)]/50 hover:bg-[var(--app-surface-hover)]"
      }`}
    >
      <span
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
          disabled ? "bg-[var(--app-surface)] text-[var(--app-text-tertiary)]" : "bg-[var(--app-accent-soft)] text-[var(--app-accent)]"
        }`}
      >
        <Icon className="h-4.5 w-4.5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-[var(--app-text-primary)]">{fileName}</span>
        <span className="block text-xs text-[var(--app-text-secondary)]">{displayType} file</span>
      </span>
      {!disabled ? (
        <Download className="h-4 w-4 shrink-0 text-[var(--app-text-tertiary)] transition group-hover:text-[var(--app-accent)]" />
      ) : null}
    </a>
  );
}
