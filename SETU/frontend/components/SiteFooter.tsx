import BridgeWord from "@/components/BridgeWord";

const REPO = "https://github.com/GeekyRiolu/SETU_v2";

export default function SiteFooter() {
  return (
    <footer className="foot">
      <div className="wrap">
        <div className="foot__grid">
          <div className="foot__brand">
            <a href="#top" className="wordmark" aria-label="SETU home">
              <span>
                SE<b>TU</b>
              </span>
              <BridgeWord className="deva" start={2} />
            </a>
            <p className="foot__tag">
              A bridge across the twenty-two languages of India, built to work
              where the network doesn't.
            </p>
          </div>

          <div className="foot__col">
            <h4>Project</h4>
            <ul>
              <li>
                <a href={REPO}>Source on GitHub</a>
              </li>
              <li>
                <a href="#how">The method</a>
              </li>
              <li>
                <a href="/app">Offline PWA</a>
              </li>
              <li>
                <a href="#pillars">Guarantees</a>
              </li>
            </ul>
          </div>

          <div className="foot__col">
            <h4>Languages</h4>
            <ul>
              <li>
                <span className="indic" lang="hi">
                  हिन्दी
                </span>{" "}
                · Hindi
              </li>
              <li>
                <span className="indic" lang="ta">
                  தமிழ்
                </span>{" "}
                · Tamil
              </li>
              <li>
                <span className="indic" lang="bn">
                  বাংলা
                </span>{" "}
                · Bengali
              </li>
              <li>
                <a href="#languages">…and 19 more</a>
              </li>
            </ul>
          </div>
        </div>

        <div className="foot__bar">
          <span>Built offline-first · no trackers · nothing to log</span>
          <span className="indic">
            <BridgeWord start={3} /> · a bridge
          </span>
        </div>
      </div>
    </footer>
  );
}
