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
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#070709" },
    { media: "(prefers-color-scheme: light)", color: "#F8F6F2" },
  ],
  colorScheme: "dark light",
};

// Roda antes da página aparecer: sem escolha salva, segue o sistema. Assim o tema não pisca.
const SCRIPT_TEMA = `try{var t=localStorage.getItem("holycut-tema");if(t==="claro"||(!t&&matchMedia("(prefers-color-scheme: light)").matches))document.documentElement.dataset.tema="claro"}catch(e){}`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" className={`${montserrat.variable} ${inter.variable} ${caveat.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA }} />
      </head>
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
