const STEPS = [
  {
    title: "Teacher",
    body: "IndicTrans2 translates a large parallel corpus into clean, consistent targets.",
    tag: "billion-param teacher",
  },
  {
    title: "Distil",
    body: "The student learns the teacher's own 1-best translations (sequence-level KD) instead of noisy web references.",
    tag: "Kim & Rush, 2016",
  },
  {
    title: "Student",
    body: "A 52M-parameter Marian seq2seq with a 16k SentencePiece vocab reaches ≈0.8× the teacher's BLEU.",
    tag: "52M params",
  },
  {
    title: "Quantise",
    body: "Export to INT4 ONNX and it fits on the edge: same translations, a twentieth of the teacher's size.",
    tag: "→ ONNX Runtime",
  },
];

export default function HowItWorks() {
  return (
    <section className="how section" id="how">
      <div className="wrap">
        <p className="eyebrow">The method</p>
        <h2 style={{ fontSize: "var(--step-3)", marginTop: "var(--space-md)", maxWidth: "20ch" }}>
          A billion-parameter teacher, distilled into a pocket student.
        </h2>
        <p className="how__lede">
          SETU is not a smaller translator trained from scratch. It is a large
          teacher compressed. The student is taught to reproduce IndicTrans2,
          then quantised until it fits where the network doesn't reach.
        </p>

        <div className="flow" data-parallax data-speed="26">
          {STEPS.map((s, i) => (
            <div className="flow__step" key={s.title}>
              <span className="flow__num">{String(i + 1).padStart(2, "0")}</span>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
              <span className="tag">{s.tag}</span>
            </div>
          ))}
        </div>

        <blockquote className="finding" data-parallax data-speed="18">
          The finding: <b>sequence-level distillation beats preference tuning</b>{" "}
          for compact Indic MT. Reference noise, not the method, was the
          bottleneck.
        </blockquote>
      </div>
    </section>
  );
}
