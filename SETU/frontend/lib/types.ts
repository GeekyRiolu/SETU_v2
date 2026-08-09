// Shared shapes for the SETU frontend. These mirror the REST contract in
// SETU/interfaces/rest/app.py - keep field names in lockstep with that file.

/** A language SETU can translate to/from. `endonym` is filled locally. */
export interface Language {
  iso: string;
  name: string;
  flores: string;
  script: string;
  /** Native-script name, e.g. हिन्दी / বাংলা / தமிழ். Attached client-side. */
  endonym?: string;
}

/** Response of POST /translate. */
export interface TranslateResult {
  translated_text: string;
  src_lang: string;
  tgt_lang: string;
  bleu: number | null;
  chrf: number | null;
  latency_ms: number | null;
  /** True when no trained student exists for the pair (passthrough demo). */
  stub: boolean;
  /** Set to "en" when the translation was routed src -> English -> tgt. */
  pivot?: string | null;
}

/** One trained + quantised student on disk, from GET /models. */
export interface ModelInfo {
  pair: string; // "hin_Deva-eng_Latn"
  src_iso: string;
  tgt_iso: string;
  src_name: string;
  tgt_name: string;
  variant: string; // "int4" | "int8" | "onnx"
  size_mb: number | null;
}

/** Connection state of the API, surfaced honestly in the UI. */
export type ApiStatus = "checking" | "online" | "offline";
