"use client";

import { LoaderCircle, Search, Upload } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { CartazCulto } from "@/componentes/acervo/CartazCulto";
import { DestaqueCulto } from "@/componentes/acervo/DestaqueCulto";
import { FileiraDeCultos } from "@/componentes/acervo/FileiraDeCultos";
import { normalizarBusca } from "@/lib/acervo";
import { chamarApi, ErroApi } from "@/lib/api";
import { useEventosJobs } from "@/lib/eventos";
import type { Acervo, CultoResumo } from "@/lib/tipos";

/** A biblioteca dos cultos da igreja, no estilo de um streaming. */
export default function PaginaAcervo() {
  const [acervo, setAcervo] = useState<Acervo | null>(null);
  const [busca, setBusca] = useState("");
  const [erro, setErro] = useState("");

  const carregar = useCallback(() => {
    chamarApi<Acervo>("/acervo")
      .then(setAcervo)
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível abrir o acervo."));
  }, []);
  useEffect(() => {
    carregar();
  }, [carregar]);

  // Um culto que termina de ser preparado, ou capas redesenhadas, aparecem sem recarregar a página
  useEventosJobs((job) => {
    if ((job.tipo === "ingestao" || job.tipo === "capas_culto") && job.status === "concluido") carregar();
  });

  const porId = useMemo(() => new Map((acervo?.cultos ?? []).map((culto) => [culto.id, culto])), [acervo]);
  const resultados = useMemo(() => {
    const termo = normalizarBusca(busca);
    if (!termo || !acervo) return null;
    return acervo.cultos.filter((culto) =>
      normalizarBusca([culto.titulo, culto.pregador, culto.serie, culto.descricao].join(" ")).includes(termo),
    );
  }, [acervo, busca]);

  if (!acervo) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <p className={erro ? "text-vermelho" : "inline-flex items-center gap-2 text-suave"}>
          {erro || (
            <>
              <LoaderCircle className="size-4 animate-spin" aria-hidden /> Abrindo o acervo...
            </>
          )}
        </p>
      </main>
    );
  }

  const destaque = acervo.destaque ? porId.get(acervo.destaque) : undefined;
  const fileira = (ids: string[]) => ids.map((id) => porId.get(id)).filter((culto): culto is CultoResumo => Boolean(culto));

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Acervo</h1>
          <p className="mt-1 text-sm text-suave">
            {acervo.cultos.length} {acervo.cultos.length === 1 ? "culto" : "cultos"} da igreja
            {acervo.preparando > 0 ? ` · ${acervo.preparando} chegando` : ""}
          </p>
        </div>
        <label className="flex w-full items-center gap-2 rounded-full border border-borda bg-ink px-4 py-2.5 focus-within:border-violeta sm:w-80">
          <Search className="size-4 shrink-0 text-suave" aria-hidden />
          <input
            type="search"
            value={busca}
            onChange={(evento) => setBusca(evento.target.value)}
            placeholder="Buscar por título, pregador ou série"
            aria-label="Buscar no acervo"
            className="w-full bg-transparent text-sm outline-none placeholder:text-suave/70"
          />
        </label>
      </div>

      {acervo.cultos.length === 0 ? (
        <section className="rounded-3xl border border-dashed border-borda px-6 py-14 text-center">
          <p className="font-display text-xl font-bold">O acervo ainda está vazio</p>
          <p className="mx-auto mt-2 max-w-md text-sm text-suave">
            Cada culto enviado vira uma capa aqui, com os cortes, os versículos e o estudo da mensagem.
          </p>
          <Link href="/app" className="botao-cta mt-5 inline-flex">
            <Upload className="size-4" aria-hidden /> Enviar a gravação de um culto
          </Link>
        </section>
      ) : resultados ? (
        <section aria-label="Resultado da busca">
          <p className="text-sm text-suave">
            {resultados.length === 0 ? "Nenhum culto encontrado." : `${resultados.length} ${resultados.length === 1 ? "culto" : "cultos"}`}
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            {resultados.map((culto) => (
              <CartazCulto key={culto.id} culto={culto} />
            ))}
          </div>
        </section>
      ) : (
        <>
          {destaque ? <DestaqueCulto culto={destaque} /> : null}
          {acervo.fileiras.map((item) => (
            <FileiraDeCultos key={item.id} titulo={item.titulo} cultos={fileira(item.ids)} />
          ))}
        </>
      )}
    </main>
  );
}
