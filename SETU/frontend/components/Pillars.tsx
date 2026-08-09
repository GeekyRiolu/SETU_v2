const ROWS = [
  {
    value: "22",
    unit: "+ English",
    title: "Every scheduled language",
    body: "All 22 constitutionally recognised languages of India, with English as the pivot: Devanagari to Ol Chiki, Perso-Arabic to Meetei.",
  },
  {
    value: "0",
    unit: "network calls",
    title: "Offline by construction",
    body: "ONNX Runtime executes locally and the tokenizer is a file on disk. A socket guard in the engine proves no bytes ever leave.",
  },
  {
    value: "≈104",
    unit: "MB / direction",
    title: "Small enough for the edge",
    body: "An INT4-quantised student, about a quarter of its full-precision size and well under the 200 MB budget, light enough to ship inside an app or run on a phone.",
  },
  {
    value: "<500",
    unit: "ms / sentence",
    title: "Answers in a blink",
    body: "p90 latency stays well under half a second per sentence on commodity CPU, greedy-decoded for deployment.",
  },
];

export default function Pillars() {
  return (
    <section className="section" id="pillars">
      <div className="wrap">
        <p className="eyebrow">The four guarantees</p>
        <h2 style={{ fontSize: "var(--step-3)", marginTop: "var(--space-md)", maxWidth: "18ch" }}>
          What SETU promises, measured.
        </h2>

        <div className="ledger" data-parallax data-speed="22">
          {ROWS.map((r, i) => (
            <div className="ledger__row" key={r.title}>
              <span className="ledger__idx">{String(i + 1).padStart(2, "0")}</span>
              <span className="ledger__value">
                {r.value}
                <span className="unit">{r.unit}</span>
              </span>
              <div className="ledger__body">
                <h3>{r.title}</h3>
                <p>{r.body}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
