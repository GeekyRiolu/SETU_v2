import { FALLBACK_LANGUAGES } from "@/lib/languages";

// The 22 scheduled languages (English is the pivot, shown in the console).
const LANGS = FALLBACK_LANGUAGES.filter((l) => l.iso !== "en");
const HALF = Math.ceil(LANGS.length / 2);
const ROW_A = LANGS.slice(0, HALF);
const ROW_B = LANGS.slice(HALF);

function Card({ iso, endonym, name }: { iso: string; endonym?: string; name: string }) {
  return (
    <div className="lang-card">
      <span className="lang-card__native indic" lang={iso}>
        {endonym ?? name}
      </span>
      <span className="lang-card__roman">{name}</span>
    </div>
  );
}

function Row({ items, reverse }: { items: typeof LANGS; reverse?: boolean }) {
  // rendered twice so the -50% translate loops seamlessly
  const doubled = [...items, ...items];
  return (
    <div className={`marquee__row${reverse ? " marquee__row--rev" : ""}`}>
      {doubled.map((l, i) => (
        <Card key={`${l.iso}-${i}`} iso={l.iso} endonym={l.endonym} name={l.name} />
      ))}
    </div>
  );
}

export default function LanguageStrip() {
  return (
    <section className="strip" id="languages" aria-label="Supported languages">
      <div className="wrap strip__head" data-parallax data-speed="26">
        <div>
          <p className="eyebrow">Every scheduled language</p>
          <h2 style={{ fontSize: "var(--step-2)", marginTop: "var(--space-sm)" }}>
            Named in its own script, not in English.
          </h2>
        </div>
        <p className="strip__count">
          22<span style={{ color: "var(--ink-3)", fontWeight: 500 }}> + English</span>
        </p>
      </div>
      <div className="marquee">
        <Row items={ROW_A} />
        <Row items={ROW_B} reverse />
      </div>
    </section>
  );
}
