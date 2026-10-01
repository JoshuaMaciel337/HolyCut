"use client";

import { BookOpen } from "lucide-react";

import { formatarTempo } from "@/lib/formatar";
import { useEstudo } from "@/lib/useEstudo";

/** A mensagem nas palavras do próprio pregador: as frases centrais, os temas e os personagens. */
export function ResumoDoCulto({ midiaId }: { midiaId: string }) {
  const { dados, erro, pedir, andando } = useEstudo(midiaId);

  return (
    <section className="cartao p-6" aria-labelledby="titulo-resumo">
      <h2 id="titulo-resumo" className="flex items-center gap-2 font-display text-lg font-bold">
        <BookOpen className="size-5 text-violeta" aria-hidden /> A mensagem
      </h2>
      <p className="mt-2 text-sm text-suave">
        As frases centrais da pregação, como o pregador disse, na ordem em que apareceram. Nada é reescrito.
      </p>
      {erro ? <p className="mt-3 text-sm text-vermelho" role="alert">{erro}</p> : null}
      {andando ? (
        <p className="mt-4 text-sm text-suave" role="status">
          {dados?.mensagem || "Na fila"} · {dados?.progresso ?? 0}%
        </p>
      ) : null}
      {dados?.status === "erro" ? (
        <p className="mt-4 text-sm text-vermelho" role="alert">
          {dados.erro || "Não foi possível preparar o resumo."}
        </p>
      ) : null}
      {dados?.status === "ausente" ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button type="button" onClick={pedir} className="botao-contorno px-4 py-2 text-sm">
            Preparar o resumo e o estudo
          </button>
          <span className="text-xs text-suave">Sai da transcrição, com a IA ligada no servidor.</span>
        </div>
      ) : null}
      {dados?.status === "pronta" ? (
        <>
          <ol className="mt-4 flex flex-col gap-3">
            {dados.resumo.map((frase) => (
              <li key={frase.inicio} className="flex gap-3">
                <span className="w-12 shrink-0 pt-0.5 text-right text-xs tabular-nums text-suave">{formatarTempo(frase.inicio)}</span>
                <blockquote className="border-l-2 border-violeta/60 pl-3 text-sm leading-relaxed">“{frase.texto}”</blockquote>
              </li>
            ))}
          </ol>
          {dados.temas.length > 0 || dados.personagens.length > 0 ? (
            <div className="mt-5 flex flex-col gap-3 text-sm">
              {dados.temas.length > 0 ? (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-suave">Temas</span>
                  {dados.temas.map((tema) => (
                    <span key={tema} className="rounded-full border border-borda px-3 py-1 text-xs">
                      {tema}
                    </span>
                  ))}
                </div>
              ) : null}
              {dados.personagens.length > 0 ? (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-suave">Personagens</span>
                  {dados.personagens.map((nome) => (
                    <span key={nome} className="rounded-full bg-violeta/15 px-3 py-1 text-xs">
                      {nome}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          <p className="mt-4 text-xs text-suave">Gerado por IA a partir da transcrição. Revise antes de compartilhar.</p>
        </>
      ) : null}
    </section>
  );
}
