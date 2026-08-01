import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Bricolage_Grotesque, Spectral } from "next/font/google";
import "./globals.css";

// Self-hosted at build time by next/font — no runtime CDN call, so the UI
// still loads with the network pulled. Indic scripts fall back to system Noto.
const display = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const body = Spectral({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SETU — offline translation across the 22 languages of India",
  description:
    "A private, on-device bridge between the 22 scheduled languages of India and English. No servers, no accounts — nothing leaves your machine.",
  applicationName: "SETU",
  authors: [{ name: "SETU" }],
};

export const viewport: Viewport = {
  themeColor: "#f7f2ea",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable}`}>
      <body id="top">{children}</body>
    </html>
  );
}
