"use client";

import { useEffect } from "react";

// Background watermark: the word for "bridge" across Indic scripts
// (सेतु / সেতু / பாலம் …), drifting at different speeds as you scroll. Sits
// behind content. This replaces the earlier curvy-line version (kept, commented,
// at the bottom in case we want to switch back).
const WORDS = [
  { t: "सेतु", lang: "hi", top: 5, left: 3, size: 13, speed: 90 },
  { t: "সেতু", lang: "bn", top: 15, left: 64, size: 11, speed: 140 },
  { t: "பாலம்", lang: "ta", top: 27, left: 5, size: 10, speed: 70 },
  { t: "వంతెన", lang: "te", top: 38, left: 58, size: 12, speed: 150 },
  { t: "ಸೇತುವೆ", lang: "kn", top: 50, left: 4, size: 10, speed: 100 },
  { t: "പാലം", lang: "ml", top: 61, left: 62, size: 12, speed: 80 },
  { t: "ਪੁਲ", lang: "pa", top: 71, left: 9, size: 13, speed: 120 },
  { t: "پُل", lang: "ur", top: 81, left: 60, size: 13, speed: 60 },
  { t: "ᱥᱮᱛᱩ", lang: "sat", top: 91, left: 7, size: 10, speed: 110 },
];

export default function ScrollFX() {
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;

    const parallax = Array.from(
      document.querySelectorAll<HTMLElement>("[data-parallax]"),
    );

    let ticking = false;
    const update = () => {
      ticking = false;
      const vh = window.innerHeight;
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
          className="scrollfx__word indic"
          lang={w.lang}
          data-parallax
          data-speed={w.speed}
          style={{ top: `${w.top}%`, left: `${w.left}%`, fontSize: `${w.size}vw` }}
        >
          {w.t}
        </span>
      ))}

      {/* Curvy-line version — commented out for now; swap back by removing the
          words above and un-commenting this (plus .scrollfx__path CSS).
      <svg viewBox="0 0 120 100" preserveAspectRatio="none">
        <path className="scrollfx__path" d="M28 -3 C 96 14, 6 32, 46 50 C 86 68, 16 84, 62 103" />
        <path className="scrollfx__path scrollfx__path--2" d="M78 -3 C 18 16, 98 34, 56 52 C 20 70, 94 86, 42 103" />
      </svg>
      */}
    </div>
  );
}
