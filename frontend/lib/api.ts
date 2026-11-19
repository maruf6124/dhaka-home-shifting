"use client";

export class ApiError extends Error {
  status: number;
  code: string;
  data: Record<string, unknown>;
  constructor(status: number, code: string, message: string, data: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.data = data;
  }
}

function currentLocale(): string {
  if (typeof document === "undefined") return "bn";
  const m = document.cookie.match(/(?:^|; )NEXT_LOCALE=(bn|en)/);
  return m ? m[1] : document.documentElement.lang || "bn";
}

let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (!refreshing) {
    refreshing = fetch("/api/auth/refresh", { method: "POST", credentials: "include" })
      .then((r) => r.ok)
      .catch(() => false)
      .finally(() => setTimeout(() => (refreshing = null), 0));
  }
  return refreshing;
}

type Options = Omit<RequestInit, "body"> & { body?: unknown; retry?: boolean };

/** Calls the FastAPI backend through the /api proxy. Refreshes the login once on 401. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function api<T = any>(path: string, opts: Options = {}): Promise<T> {
  const { body, retry = true, headers, ...rest } = opts;
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  const res = await fetch(`/api${path}`, {
    credentials: "include",
    ...rest,
    headers: {
      "Accept-Language": currentLocale(),
      ...(body !== undefined && !isForm ? { "Content-Type": "application/json" } : {}),
      ...(headers || {}),
    },
    body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
  });
  if (res.status === 401 && retry && !path.startsWith("/auth/")) {
    if (await tryRefresh()) return api<T>(path, { ...opts, retry: false });
  }
  if (!res.ok) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let detail: any = {};
    try {
      detail = (await res.json()).detail ?? {};
    } catch {
      /* not JSON */
    }
    if (typeof detail === "string") detail = { code: "error", message: detail };
    throw new ApiError(res.status, detail.code || "error", detail.message || res.statusText, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

/** Makes images smaller in the browser before upload (max 1600px, WebP). */
export async function compressImage(file: File, maxSide = 1600, quality = 0.82): Promise<File> {
  if (!file.type.startsWith("image/")) return file;
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob: Blob | null = await new Promise((r) => canvas.toBlob(r, "image/webp", quality));
    if (!blob || blob.size >= file.size) return file;
    return new File([blob], file.name.replace(/\.\w+$/, "") + ".webp", { type: "image/webp" });
  } catch {
    return file;
  }
}

export function wsUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_WS_URL;
  if (base) return `${base.replace(/\/$/, "")}${path}`;
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.hostname}:8000${path}`;
}
