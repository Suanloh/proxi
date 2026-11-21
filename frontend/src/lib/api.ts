import "server-only";

function healthUrl(): URL {
  const base = new URL(process.env.PROXI_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1");
  if (!["http:", "https:"].includes(base.protocol) || base.username || base.password || base.search || base.hash) {
    throw new Error("PROXI_API_BASE_URL must be an HTTP(S) base URL without credentials, query, or fragment");
  }
  base.pathname = `${base.pathname.replace(/\/+$/, "")}/health`;
  return base;
}

export async function getApiHealth(): Promise<{ status: "ok" }> {
  const response = await fetch(healthUrl(), {
    cache: "no-store",
    signal: AbortSignal.timeout(3000),
  });
  if (!response.ok) {
    throw new Error(`PROXI health check returned HTTP ${response.status}`);
  }
  const data: unknown = await response.json();
  if (typeof data !== "object" || data === null || !("status" in data) || data.status !== "ok") {
    throw new Error("Unexpected PROXI health response");
  }
  return { status: data.status };
}
