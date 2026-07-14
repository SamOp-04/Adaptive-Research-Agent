type FileDownloadCardProps = {
  fileName: string;
  fileType: string;
  href: string;
  disabled?: boolean;
};


export function FileDownloadCard({ fileName, fileType, href, disabled = false }: FileDownloadCardProps) {
  return (
    <section className="rounded-lg border border-[var(--app-border)] bg-white p-4">
      <p className="text-sm font-semibold text-zinc-950">File output</p>
      <p className="mt-2 text-sm text-zinc-600">{fileName}</p>
      <a
        href={disabled ? undefined : href}
        aria-disabled={disabled}
        className={`mt-3 inline-flex rounded-md px-3 py-2 text-sm font-medium ${
          disabled
            ? "cursor-not-allowed bg-zinc-100 text-zinc-400"
            : "bg-zinc-950 text-white hover:bg-zinc-800"
        }`}
      >
        Download {fileType}
      </a>
    </section>
  );
}
