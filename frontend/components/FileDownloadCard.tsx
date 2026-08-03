type FileDownloadCardProps = {
  fileName: string;
  fileType: string;
  href: string;
  disabled?: boolean;
};


export function FileDownloadCard({ fileName, fileType, href, disabled = false }: FileDownloadCardProps) {
  const displayType = fileType.toUpperCase();

  return (
    <section className="rounded-md border border-[var(--app-border)] bg-[var(--app-panel)] p-4">
      <p className="text-sm font-semibold text-[var(--app-text-primary)]">File output</p>
      <p className="mt-2 break-words text-sm text-[var(--app-text-secondary)]">{fileName}</p>
      <a
        href={disabled ? undefined : href}
        aria-disabled={disabled}
        className={`mt-3 inline-flex rounded-md px-3 py-2 text-sm font-medium transition ${
          disabled
            ? "cursor-not-allowed bg-[var(--app-border)] text-[var(--app-text-secondary)]"
            : "bg-[var(--app-accent)] text-[var(--app-bg)] hover:bg-[var(--app-accent-hover)]"
        }`}
      >
        Download {displayType}
      </a>
    </section>
  );
}
