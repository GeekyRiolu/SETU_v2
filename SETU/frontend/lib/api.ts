import type { ApiStatus, Language, ModelInfo, TranslateResult } from "./types";
import { FALLBACK_LANGUAGES, withEndonyms } from "./languages";

/** Base URL of the SETU REST API. Configurable; defaults to the local server. */
export const API_BASE = (
  process.env.NEXT_PUBLIC_SETU_API ?? "http://localhost:8000"
).replace(/\/+$/, "");

async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* error body wasn't JSON - keep the status line */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

/** All languages SETU knows. Falls back to the bundled list when offline so the
 *  picker never comes up empty. `online` tells the UI which source was used. */
export async function fetchLanguages(
  signal?: AbortSignal,
): Promise<{ languages: Language[]; online: boolean }> {
  try {
    const data = await getJSON<{ languages: Language[] }>("/languages", { signal });
    return { languages: withEndonyms(data.languages), online: true };
  } catch {
    return { languages: FALLBACK_LANGUAGES, online: false };
  }
}

/** Pairs that actually have a trained + quantised student on disk. */
export async function fetchModels(signal?: AbortSignal): Promise<ModelInfo[]> {
  try {
    const data = await getJSON<{ models: ModelInfo[] }>("/models", { signal });
    return data.models ?? [];
  } catch {
    return [];
  }
}

export async function checkHealth(signal?: AbortSignal): Promise<ApiStatus> {
  try {
    await getJSON<{ status: string }>("/health", { signal });
    return "online";
  } catch {
    return "offline";
  }
}

export async function translate(
  req: { source_lang: string; target_lang: string; text: string },
  signal?: AbortSignal,
): Promise<TranslateResult> {
  return getJSON<TranslateResult>("/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });
}
