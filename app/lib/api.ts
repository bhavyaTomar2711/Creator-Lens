import type { IngestResponse, Source, Video } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getSession(sessionId: string): Promise<{ video_a: Video; video_b: Video }> {
  const res = await fetch(`${API}/session/${sessionId}`);
  if (!res.ok) throw new Error(`Session not found (${res.status})`);
  return res.json();
}

export async function ingestPair(urlA: string, urlB: string): Promise<IngestResponse> {
  const res = await fetch(`${API}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url_a: urlA, url_b: urlB }),
  });
  if (!res.ok) throw new Error((await res.text()) || `Ingest failed (${res.status})`);
  return res.json();
}

export interface StreamHandlers {
  onSources?: (s: Source[]) => void;
  onToken?: (t: string) => void;
  onDone?: (answer: string, sources: Source[]) => void;
  onError?: (e: Error) => void;
}

/**
 * Streams /chat over SSE. We use fetch (not EventSource) because the endpoint is POST.
 * Parses the SSE wire format manually, preserving a token's own leading spaces
 * (strip the "data:" prefix and at most ONE separator space — matches EventSource).
 */
export async function streamChat(
  sessionId: string,
  message: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  try {
    const res = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
      signal,
    });
    if (!res.ok || !res.body) throw new Error(`Chat failed (${res.status})`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      // sse_starlette uses CRLF; normalize so the \n\n event split works in the browser.
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n?/g, "\n");

      // events are separated by a blank line
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const raw = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        dispatch(raw, handlers);
      }
    }
  } catch (e) {
    if ((e as Error).name !== "AbortError") handlers.onError?.(e as Error);
  }
}

function dispatch(raw: string, h: StreamHandlers) {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      let d = line.slice(5);
      if (d.startsWith(" ")) d = d.slice(1); // strip ONE separator space, keep token spaces
      dataLines.push(d);
    }
  }
  const data = dataLines.join("\n");

  if (event === "token") h.onToken?.(data);
  else if (event === "sources") h.onSources?.(safeParse(data) ?? []);
  else if (event === "done") {
    const parsed = safeParse(data) ?? {};
    h.onDone?.(parsed.answer ?? "", parsed.sources ?? []);
  }
}

function safeParse(s: string): any {
  try {
    return JSON.parse(s);
  } catch {
    return null;
  }
}
