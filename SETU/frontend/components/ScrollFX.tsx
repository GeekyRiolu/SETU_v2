"use client";

import { useEffect, useRef } from "react";

// A curvy line that draws itself as you scroll, plus gentle parallax drift on
// elements marked [data-parallax][data-speed]. One rAF loop drives both.
// Fully client-side; respects prefers-reduced-motion.
export default function ScrollFX() {
  const pathsRef = useRef<(SVGPathElement | null)[]>([]);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const paths = pathsRef.current.filter((p): p is SVGPathElement => !!p);
    const lengths = paths.map((p) => p.getTotalLength());

    paths.forEach((p, i) => {
      p.style.strokeDasharray = `${lengths[i]}`;
      p.style.strokeDashoffset = reduce ? "0" : `${lengths[i]}`;
    });

    if (reduce) return;

    const parallax = Array.from(
      document.querySelectorAll<HTMLElement>("[data-parallax]"),
    );

    let ticking = false;
    const update = () => {
      ticking = false;
      const vh = window.innerHeight;
      const max = document.documentElement.scrollHeight - vh;
      const progress = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;

      // draw the line proportionally to scroll progress
      paths.forEach((p, i) => {
        p.style.strokeDashoffset = `${lengths[i] * (1 - progress)}`;
      });

      // drift each element relative to its distance from the viewport centre
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

  const setPath = (i: number) => (el: SVGPathElement | null) => {
    pathsRef.current[i] = el;
  };

  return (
    <div className="scrollfx" aria-hidden="true">
      <svg viewBox="0 0 120 100" preserveAspectRatio="none">
        <path
          ref={setPath(0)}
          className="scrollfx__path"
          d="M28 -3 C 96 14, 6 32, 46 50 C 86 68, 16 84, 62 103"
        />
        <path
          ref={setPath(1)}
          className="scrollfx__path scrollfx__path--2"
          d="M78 -3 C 18 16, 98 34, 56 52 C 20 70, 94 86, 42 103"
        />
      </svg>
    </div>
  );
}
