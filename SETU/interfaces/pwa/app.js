// SETU PWA — thin client over the shared REST engine (POST /translate).
// No translation logic here; the same InferenceEngine backs every interface.

const API = location.origin; // REST API served on the same origin
const $ = (id) => document.getElementById(id);

// Fallback language list so the picker works even before the first /languages
// fetch (offline first launch). Kept small; refreshed from the API when online.
const FALLBACK_LANGS = [
  { iso: "hi", name: "Hindi" }, { iso: "en", name: "English" },
  { iso: "bn", name: "Bengali" }, { iso: "ta", name: "Tamil" },
  { iso: "te", name: "Telugu" }, { iso: "mr", name: "Marathi" },
  { iso: "gu", name: "Gujarati" }, { iso: "kn", name: "Kannada" },
];

function fillLangs(langs) {
  const src = $("src"), tgt = $("tgt");
  src.innerHTML = tgt.innerHTML = "";
  for (const l of langs) {
    src.add(new Option(l.name, l.iso));
    tgt.add(new Option(l.name, l.iso));
  }
  src.value = "hi";
  tgt.value = "en";
}

async function loadLanguages() {
  try {
    const r = await fetch(`${API}/languages`, { cache: "no-store" });
    const body = await r.json();
    localStorage.setItem("setu_langs", JSON.stringify(body.languages));
    fillLangs(body.languages);
  } catch {
    const cached = localStorage.getItem("setu_langs");
    fillLangs(cached ? JSON.parse(cached) : FALLBACK_LANGS);
  }
}

async function translate() {
  const text = $("input").value.trim();
  if (!text) return;
  $("go").disabled = true;
  $("output").textContent = "…";
  $("meta").textContent = "";
  try {
    const r = await fetch(`${API}/translate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_lang: $("src").value,
        target_lang: $("tgt").value,
        text,
      }),
    });
    const body = await r.json();
    if (!r.ok) throw new Error(body.detail || "translation failed");
    $("output").textContent = body.translated_text;
    const bits = [];
    if (body.latency_ms != null) bits.push(`${body.latency_ms.toFixed(0)} ms`);
    if (body.stub) bits.push("stub engine (no trained model yet)");
    $("meta").textContent = bits.join(" · ");
  } catch (e) {
    $("output").textContent = `⚠ ${e.message}. The local SETU server must be running.`;
  } finally {
    $("go").disabled = false;
  }
}

function updateConn() {
  const el = $("conn");
  if (navigator.onLine) {
    el.textContent = "online";
    el.classList.remove("offline");
  } else {
    el.textContent = "offline · cached";
    el.classList.add("offline");
  }
}

$("go").addEventListener("click", translate);
$("swap").addEventListener("click", () => {
  const s = $("src").value;
  $("src").value = $("tgt").value;
  $("tgt").value = s;
});
window.addEventListener("online", updateConn);
window.addEventListener("offline", updateConn);

updateConn();
loadLanguages();

// register the service worker so the app shell is cached for offline use
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("service-worker.js").catch(() => {});
}
