import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Bricolage_Grotesque, Spectral } from "next/font/google";
import "./globals.css";

// Self-hosted at build time by next/font (no runtime CDN call), so the UI
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
  title: "SETU: offline translation across the 22 languages of India",
  description:
    "A private, on-device bridge between the 22 scheduled languages of India and English. No servers, no accounts, nothing leaves your machine.",
  applicationName: "SETU",
  authors: [{ name: "SETU" }],
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f7f2ea" },
    { media: "(prefers-color-scheme: dark)", color: "#231f1b" },
  ],
  width: "device-width",
  initialScale: 1,
};

// Runs before paint so the stored/system theme is set with no flash of wrong theme.
const THEME_INIT =
  "!function(){try{var t=localStorage.getItem('setu-theme')||(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme='light'}}()";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${display.variable} ${body.variable}`}
    >
      <body id="top">
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
        {children}
      </body>
    </html>
  );
}
