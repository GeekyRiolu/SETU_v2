"use client";

import { useEffect } from "react";

// Background parallax tapestry: the word for "bridge" across Indic scripts,
// placed down the page at several depths. Each word moves vertically at its own
// rate (depth) as you scroll, drifts sideways, and holds a slight tilt — near
// layers race, far layers linger, so the field reads with real depth.
// (The earlier curvy-line version is kept commented at the bottom.)
type Word = {
  t: string;
  lang: string;
  top: number;
  left: number;
  size: number; // vw
  depth: number; // vertical parallax factor: higher = slower = further back
  drift: number; // horizontal factor
  rot: number; // degrees
  accent?: boolean;
};

const WORDS: Word[] = [
  { t: "सेतु", lang: "hi", top: 2, left: -3, size: 16, depth: 0.55, drift: 0.05, rot: -4, accent: true },
  { t: "সেতু", lang: "bn", top: 11, left: 60, size: 12, depth: 0.22, drift: -0.06, rot: 3 },
  { t: "பாலம்", lang: "ta", top: 20, left: 6, size: 10, depth: 0.42, drift: 0.03, rot: -2 },
  { t: "వంతెన", lang: "te", top: 28, left: 54, size: 13, depth: 0.14, drift: -0.03, rot: 4, accent: true },
  { t: "ಸೇತುವೆ", lang: "kn", top: 37, left: -4, size: 11, depth: 0.5, drift: 0.06, rot: 2 },
  { t: "പാലം", lang: "ml", top: 45, left: 58, size: 13, depth: 0.3, drift: -0.05, rot: -3 },
  { t: "ਪੁਲ", lang: "pa", top: 54, left: 10, size: 15, depth: 0.18, drift: 0.03, rot: 2 },
  { t: "સેતુ", lang: "gu", top: 62, left: 56, size: 11, depth: 0.46, drift: -0.06, rot: -4, accent: true },
  { t: "ସେତୁ", lang: "or", top: 70, left: 3, size: 12, depth: 0.26, drift: 0.05, rot: 3 },
  { t: "پُل", lang: "ur", top: 79, left: 58, size: 14, depth: 0.5, drift: -0.04, rot: -2 },
  { t: "ᱥᱮᱛᱩ", lang: "sat", top: 87, left: 7, size: 10, depth: 0.34, drift: 0.06, rot: 3 },
  { t: "सेतु", lang: "mr", top: 95, left: 54, size: 12, depth: 0.2, drift: -0.05, rot: -3 },
];

export default function ScrollFX() {
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const words = Array.from(document.querySelectorAll<HTMLElement>(".scrollfx__word"));
    const parallax = Array.from(document.querySelectorAll<HTMLElement>("[data-parallax]"));

    if (reduce) return;

    let ticking = false;
    const update = () => {
      ticking = false;
      const vh = window.innerHeight;
      const y = window.scrollY;

      // background words: continuous scroll-linked depth parallax
      for (const el of words) {
        const d = parseFloat(el.dataset.depth || "0.3");
        const h = parseFloat(el.dataset.drift || "0");
        const r = el.dataset.rot || "0";
        el.style.transform = `translate3d(${(y * h).toFixed(1)}px, ${(y * d).toFixed(1)}px, 0) rotate(${r}deg)`;
      }

      // content blocks: subtle drift relative to the viewport centre
      for (const el of parallax) {
        const speed = parseFloat(el.dataset.speed || "30");
        const rect = el.getBoundingClientRect();
        const delta = (rect.top + rect.height / 2 - vh / 2) / vh;
        el.style.transform = `translate3d(0, ${(-delta * speed).toFixed(1)}px, 0)`;
      }
    };

    const onScroll = () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(update);
      }
    };

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    window.addEventListener("load", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      window.removeEventListener("load", onScroll);
    };
  }, []);

  return (
    <div className="scrollfx" aria-hidden="true">
      {WORDS.map((w, i) => (
        <span
          key={i}
          className={`scrollfx__word indic${w.accent ? " scrollfx__word--accent" : ""}`}
          lang={w.lang}
          data-depth={w.depth}
          data-drift={w.drift}
          data-rot={w.rot}
          style={{ top: `${w.top}%`, left: `${w.left}%`, fontSize: `${w.size}vw` }}
        >
          {w.t}
        </span>
      ))}

      {/* Curvy-line version — commented out; swap back by removing the words
          above and un-commenting this (plus the .scrollfx__path CSS).
      <svg viewBox="0 0 120 100" preserveAspectRatio="none">
        <path className="scrollfx__path" d="M28 -3 C 96 14, 6 32, 46 50 C 86 68, 16 84, 62 103" />
        <path className="scrollfx__path scrollfx__path--2" d="M78 -3 C 18 16, 98 34, 56 52 C 20 70, 94 86, 42 103" />
      </svg>
      */}
    </div>
  );
}
