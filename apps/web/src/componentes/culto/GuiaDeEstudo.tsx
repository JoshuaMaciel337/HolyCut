"use client";

import { Printer, ScrollText } from "lucide-react";
import Link from "next/link";

import { formatarTempo } from "@/lib/formatar";
import type { Estudo } from "@/lib/tipos";
import { useEstudo } from "@/lib/useEstudo";

/** As partes do guia, iguais na tela e na impressão. */
export function SecoesDoGuia({ estudo }: { estudo: Estudo }) {
  return (
    <div className="flex flex-col gap-6">
      {estudo.versiculos_chave.length > 0 ? (
        <section aria-labelledby="guia-texto-base">
          <h3 id="guia-texto-base" className="font-display text-base font-bold">
            Texto base
          </h3>
          <ul className="mt-2 flex flex-col gap-1.5 text-sm">
            {estudo.versiculos_chave.map((item) => (
              <li key={item.referencia}>
                <strong>{item.referencia}</strong>
                {item.vezes > 1 ? <span className="opacity-70"> · citado {item.vezes} vezes</span> : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {estudo.resumo.length > 0 ? (
        <section aria-labelledby="guia-ideias">
          <h3 id="guia-ideias" className="font-display text-base font-bold">
            O que a mensagem disse
          </h3>
          <ul className="mt-2 flex flex-col gap-2 text-sm leading-relaxed">
            {estudo.resumo.map((frase) => (
              <li key={frase.inicio}>“{frase.texto}”</li>
            ))}
          </ul>
        </section>
      ) : null}
      {estudo.perguntas.length > 0 ? (
        <section aria-labelledby="guia-perguntas">
          <h3 id="guia-perguntas" className="font-display text-base font-bold">
            Perguntas para o grupo
          </h3>
          <ol className="mt-2 flex list-decimal flex-col gap-3 pl-5 text-sm">
            {estudo.perguntas.map((item) => (
              <li key={item.pergunta}>
                <p className="font-medium">{item.pergunta}</p>
                <p className="mt-0.5 text-xs opacity-70">
                  A partir de: “{item.base.texto}” ({formatarTempo(item.base.inicio)})
                </p>
              </li>
            ))}
          </ol>
        </section>
      ) : null}
      {estudo.aplicacoes.length > 0 ? (
        <section aria-labelledby="guia-aplicacao">
          <h3 id="guia-aplicacao" className="font-display text-base font-bold">
            Para viver nesta semana
          </h3>
          <ul className="mt-2 flex flex-col gap-2 text-sm">
            {estudo.aplicacoes.map((frase) => (
              <li key={frase.inicio}>“{frase.texto}”</li>
            ))}
          </ul>
        </section>
      ) : null}
      <section aria-labelledby="guia-oracao">
        <h3 id="guia-oracao" className="font-display text-base font-bold">
          Oração
        </h3>
        <p className="mt-2 text-sm">{estudo.oracao}</p>
      </section>
    </div>
  );
}

/** O guia para células: texto base, as ideias, as perguntas, a aplicação e a oração. */
export function GuiaDeEstudo({ midiaId }: { midiaId: string }) {
  const { dados, erro, pedir, andando } = useEstudo(midiaId);

  return (
    <section className="cartao p-6" aria-labelledby="titulo-guia">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="titulo-guia" className="flex items-center gap-2 font-display text-lg font-bold">
            <ScrollText className="size-5 text-violeta" aria-hidden /> Guia de estudo
          </h2>
          <p className="mt-1 text-sm text-suave">Para células e devocionais. Cada pergunta se apoia numa frase que o pregador disse.</p>
        </div>
        {dados?.status === "pronta" ? (
          <Link href={`/app/midias/${midiaId}/estudo`} className="botao-contorno px-4 py-2 text-sm">
            <Printer className="size-4" aria-hidden /> Imprimir ou salvar em PDF
          </Link>
        ) : null}
      </div>
      {erro ? <p className="mt-3 text-sm text-vermelho" role="alert">{erro}</p> : null}
      {andando ? (
        <p className="mt-4 text-sm text-suave" role="status">
          {dados?.mensagem || "Na fila"} · {dados?.progresso ?? 0}%
        </p>
      ) : null}
      {dados?.status === "erro" ? (
        <p className="mt-4 text-sm text-vermelho" role="alert">
          {dados.erro || "Não foi possível preparar o guia."}
        </p>
      ) : null}
      {dados?.status === "ausente" ? (
        <button type="button" onClick={pedir} className="botao-contorno mt-4 px-4 py-2 text-sm">
          Preparar o guia de estudo
        </button>
      ) : null}
      {dados?.status === "pronta" ? (
        <div className="mt-5">
          <SecoesDoGuia estudo={dados} />
          <p className="mt-5 text-xs text-suave">
            Gerado por IA a partir da transcrição. As perguntas são sugestões: o líder revisa antes do encontro.
          </p>
        </div>
      ) : null}
    </section>
  );
}
