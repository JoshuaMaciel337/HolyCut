import type { Metadata } from "next";

// O token do link vale como senha daquele vídeo: a página não entra em buscadores
// e não manda o endereço como "Referer" para lugar nenhum.
export const metadata: Metadata = {
  title: "Aprovar vídeo",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default function LayoutAprovar({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
