"use client";

import { ArrowLeft, Printer } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { SecoesDoGuia } from "@/componentes/culto/GuiaDeEstudo";
import { dataDoCulto } from "@/lib/acervo";
import { chamarApi } from "@/lib/api";
import type { Identidade, Midia } from "@/lib/tipos";
import { useEstudo } from "@/lib/useEstudo";

/** O guia de estudo numa folha para imprimir ou salvar em PDF pelo navegador. */
export default function PaginaImprimirEstudo() {
  const { id } = useParams<{ id: string }>();
  const { dados } = useEstudo(id);
  const [midia, setMidia] = useState<Midia | null>(null);
  const [igreja, setIgreja] = useState("");

  useEffect(() => {
    chamarApi<Midia>(`/midias/${id}`).then(setMidia).catch(() => undefined);
    chamarApi<Identidade>("/identidade")
      .then((identidade) => setIgreja(identidade.nome_exibicao))
      .catch(() => undefined);
  }, [id]);

  const detalhes = midia ? [midia.ficha.pregador, dataDoCulto(midia.ficha.data), midia.ficha.serie ? `Série: ${midia.ficha.serie}` : ""].filter(Boolean) : [];

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 print:max-w-none print:p-0">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link href={`/app/midias/${id}?aba=estudo`} className="inline-flex items-center gap-2 text-sm text-suave hover:text-texto">
          <ArrowLeft className="size-4" aria-hidden /> Voltar ao culto
        </Link>
        <button type="button" onClick={() => window.print()} disabled={dados?.status !== "pronta"} className="botao-cta">
          <Printer className="size-4" aria-hidden /> Imprimir ou salvar em PDF
        </button>
      </div>

      <article className="rounded-2xl bg-white p-8 text-neutral-900 shadow-xl sm:p-12 print:rounded-none print:p-0 print:shadow-none">
        <header className="border-b border-neutral-200 pb-5">
          <p className="text-xs font-semibold uppercase tracking-widest text-neutral-500">{igreja || "Guia de estudo"}</p>
          <h1 className="mt-2 font-display text-3xl font-bold">{midia?.nome ?? "Carregando..."}</h1>
          {detalhes.length > 0 ? <p className="mt-1 text-sm text-neutral-600">{detalhes.join(" · ")}</p> : null}
        </header>
        <div className="mt-6">
          {dados?.status === "pronta" ? (
            <SecoesDoGuia estudo={dados} />
          ) : (
            <p className="text-sm text-neutral-600">{dados ? "O guia desta pregação ainda não está pronto." : "Carregando o guia..."}</p>
          )}
        </div>
        <footer className="mt-8 border-t border-neutral-200 pt-4 text-[11px] text-neutral-500">
          Guia preparado a partir da transcrição da pregação, com as palavras do próprio pregador. As perguntas são sugestões
          geradas por IA, revisadas pela liderança.
        </footer>
      </article>
    </main>
  );
}
