"use client";

import Link from "next/link";

import type { Legenda, PosicaoLegenda, PresetLegenda } from "@/lib/tipos";

const PRESETS: { valor: PresetLegenda; rotulo: string; descricao: string }[] = [
  { valor: "clean", rotulo: "Clean", descricao: "Tudo em branco, sem destaque." },
  { valor: "karaoke", rotulo: "Karaokê", descricao: "A palavra do momento acende na cor da igreja." },
  { valor: "destaque", rotulo: "Destaque", descricao: "A palavra mais longa fica na cor da igreja." },
  { valor: "digno", rotulo: "Digno", descricao: "Essa palavra sai em letra manuscrita, dourada." },
  { valor: "flutuante", rotulo: "Flutuante", descricao: "Uma palavra por vez, grande, subindo." },
];

const POSICOES: { valor: PosicaoLegenda; rotulo: string }[] = [
  { valor: "base", rotulo: "Embaixo" },
  { valor: "centro", rotulo: "No centro" },
];

export function PainelLegenda({
  legenda,
  temTranscricao,
  midiaId,
  aoMudar,
}: {
  legenda: Legenda;
  temTranscricao: boolean;
  midiaId: string;
  aoMudar: (legenda: Legenda) => void;
}) {
  return (
    <section className="cartao p-6" aria-labelledby="titulo-legenda">
      <h2 id="titulo-legenda" className="font-display text-lg font-bold">
        Legenda
      </h2>
      <p className="mt-1 text-sm text-suave">Gerado por IA, para revisar. A fala não foi corrigida.</p>
      {!temTranscricao ? (
        <p className="mt-3 text-sm text-suave">
          Esta gravação ainda não tem transcrição.{" "}
          <Link href={`/app/midias/${midiaId}?aba=transcricao`} className="font-medium text-laranja hover:underline">
            Transcreva na página do culto
          </Link>{" "}
          para a legenda aparecer.
        </p>
      ) : null}
      <label className="mt-4 flex items-center gap-3 text-sm">
        <input
          type="checkbox"
          checked={legenda.ativa}
          onChange={(evento) => aoMudar({ ...legenda, ativa: evento.target.checked })}
          className="size-4 accent-[var(--hc-orange)]"
        />
        Mostrar a legenda no vídeo
      </label>
      <div className={legenda.ativa ? "mt-4" : "mt-4 pointer-events-none opacity-50"}>
        <div role="radiogroup" aria-label="Estilo da legenda" className="grid gap-2 sm:grid-cols-2">
          {PRESETS.map((preset) => (
            <button
              key={preset.valor}
              type="button"
              role="radio"
              aria-checked={legenda.preset === preset.valor}
              onClick={() => aoMudar({ ...legenda, preset: preset.valor })}
              className={`rounded-xl border px-3 py-2 text-left text-sm ${
                legenda.preset === preset.valor ? "border-laranja bg-laranja/10" : "border-borda hover:border-suave"
              }`}
            >
              <span className="font-semibold">{preset.rotulo}</span>
              <span className="mt-0.5 block text-xs text-suave">{preset.descricao}</span>
            </button>
          ))}
        </div>
        <div
          role="radiogroup"
          aria-label="Posição da legenda"
          className="mt-3 flex gap-1 rounded-full border border-borda bg-ink p-1"
        >
          {POSICOES.map((posicao) => (
            <button
              key={posicao.valor}
              type="button"
              role="radio"
              aria-checked={legenda.posicao === posicao.valor}
              onClick={() => aoMudar({ ...legenda, posicao: posicao.valor, x: null, y: null })}
              className={`flex-1 rounded-full px-3 py-1 text-xs font-semibold ${
                legenda.posicao === posicao.valor ? "bg-surface-2 text-texto" : "text-suave hover:text-texto"
              }`}
            >
              {posicao.rotulo}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
