"use client";

import { useEffect, useRef, useState } from "react";
import { BRIDGE_IN_SCRIPTS } from "@/lib/languages";

// Cycles the word for "bridge" across Indian scripts (सेतु / সেতু / பாலம் / …) so
// no single language is favoured. Decorative -> aria-hidden. The initial index is
// deterministic (`start`) so SSR and client hydration match; each instance drifts
// at a slightly different pace, so several scripts show at once.
export default function BridgeWord({
  className = "",
  start = 0,
}: {
  className?: string;
  start?: number;
}) {
  const n = BRIDGE_IN_SCRIPTS.length;
  const [i, setI] = useState(start % n);
  const cycled = useRef(false);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = setInterval(() => {
      cycled.current = true;
      setI((v) => (v + 1) % n);
    }, 2500 + (start % 4) * 250);
    return () => clearInterval(id);
  }, [n, start]);

  return (
    <span className={`bridgeword indic ${className}`.trim()} aria-hidden="true">
      <span key={i} className={cycled.current ? "bridgeword__in" : undefined}>
        {BRIDGE_IN_SCRIPTS[i].word}
      </span>
    </span>
  );
}
