"use client";

import type { BlocoLegenda, Legenda } from "@/lib/tipos";

// O mesmo dourado de core/modelos/legenda.py (COR_DOURADA). O Destaque e o Karaokê usam a cor da igreja.
const DOURADO = "#FFD24D";

function blocoNoInstante(blocos: BlocoLegenda[], instante: number): BlocoLegenda | null {
  return blocos.find((bloco) => instante >= bloco.inicio && instante < bloco.fim) ?? null;
}

/** No Karaokê, a palavra acesa é a do momento. Nos outros presets, é a marcada como destaque. */
function indiceAceso(bloco: BlocoLegenda, instante: number, preset: Legenda["preset"]): number {
  if (preset === "karaoke") {
    let aceso = 0;
    bloco.palavras.forEach((palavra, indice) => {
      if (instante >= palavra.inicio) aceso = indice;
    });
    return aceso;
  }
  const destaque = bloco.palavras.findIndex((palavra) => palavra.destaque);
  return destaque >= 0 ? destaque : 0;
}

export function LegendaNaPrevia({
  blocos,
  instante,
  legenda,
  corDestaque,
}: {
  blocos: BlocoLegenda[];
  instante: number;
  legenda: Legenda;
  corDestaque: string;
}) {
  if (!legenda.ativa) return null;
  const bloco = blocoNoInstante(blocos, instante);
  if (!bloco) return null;
  const aceso = indiceAceso(bloco, instante, legenda.preset);
  const cor = legenda.preset === "digno" ? DOURADO : corDestaque;
  return (
    <p
      className={`pointer-events-none absolute inset-x-[8%] z-10 text-center font-display font-bold leading-tight text-white ${
        legenda.posicao === "centro" ? "top-1/2 -translate-y-1/2" : "bottom-[12%]"
      }`}
      style={{ fontSize: "3.8cqh", WebkitTextStroke: "0.12cqh #000", paintOrder: "stroke fill" }}
    >
      {bloco.palavras.map((palavra, indice) => {
        const acesa = legenda.preset !== "clean" && indice === aceso;
        return (
          <span
            key={`${palavra.id}-${indice}`}
            style={acesa ? { color: cor } : undefined}
            className={acesa && legenda.preset === "digno" ? "font-script text-[1.35em] leading-none" : undefined}
          >
            {indice > 0 ? " " : ""}
            {palavra.texto}
          </span>
        );
      })}
    </p>
  );
}
