const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export const runtime = "nodejs";

export async function GET(
  _request: Request,
  { params }: { params: { fileName: string } },
) {
  const fileName = params.fileName;
  if (!/^[A-Za-z0-9._-]+$/.test(fileName)) {
    return new Response("Invalid file name", { status: 400 });
  }

  const upstream = await fetch(`${BACKEND_URL}/files/${encodeURIComponent(fileName)}`, {
    cache: "no-store",
  });

  const headers = new Headers();
  headers.set("Content-Type", upstream.headers.get("Content-Type") ?? "application/octet-stream");
  headers.set(
    "Content-Disposition",
    upstream.headers.get("Content-Disposition") ?? `attachment; filename="${fileName}"`,
  );

  return new Response(upstream.body, {
    status: upstream.status,
    headers,
  });
}
