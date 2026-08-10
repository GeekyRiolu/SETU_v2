import BridgeWord from "@/components/BridgeWord";

// "setu" means bridge. The word for bridge across writing systems is the motif.
const WALL = [
  { word: "सेतु", script: "Devanagari", mark: true },
  { word: "সেতু", script: "Bengali", mark: false },
  { word: "பாலம்", script: "Tamil", mark: false },
  { word: "వంతెన", script: "Telugu", mark: false },
  { word: "ಸೇತುವೆ", script: "Kannada", mark: false },
  { word: "پُل", script: "Perso-Arabic", mark: false },
];

export default function Hero() {
  return (
    <section className="hero">
      <div className="wrap hero__grid">
        <div>
          <p className="eyebrow hero__kicker reveal reveal-1">
            <span>
              <BridgeWord start={1} /> · a translation commons
            </span>
          </p>
          <h1 className="reveal reveal-2">
            One bridge.
            <br />
            Twenty-two languages.
            <br />
            <span className="rule mark">Zero network.</span>
          </h1>
          <p className="lede hero__lede reveal reveal-3">
            SETU translates between the 22 scheduled languages of India and
            English entirely on your device. It is a student distilled from
            IndicTrans2, small enough to carry. No servers, no accounts, nothing
            leaves your machine.
          </p>
          <div className="hero__cta reveal reveal-3">
            <a className="btn btn--primary" href="#translate">
              Open the translator
            </a>
            <a className="btn btn--ghost" href="#how">
              Read the method
            </a>
          </div>
          <dl className="hero__meta reveal reveal-4">
            <div>
              <b>≈104 MB</b> per direction, on disk
            </div>
            <div>
              <b>&lt;500 ms</b> a sentence, on CPU
            </div>
            <div>
              <b>0</b> network calls
            </div>
          </dl>
        </div>

        <div className="wall" data-parallax data-speed="52" aria-hidden="true">
          {WALL.map((c) => (
            <div
              key={c.script}
              className={`wall__cell${c.mark ? " wall__cell--mark" : ""}`}
            >
              <span className="wall__word">{c.word}</span>
              <span className="wall__script">{c.script}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
