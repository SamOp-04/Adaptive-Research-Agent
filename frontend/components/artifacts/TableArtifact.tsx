"use client";

import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { useMemo } from "react";

import { CredibilityBadge } from "@/components/CredibilityBadge";


type TableRow = Record<string, string | number | null | undefined>;
const MAX_ROWS = 12;

function formatHeader(key: string) {
  return key.replace(/_/g, " ");
}

function displayDomain(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function TableArtifact({
  rows,
  columns,
}: {
  rows: TableRow[];
  columns?: string[];
}) {
  const keys = columns?.length ? columns : Object.keys(rows[0] ?? {});
  const orderedKeys = useMemo(() => {
    const preferred = ["title", "credibility", "url"];
    return [
      ...preferred.filter((key) => keys.includes(key)),
      ...keys.filter((key) => !preferred.includes(key)),
    ];
  }, [keys]);
  const visibleRows = useMemo(() => rows.slice(0, MAX_ROWS), [rows]);
  const hiddenRowCount = Math.max(0, rows.length - MAX_ROWS);
  const columnDefs = useMemo<ColumnDef<TableRow>[]>(
    () =>
      orderedKeys.map((key) => ({
        accessorKey: key,
        header: formatHeader(key),
        cell: (info) => {
          const value = info.getValue();
          if (key === "credibility") {
            const score = typeof value === "number" ? value : Number(value);
            return <CredibilityBadge score={Number.isFinite(score) ? score : undefined} />;
          }
          if (key === "url" && typeof value === "string") {
            const domain = displayDomain(value);
            return (
              <a
                className="text-[var(--app-accent)] underline underline-offset-2 transition hover:text-[var(--app-accent-hover)]"
                href={value}
                title={value}
                target="_blank"
                rel="noreferrer"
              >
                {domain}
              </a>
            );
          }
          return String(value ?? "");
        },
      })),
    [orderedKeys],
  );

  const table = useReactTable({
    data: visibleRows,
    columns: columnDefs,
    getCoreRowModel: getCoreRowModel(),
  });

  if (!rows.length) {
    return <p className="mt-3 text-sm text-[var(--app-text-secondary)]">No table rows returned.</p>;
  }

  return (
    <div className="mt-4 overflow-x-auto rounded-md border border-[var(--app-border)]">
      <table className="min-w-full text-left text-sm">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className="border-b border-[var(--app-border)]">
              {headerGroup.headers.map((header) => (
                <th key={header.id} className="px-3 py-2 text-xs font-medium capitalize text-[var(--app-text-secondary)]">
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="border-b border-[var(--app-border)] last:border-b-0">
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="max-w-xs px-3 py-2 align-top text-[var(--app-text-primary)]">
                  <div className="break-words">{flexRender(cell.column.columnDef.cell, cell.getContext())}</div>
                </td>
              ))}
            </tr>
          ))}
          {hiddenRowCount ? (
            <tr>
              <td
                colSpan={orderedKeys.length}
                className="px-3 py-2 text-sm text-[var(--app-text-secondary)]"
              >
                +{hiddenRowCount} more sources
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
