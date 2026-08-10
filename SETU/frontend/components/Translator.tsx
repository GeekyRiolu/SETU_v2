"use client";

import { type KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API_BASE, checkHealth, fetchLanguages, fetchModels, translate } from "@/lib/api";
import { FALLBACK_LANGUAGES } from "@/lib/languages";
import type { ApiStatus, Language, ModelInfo, TranslateResult } from "@/lib/types";

const SAMPLE = "भारत एक विशाल देश है, जहाँ अनेक भाषाएँ बोली जाती हैं।";

// Showcase the real bridge: Indic<->Indic (via English pivot) as well as
// Indic<->English, so it never reads as "English only".
const EXAMPLES: [string, string][] = [
  ["hi", "bn"],
  ["ta", "hi"],
  ["mr", "kn"],
  ["bn", "gu"],
  ["te", "ta"],
  ["en", "pa"],
  ["ml", "en"],
];

const STATUS_LABEL: Record<ApiStatus, string> = {
  checking: "Connecting…",
  online: "On-device engine",
  offline: "Engine offline",
};

export default function Translator() {
  const [langs, setLangs] = useState<Language[]>(FALLBACK_LANGUAGES);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [status, setStatus] = useState<ApiStatus>("checking");

  const [src, setSrc] = useState("hi");
  const [tgt, setTgt] = useState("en");
  const [input, setInput] = useState(SAMPLE);

  const [result, setResult] = useState<TranslateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    (async () => {
      const [{ languages, online }, mdls, health] = await Promise.all([
        fetchLanguages(ac.signal),
        fetchModels(ac.signal),
        checkHealth(ac.signal),
      ]);
      setLangs(languages);
      setModels(mdls);
      setStatus(online || health === "online" ? "online" : "offline");
    })();
    return () => ac.abort();
  }, []);

  const byIso = useMemo(() => new Map(langs.map((l) => [l.iso, l])), [langs]);
  const srcLang = byIso.get(src);
  const tgtLang = byIso.get(tgt);

  const pairModel = useMemo(
    () => models.find((m) => m.src_iso === src && m.tgt_iso === tgt) ?? null,
    [models, src, tgt],
  );

  // No direct model, but both src->English and English->tgt exist: pivot works.
  const canPivot = useMemo(() => {
    if (src === "en" || tgt === "en") return false;
    const has = (a: string, b: string) => models.some((m) => m.src_iso === a && m.tgt_iso === b);
    return has(src, "en") && has("en", tgt);
  }, [models, src, tgt]);

  const runTranslate = useCallback(async () => {
    const text = input.trim();
    if (!text || src === tgt || busy) return;
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    setBusy(true);
    setError(null);
    try {
      const res = await translate({ source_lang: src, target_lang: tgt, text }, ac.signal);
      setResult(res);
      if (status !== "online") setStatus("online");
    } catch (err) {
      if (ac.signal.aborted) return;
      const networkish =
        err instanceof TypeError || /failed to fetch|networkerror|load failed/i.test(String(err));
      setError(
        networkish
          ? `Can't reach the SETU engine at ${API_BASE}. Start it with:  uvicorn interfaces.rest.app:app --port 8000`
          : (err as Error).message || "Translation failed.",
      );
      setResult(null);
      if (networkish) setStatus("offline");
    } finally {
      setBusy(false);
    }
  }, [input, src, tgt, busy, status]);

  const swap = useCallback(() => {
    setSrc(tgt);
    setTgt(src);
    setInput(result?.translated_text ?? input);
    setResult(null);
    setError(null);
  }, [src, tgt, input, result]);

  const clear = useCallback(() => {
    setInput("");
    setResult(null);
    setError(null);
  }, []);

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      runTranslate();
    }
  };

  const label = (l: Language) => (l.iso === "en" ? l.name : `${l.endonym} · ${l.name}`);

  return (
    <section className="console-section section" id="translate">
      <div className="wrap">
        <p className="eyebrow">The bridge</p>
        <h2 style={{ fontSize: "var(--step-3)", marginTop: "var(--space-md)", maxWidth: "16ch" }}>
          Translate, on your own machine.
        </h2>

        <div className="console" style={{ marginTop: "var(--space-2xl)" }}>
          <div className="console__bar">
            <span className="console__title">Translator</span>
            <span className={`status status--${status}`}>
              <span className="status__dot" />
              {STATUS_LABEL[status]}
            </span>
          </div>

          <div className="console__body">
            <div className="panel">
              <div className="panel__head">
                <span className="panel__label">From</span>
                <div className="lang-select">
                  <select
                    aria-label="Source language"
                    value={src}
                    onChange={(e) => {
                      const v = e.target.value;
                      if (v === tgt) setTgt(src);
                      setSrc(v);
                      setResult(null);
                    }}
                  >
                    {langs.map((l) => (
                      <option key={l.iso} value={l.iso}>
                        {label(l)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <textarea
                className="field indic"
                lang={src}
                value={input}
                placeholder={`Type or paste ${srcLang?.name ?? "text"}…`}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                aria-label="Text to translate"
              />
              <div className="panel__foot">
                <span>{input.trim().length} characters</span>
                <span>⌘⏎ to translate</span>
              </div>
            </div>

            <button
              type="button"
              className="swap"
              onClick={swap}
              aria-label="Swap languages"
              title="Swap languages"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M7 4L3 8l4 4M3 8h13M17 20l4-4-4-4M21 16H8"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>

            <div className="panel panel--out">
              <div className="panel__head">
                <span className="panel__label">To</span>
                <div className="lang-select">
                  <select
                    aria-label="Target language"
                    value={tgt}
                    onChange={(e) => {
                      const v = e.target.value;
                      if (v === src) setSrc(tgt);
                      setTgt(v);
                      setResult(null);
                    }}
                  >
                    {langs.map((l) => (
                      <option key={l.iso} value={l.iso}>
                        {label(l)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="output indic" lang={tgt} aria-live="polite">
                {error ? (
                  <span className="output--error">{error}</span>
                ) : result ? (
                  <span className="out-anim">{result.translated_text}</span>
                ) : (
                  <span className="output--empty">
                    Your translation appears here.
                    <span className="hint">
                      {pairModel
                        ? `A trained ${pairModel.variant.toUpperCase()} model is ready for this pair.`
                        : canPivot
                          ? "No direct model, so this routes through English (two hops)."
                          : "No trained model for this pair yet, so output will pass through."}
                    </span>
                  </span>
                )}
              </div>

              <div className="panel__foot">
                {result && !error ? (
                  <>
                    <span className="tele">
                      <strong>{Math.round(result.latency_ms ?? 0)}</strong>&nbsp;ms
                      {result.pivot ? (
                        <>{" · via English"}</>
                      ) : pairModel?.size_mb ? (
                        <>
                          {" · "}
                          {pairModel.variant.toUpperCase()} · {pairModel.size_mb} MB
                        </>
                      ) : null}
                    </span>
                    {result.stub ? (
                      <span className="pill pill--demo">demo · passthrough</span>
                    ) : (
                      <span className="pill pill--device">
                        <span className="dot" />
                        on-device
                      </span>
                    )}
                  </>
                ) : (
                  <span />
                )}
              </div>
            </div>
          </div>

          <div className="console__actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={runTranslate}
              disabled={busy || !input.trim() || src === tgt}
            >
              {busy ? "Translating…" : "Translate"}
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={clear}
              disabled={!input && !result}
            >
              Clear
            </button>
            <span className="grow" />
            <span className="tele" style={{ color: "var(--ink-3)" }}>
              {srcLang?.name} → {tgtLang?.name}
            </span>
          </div>
        </div>

        <div className="quickpicks">
          <span className="quickpicks__label">Try:</span>
          {EXAMPLES.map(([s, t]) => (
            <button
              type="button"
              key={`${s}-${t}`}
              className="chip"
              onClick={() => {
                setSrc(s);
                setTgt(t);
                setResult(null);
                setError(null);
              }}
            >
              <span className="indic" lang={s}>
                {byIso.get(s)?.endonym ?? s}
              </span>
              <span className="arrow">→</span>
              <span className="indic" lang={t}>
                {byIso.get(t)?.endonym ?? t}
              </span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
