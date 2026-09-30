"use client";

import Image from "next/image";

import { cssDoFiltro, FiltroSvg, useFiltros } from "@/lib/filtros";
import type { Cor } from "@/lib/tipos";

/** Filtros de cor com miniatura sobre a capa da gravação, e a intensidade. */
export function PainelCor({ cor, aoMudar, capa }: { cor: Cor; aoMudar: (cor: Cor) => void; capa?: string }) {
  const filtros = useFiltros();
  return (
    <section className="cartao p-6" aria-labelledby="titulo-cor">
      <h2 id="titulo-cor" className="font-display text-lg font-bold">
        Cor
      </h2>
      <div role="radiogroup" aria-label="Filtro de cor" className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-6">
        {filtros.map((filtro) => {
          const id = `miniatura-cor-${filtro.id}`;
          const escolhido = cor.filtro === filtro.id;
          return (
            <button
              key={filtro.id}
              type="button"
              role="radio"
              aria-checked={escolhido}
              onClick={() => aoMudar({ filtro: filtro.id, intensidade: cor.filtro === filtro.id ? cor.intensidade : 1 })}
              className={`flex flex-col items-center gap-1.5 rounded-xl border p-1.5 transition ${escolhido ? "border-laranja bg-laranja/10" : "border-borda hover:border-suave"}`}
            >
              <FiltroSvg id={id} filtro={filtro} intensidade={1} />
              <span className="relative block aspect-square w-full overflow-hidden rounded-lg bg-surface-2">
                {capa ? (
                  <Image src={capa} alt="" fill unoptimized sizes="80px" className="object-cover" style={{ filter: cssDoFiltro(id, filtro, 1) || undefined }} />
                ) : null}
              </span>
              <span className="text-xs font-semibold">{filtro.nome}</span>
            </button>
          );
        })}
      </div>
      <label className={`mt-4 flex items-center gap-3 text-sm ${cor.filtro === "natural" ? "pointer-events-none opacity-50" : ""}`}>
        <span className="w-24 shrink-0 text-suave">Intensidade</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={cor.intensidade}
          onChange={(evento) => aoMudar({ ...cor, intensidade: Number(evento.target.value) })}
          className="w-full accent-[var(--hc-orange)]"
        />
        <span className="w-12 text-right tabular-nums">{Math.round(cor.intensidade * 100)}%</span>
      </label>
    </section>
  );
}
