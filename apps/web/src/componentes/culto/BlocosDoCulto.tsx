"use client";

import { LayoutList } from "lucide-react";

import { formatarTempo } from "@/lib/formatar";
import type { Blocos, TipoBloco } from "@/lib/tipos";

export const ROTULOS_BLOCO: Record<TipoBloco, string> = {
  louvor: "Louvor",
  oracao: "Oração",
  avisos: "Avisos",
  oferta: "Oferta",
  ceia: "Santa Ceia",
  pregacao: "Pregação",
  outro: "Outro",
};

const CORES: Record<TipoBloco, string> = {
  louvor: "bg-violeta",
  oracao: "bg-ciano",
  avisos: "bg-amarelo",
  oferta: "bg-laranja",
  ceia: "bg-coral",
  pregacao: "bg-magenta",
  outro: "bg-surface-2",
};

type Props = {
  dados: Blocos | null;
  erro: string;
  andando: boolean;
  pedir: () => void;
  duracao: number;
  tempo: number;
  aoBuscar: (segundos: number) => void;
};

/** O culto numa faixa colorida, bloco a bloco. Clicar num bloco leva o player até o começo dele. */
export function BlocosDoCulto({ dados, erro, andando, pedir, duracao, tempo, aoBuscar }: Props) {
  const blocos = dados?.status === "pronta" ? dados.blocos : [];

  return (
    <section className="cartao p-4 sm:p-6" aria-labelledby="titulo-blocos">
      <h2 id="titulo-blocos" className="flex items-center gap-2 font-display text-lg font-bold">
        <LayoutList className="size-5 text-violeta" aria-hidden /> Blocos do culto
      </h2>
      <p className="mt-1 text-sm text-suave">Louvor, oração, avisos, oferta e pregação, separados pelo áudio e pelas palavras ditas.</p>
      {erro ? <p className="mt-3 text-sm text-vermelho" role="alert">{erro}</p> : null}
      {andando ? (
        <p className="mt-4 text-sm text-suave" role="status">
          {dados?.mensagem || "Na fila"} · {dados?.progresso ?? 0}%
        </p>
      ) : null}
      {dados?.status === "erro" ? (
        <p className="mt-4 text-sm text-vermelho" role="alert">
          {dados.erro || "Não foi possível separar os blocos."}
        </p>
      ) : null}
      {dados?.status === "ausente" ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button type="button" onClick={pedir} className="botao-contorno px-4 py-2 text-sm">
            Separar os blocos
          </button>
          <span className="text-xs text-suave">Sai da transcrição, com a IA ligada no servidor. Sem ela, marque a pregação à mão.</span>
        </div>
      ) : null}
      {blocos.length > 0 && duracao > 0 ? (
        <>
          <div className="relative mt-4 flex h-7 w-full overflow-hidden rounded-lg bg-surface-2">
            {blocos.map((bloco) => (
              <button
                key={bloco.inicio}
                type="button"
                onClick={() => aoBuscar(bloco.inicio)}
                className={`${CORES[bloco.tipo]} h-full border-r border-ink/50 last:border-0 hover:brightness-125 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-white`}
                style={{ width: `${((bloco.fim - bloco.inicio) / duracao) * 100}%` }}
                aria-label={`${ROTULOS_BLOCO[bloco.tipo]}, de ${formatarTempo(bloco.inicio)} a ${formatarTempo(bloco.fim)}`}
                title={`${ROTULOS_BLOCO[bloco.tipo]} · ${formatarTempo(bloco.inicio)}`}
              />
            ))}
            <span
              className="pointer-events-none absolute inset-y-0 w-0.5 bg-white"
              style={{ left: `${Math.min(tempo / duracao, 1) * 100}%` }}
              aria-hidden
            />
          </div>
          <ol className="mt-4 flex flex-col divide-y divide-borda">
            {blocos.map((bloco) => {
              const atual = tempo >= bloco.inicio && tempo < bloco.fim;
              return (
                <li key={bloco.inicio}>
                  <button
                    type="button"
                    onClick={() => aoBuscar(bloco.inicio)}
                    className={`flex w-full items-start gap-3 py-2.5 text-left text-sm hover:text-laranja ${atual ? "text-texto" : ""}`}
                    aria-current={atual ? "true" : undefined}
                  >
                    <span className={`mt-1.5 size-2.5 shrink-0 rounded-full ${CORES[bloco.tipo]}`} aria-hidden />
                    <span className="w-24 shrink-0 font-medium">{ROTULOS_BLOCO[bloco.tipo]}</span>
                    <span className="w-28 shrink-0 tabular-nums text-suave">
                      {formatarTempo(bloco.inicio)}–{formatarTempo(bloco.fim)}
                    </span>
                    {bloco.frase ? <span className="min-w-0 truncate text-suave">“{bloco.frase}...”</span> : null}
                  </button>
                </li>
              );
            })}
          </ol>
          <p className="mt-3 text-xs text-suave">
            Separados automaticamente{dados?.nomes_pelo_modelo ? ", com os nomes dados pela IA" : ", com os nomes pelas palavras-chave"}. Confira
            antes de exportar.
          </p>
        </>
      ) : null}
    </section>
  );
}
