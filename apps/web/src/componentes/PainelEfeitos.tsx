"use client";

import { formatarTempo } from "@/lib/formatar";
import type { EfeitosProjeto } from "@/lib/tipos";

const VAZIO: EfeitosProjeto = {
  brilho: 0,
  tremor: 0,
  luz: 0,
  contorno: false,
  transicao: "corte",
  zoom: null,
  som: { id: "nenhum", inicio: 0 },
};

type Props = {
  efeitos: EfeitosProjeto;
  aoMudar: (efeitos: EfeitosProjeto) => void;
  posicaoFinal: number;
  duracaoFinal: number;
  temRosto: boolean;
};

/** Brilho, luz, tremor, zoom, transição e um som curto. A prévia usa os mesmos números do render. */
export function PainelEfeitos({ efeitos, aoMudar, posicaoFinal, duracaoFinal, temRosto }: Props) {
  const atual = { ...VAZIO, ...efeitos, som: { ...VAZIO.som, ...efeitos.som } };
  const zoom = atual.zoom;
  const mudar = (mudanca: Partial<EfeitosProjeto>) => aoMudar({ ...atual, ...mudanca });

  return (
    <section className="cartao p-6" aria-labelledby="titulo-efeitos">
      <h2 id="titulo-efeitos" className="font-display text-lg font-bold">
        Efeitos
      </h2>
      <p className="mt-1 text-sm text-suave">O logo e os textos ficam parados. O som é gerado pelo HolyCut, sem faixa de terceiro.</p>
      <label className="mt-4 flex items-center gap-3 text-sm">
        <span className="w-24 shrink-0 text-suave">Brilho</span>
        <input
          type="range"
          min={-0.3}
          max={0.3}
          step={0.01}
          value={atual.brilho}
          onChange={(evento) => mudar({ brilho: Number(evento.target.value) })}
          className="w-full accent-[var(--hc-orange)]"
        />
      </label>
      <label className="mt-3 flex items-center gap-3 text-sm">
        <span className="w-24 shrink-0 text-suave">Tremor</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={atual.tremor}
          onChange={(evento) => mudar({ tremor: Number(evento.target.value) })}
          className="w-full accent-[var(--hc-orange)]"
        />
      </label>
      <label className="mt-3 flex items-center gap-3 text-sm">
        <span className="w-24 shrink-0 text-suave">Luz</span>
        <input
          type="range"
          min={0}
          max={0.8}
          step={0.02}
          value={atual.luz}
          onChange={(evento) => mudar({ luz: Number(evento.target.value) })}
          className="w-full accent-[var(--hc-orange)]"
        />
      </label>
      <label className="mt-3 flex items-center gap-3 text-sm">
        <input
          type="checkbox"
          checked={atual.contorno}
          onChange={(evento) => mudar({ contorno: evento.target.checked })}
          className="size-4 accent-[var(--hc-orange)]"
        />
        Contorno do rosto
      </label>
      {atual.contorno && !temRosto ? (
        <p className="mt-2 text-xs text-suave">
          O contorno espera a trilha do rosto. Ligue o acompanhamento na ferramenta Enquadrar.
        </p>
      ) : null}
      <label className="mt-4 flex flex-col gap-1 text-sm">
        <span className="text-suave">Entre as partes</span>
        <select
          value={atual.transicao}
          onChange={(evento) => mudar({ transicao: evento.target.value as EfeitosProjeto["transicao"] })}
          className="rounded-xl border border-borda bg-ink px-3 py-2 outline-none focus:border-violeta"
        >
          <option value="corte">Corte seco</option>
          <option value="escurecer">Escurecer</option>
          <option value="desfoque">Desfoque</option>
          <option value="fusao">Fusão</option>
        </select>
      </label>
      <div className="mt-4 rounded-2xl border border-borda p-4">
        <p className="text-sm font-semibold">Aproximar</p>
        <label className="mt-3 flex items-center gap-3 text-sm">
          <span className="w-24 shrink-0 text-suave">Zoom</span>
          <input
            type="range"
            min={1}
            max={1.35}
            step={0.01}
            value={zoom?.nivel ?? 1}
            onChange={(evento) => {
              const nivel = Number(evento.target.value);
              mudar({
                zoom: nivel <= 1 ? null : { inicio: zoom?.inicio ?? 0, fim: zoom?.fim ?? null, nivel },
              });
            }}
            className="w-full accent-[var(--hc-orange)]"
          />
        </label>
        {zoom && zoom.nivel > 1 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              className="botao-contorno px-3 py-1.5 text-xs"
              onClick={() => mudar({ zoom: { ...zoom, inicio: Math.round(posicaoFinal * 10) / 10 } })}
            >
              Começa aqui
            </button>
            <button
              type="button"
              className="botao-contorno px-3 py-1.5 text-xs"
              onClick={() => mudar({ zoom: { ...zoom, fim: Math.max(Math.round(posicaoFinal * 10) / 10, zoom.inicio + 0.2) } })}
            >
              Termina aqui
            </button>
            <p className="w-full text-xs text-suave">
              {formatarTempo(zoom.inicio)}
              {zoom.fim === null ? " até o fim" : ` – ${formatarTempo(Math.min(zoom.fim, duracaoFinal))}`}
            </p>
          </div>
        ) : null}
      </div>
      <label className="mt-4 flex flex-col gap-1 text-sm">
        <span className="text-suave">Som</span>
        <select
          value={atual.som.id}
          onChange={(evento) => mudar({ som: { ...atual.som, id: evento.target.value as EfeitosProjeto["som"]["id"] } })}
          className="rounded-xl border border-borda bg-ink px-3 py-2 outline-none focus:border-violeta"
        >
          <option value="nenhum">Nenhum</option>
          <option value="sopro">Sopro</option>
          <option value="toque">Toque</option>
        </select>
      </label>
      {atual.som.id !== "nenhum" ? (
        <button
          type="button"
          className="botao-contorno mt-2 px-3 py-1.5 text-xs"
          onClick={() => mudar({ som: { ...atual.som, inicio: Math.round(posicaoFinal * 10) / 10 } })}
        >
          Tocar em {formatarTempo(posicaoFinal)}
        </button>
      ) : null}
    </section>
  );
}
