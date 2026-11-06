import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
// Matches Vercel's Hobby maximum; proxied chat calls can be slow with a local
// Ollama model and must not be cut off early.
export const maxDuration = 300;

const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8000").replace(
  /\/+$/,
  ""
);

const FORWARDED_REQUEST_HEADERS = ["content-type", "accept"];

async function handle(
  req: NextRequest,
  { params }: { params: { path?: string[] } }
) {
  const path = (params.path ?? []).join("/");
  const target = `${BACKEND_URL}/${path}${req.nextUrl.search}`;

  const headers = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = req.headers.get(name);
    if (value) headers.set(name, value);
  }

  const hasBody = !["GET", "HEAD"].includes(req.method);

  try {
    const upstream = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? await req.arrayBuffer() : undefined,
      cache: "no-store",
      redirect: "manual",
    });

    const responseHeaders = new Headers();
    const contentType = upstream.headers.get("content-type");
    if (contentType) responseHeaders.set("content-type", contentType);
    responseHeaders.set("cache-control", "no-store");

    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (err: any) {
    // Surface a useful message instead of a bare 500. The chat/upload pages
    // and the health banner show this text directly.
    const detail =
      `Backend unreachable at ${BACKEND_URL} (${err?.message || "network error"}). ` +
      "On Vercel, the FastAPI service should be injected as BACKEND_URL by the " +
      "service binding in vercel.json; locally, start it with `python run_backend.py`.";
    return Response.json({ detail }, { status: 502 });
  }
}

export {
  handle as GET,
  handle as POST,
  handle as PUT,
  handle as PATCH,
  handle as DELETE,
};
