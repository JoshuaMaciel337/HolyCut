import type { Metadata, Viewport } from "next";
import { Caveat, Inter, Montserrat } from "next/font/google";

import "./globals.css";

const montserrat = Montserrat({ subsets: ["latin"], variable: "--font-montserrat", display: "swap" });
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const caveat = Caveat({ subsets: ["latin"], variable: "--font-caveat", display: "swap" });

export const metadata: Metadata = {
  title: {
    default: "HolyCut — Transforme momentos em histórias",
    template: "%s · HolyCut",
  },
  description:
    "IA que transforma a gravação do culto em Stories, Reels e cortes da pregação prontos para postar, com a identidade da sua igreja.",
  applicationName: "HolyCut",
};

export const viewport: Viewport = {
  themeColor: "#08090F",
  colorScheme: "dark",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" className={`${montserrat.variable} ${inter.variable} ${caveat.variable}`}>
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
