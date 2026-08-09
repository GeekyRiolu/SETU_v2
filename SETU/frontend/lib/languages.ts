import type { Language } from "./types";

/** Native-script endonyms, keyed by ISO code - the signature visual of SETU.
 *  We name each language in its own writing system, not in English. */
export const ENDONYMS: Record<string, string> = {
  en: "English",
  as: "অসমীয়া",
  bn: "বাংলা",
  brx: "बड़ो",
  doi: "डोगरी",
  gu: "ગુજરાતી",
  hi: "हिन्दी",
  kn: "ಕನ್ನಡ",
  ks: "کٲشُر",
  gom: "कोंकणी",
  mai: "मैथिली",
  ml: "മലയാളം",
  mni: "মণিপুরী",
  mr: "मराठी",
  ne: "नेपाली",
  or: "ଓଡ଼ିଆ",
  pa: "ਪੰਜਾਬੀ",
  sa: "संस्कृतम्",
  sat: "ᱥᱟᱱᱛᱟᱲᱤ",
  sd: "سنڌي",
  ta: "தமிழ்",
  te: "తెలుగు",
  ur: "اردو",
};

/** Bundled registry - mirrors SETU/configs/languages.yaml. Used when the API's
 *  GET /languages is unreachable, so the picker still works fully offline. */
export const FALLBACK_LANGUAGES: Language[] = [
  { iso: "en", name: "English", flores: "eng_Latn", script: "Latin" },
  { iso: "as", name: "Assamese", flores: "asm_Beng", script: "Bengali" },
  { iso: "bn", name: "Bengali", flores: "ben_Beng", script: "Bengali" },
  { iso: "brx", name: "Bodo", flores: "brx_Deva", script: "Devanagari" },
  { iso: "doi", name: "Dogri", flores: "doi_Deva", script: "Devanagari" },
  { iso: "gu", name: "Gujarati", flores: "guj_Gujr", script: "Gujarati" },
  { iso: "hi", name: "Hindi", flores: "hin_Deva", script: "Devanagari" },
  { iso: "kn", name: "Kannada", flores: "kan_Knda", script: "Kannada" },
  { iso: "ks", name: "Kashmiri", flores: "kas_Arab", script: "Perso-Arabic" },
  { iso: "gom", name: "Konkani", flores: "gom_Deva", script: "Devanagari" },
  { iso: "mai", name: "Maithili", flores: "mai_Deva", script: "Devanagari" },
  { iso: "ml", name: "Malayalam", flores: "mal_Mlym", script: "Malayalam" },
  { iso: "mni", name: "Manipuri", flores: "mni_Beng", script: "Bengali" },
  { iso: "mr", name: "Marathi", flores: "mar_Deva", script: "Devanagari" },
  { iso: "ne", name: "Nepali", flores: "npi_Deva", script: "Devanagari" },
  { iso: "or", name: "Odia", flores: "ory_Orya", script: "Odia" },
  { iso: "pa", name: "Punjabi", flores: "pan_Guru", script: "Gurmukhi" },
  { iso: "sa", name: "Sanskrit", flores: "san_Deva", script: "Devanagari" },
  { iso: "sat", name: "Santali", flores: "sat_Olck", script: "Ol Chiki" },
  { iso: "sd", name: "Sindhi", flores: "snd_Arab", script: "Perso-Arabic" },
  { iso: "ta", name: "Tamil", flores: "tam_Taml", script: "Tamil" },
  { iso: "te", name: "Telugu", flores: "tel_Telu", script: "Telugu" },
  { iso: "ur", name: "Urdu", flores: "urd_Arab", script: "Perso-Arabic" },
].map((l) => ({ ...l, endonym: ENDONYMS[l.iso] ?? l.name }));

/** Attach endonyms to languages returned by the API's /languages endpoint. */
export function withEndonyms(langs: Language[]): Language[] {
  return langs.map((l) => ({ ...l, endonym: ENDONYMS[l.iso] ?? l.name }));
}

/** "setu" = bridge. The word for bridge across writing systems - the hero wall. */
export const BRIDGE_IN_SCRIPTS: { script: string; word: string }[] = [
  { script: "Devanagari", word: "सेतु" },
  { script: "Bengali", word: "সেতু" },
  { script: "Tamil", word: "பாலம்" },
  { script: "Telugu", word: "వంతెన" },
  { script: "Kannada", word: "ಸೇತುವೆ" },
  { script: "Malayalam", word: "പാലം" },
  { script: "Gujarati", word: "સેતુ" },
  { script: "Gurmukhi", word: "ਪੁਲ" },
  { script: "Odia", word: "ସେତୁ" },
  { script: "Perso-Arabic", word: "پُل" },
  { script: "Ol Chiki", word: "ᱥᱮᱛᱩ" },
];
