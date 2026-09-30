"use client";

import type { Fundo } from "@/lib/tipos";

/** Escurecer e desfocar o vídeo atrás dos textos, para a leitura ficar fácil. */
export function PainelFundo({ fundo, aoMudar }: { fundo: Fundo; aoMudar: (fundo: Fundo) => void }) {
  return (
    <section className="cartao p-6" aria-labelledby="titulo-fundo">
      <h2 id="titulo-fundo" className="font-display text-lg font-bold">
        Fundo
      </h2>
      <p className="mt-1 text-sm text-suave">Escureça ou desfoque o vídeo para o texto aparecer mais.</p>
      <div className="mt-4 flex flex-col gap-3 text-sm">
        <label className="flex items-center gap-3">
          <span className="w-24 shrink-0 text-suave">Escurecer</span>
          <input
            type="range"
            min={0}
            max={0.8}
            step={0.05}
            value={fundo.escurecer}
            onChange={(evento) => aoMudar({ ...fundo, escurecer: Number(evento.target.value) })}
            className="w-full accent-[var(--hc-orange)]"
          />
          <span className="w-12 text-right tabular-nums">{Math.round(fundo.escurecer * 100)}%</span>
        </label>
        <label className="flex items-center gap-3">
          <span className="w-24 shrink-0 text-suave">Desfocar</span>
          <input
            type="range"
            min={0}
            max={30}
            step={1}
            value={fundo.desfoque}
            onChange={(evento) => aoMudar({ ...fundo, desfoque: Number(evento.target.value) })}
            className="w-full accent-[var(--hc-orange)]"
          />
          <span className="w-12 text-right tabular-nums">{fundo.desfoque}</span>
        </label>
      </div>
    </section>
  );
}
