"use client";

import { useState } from "react";
import ThemeToggle from "@/components/ThemeToggle";

const LINKS = [
  { href: "#translate", label: "Translate" },
  { href: "#languages", label: "Languages" },
  { href: "#how", label: "The method" },
  { href: "#pillars", label: "Guarantees" },
];

export default function SiteHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="masthead">
      <div className="wrap masthead__row">
        <a href="#top" className="wordmark" aria-label="SETU home">
          <span>
            SE<b>TU</b>
          </span>
          <span className="deva" aria-hidden="true">
            सेतु
          </span>
        </a>

        <div className="masthead__right">
          <nav className="nav" data-open={open} onClick={() => setOpen(false)}>
            {LINKS.map((l) => (
              <a key={l.href} className="nav__link" href={l.href}>
                {l.label}
              </a>
            ))}
            <a className="btn btn--primary" href="#translate">
              Open translator
            </a>
          </nav>

          <ThemeToggle />

          <button
            type="button"
            className="nav-toggle"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            <span />
          </button>
        </div>
      </div>
    </header>
  );
}
