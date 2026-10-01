"use client";

import { ArrowLeft, BookOpen, CircleAlert, Clapperboard, FileText, Quote, ScrollText, Trash2, Video } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { BarraProgresso } from "@/componentes/BarraProgresso";
import { AbaGravacao } from "@/componentes/culto/AbaGravacao";
import { AbaTranscricao } from "@/componentes/culto/AbaTranscricao";
import { CapaDoCulto } from "@/componentes/culto/CapaDoCulto";
import { GuiaDeEstudo } from "@/componentes/culto/GuiaDeEstudo";
import { FichaDoCulto } from "@/componentes/culto/FichaDoCulto";
import { MomentosDoCulto } from "@/componentes/culto/MomentosDoCulto";
import { ResumoDoCulto } from "@/componentes/culto/ResumoDoCulto";
import { SugestoesDoCulto } from "@/componentes/culto/SugestoesDoCulto";
import { VersiculosDoCulto } from "@/componentes/culto/VersiculosDoCulto";
import { ListaExportacoes } from "@/componentes/ListaExportacoes";
import { ReelsDaMidia } from "@/componentes/ReelsDaMidia";
import { dataDoCulto, urlBanner } from "@/lib/acervo";
import { chamarApi, ErroApi } from "@/lib/api";
import { useEventosJobs } from "@/lib/eventos";
import { formatarTempo, porcentagem } from "@/lib/formatar";
import type { Midia } from "@/lib/tipos";

const ABAS = [
  { id: "visao", rotulo: "Visão geral" },
  { id: "cortes", rotulo: "Cortes" },
  { id: "versiculos", rotulo: "Versículos" },
  { id: "estudo", rotulo: "Estudo" },
  { id: "transcricao", rotulo: "Transcrição" },
  { id: "gravacao", rotulo: "Gravação" },
] as const;

type AbaId = (typeof ABAS)[number]["id"];

function abaValida(valor: string | null): AbaId {
  return ABAS.some((aba) => aba.id === valor) ? (valor as AbaId) : "visao";
}

function AbaCortes({ midia }: { midia: Midia }) {
  return (
    <div className="flex flex-col gap-6">
      <SugestoesDoCulto midiaId={midia.id} />
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <section className="cartao p-6" aria-labelledby="titulo-cortes-prontos">
        <h2 id="titulo-cortes-prontos" className="font-display text-lg font-bold">
          Cortes prontos
        </h2>
        <div className="mt-4">
          <ListaExportacoes
            midiaId={midia.id}
            vazio="Nenhum corte exportado ainda. Crie um Reel ou um Story e, quando estiver bom, exporte."
          />
        </div>
      </section>
      <ReelsDaMidia midia={midia} />
      </div>
    </div>
  );
}

function ConteudoDaAba({ aba, midia, aoMudar }: { aba: AbaId; midia: Midia; aoMudar: (midia: Midia) => void }) {
  switch (aba) {
    case "visao":
      return (
        <div className="flex flex-col gap-6">
          <FichaDoCulto midia={midia} aoSalvar={aoMudar} />
          <CapaDoCulto midia={midia} aoMudar={aoMudar} />
          <MomentosDoCulto midiaId={midia.id} />
          <ResumoDoCulto midiaId={midia.id} />
        </div>
      );
    case "cortes":
      return <AbaCortes midia={midia} />;
    case "versiculos":
      return <VersiculosDoCulto midiaId={midia.id} />;
    case "estudo":
      return (
        <GuiaDeEstudo midiaId={midia.id} />
      );
    case "transcricao":
      return <AbaTranscricao midiaId={midia.id} pronta={midia.status === "pronta"} temAudio={midia.audio != null} />;
    case "gravacao":
      return <AbaGravacao key={midia.id} midia={midia} aoMudar={aoMudar} />;
  }
}

function PaginaCulto() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const aba = abaValida(useSearchParams().get("aba"));
  const [midia, setMidia] = useState<Midia | null>(null);
  const [erro, setErro] = useState("");

  const carregar = useCallback(() => {
    chamarApi<Midia>(`/midias/${id}`)
      .then(setMidia)
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar o culto."));
  }, [id]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEventosJobs((job) => {
    const midiaId = job.entrada?.midia_id;
    if (typeof midiaId !== "string" || midiaId !== id) return;
    if (job.tipo === "ingestao") {
      setMidia((atual) =>
        atual ? { ...atual, processamento: { status: job.status, progresso: job.progresso, mensagem: job.mensagem } } : atual,
      );
      if (job.status === "concluido" || job.status === "erro") carregar();
    }
    if (job.tipo === "capas_culto" && job.status === "concluido") carregar();
  });

  async function excluir() {
    if (!midia || !window.confirm(`Excluir "${midia.nome}"? A gravação e tudo o que foi gerado a partir dela serão apagados.`)) return;
    try {
      await chamarApi(`/midias/${id}`, { metodo: "DELETE" });
      router.replace("/app/acervo");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível excluir.");
    }
  }

  const voltar = (
    <Link href="/app/acervo" className="inline-flex items-center gap-2 text-sm text-suave hover:text-texto">
      <ArrowLeft className="size-4" aria-hidden /> Acervo
    </Link>
  );

  if (!midia) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        {voltar}
        <p className="mt-6 text-suave">{erro || "Carregando..."}</p>
      </main>
    );
  }

  const pronta = midia.status === "pronta";
  const detalhes = [midia.ficha.pregador, dataDoCulto(midia.ficha.data), formatarTempo(midia.duracao)].filter(
    (parte) => parte && parte !== "--:--",
  );

  let preparacao: React.ReactNode = null;
  if (midia.status === "processando") {
    const progresso = midia.processamento?.progresso ?? 0;
    preparacao = (
      <section className="cartao flex flex-col gap-3 p-6">
        <h2 className="font-display text-lg font-bold">Preparando a gravação</h2>
        <BarraProgresso valor={progresso} rotulo="Preparação" />
        <p className="text-sm text-suave">
          {midia.processamento?.mensagem || "Na fila"} · {progresso}%
        </p>
      </section>
    );
  } else if (midia.status === "enviando") {
    preparacao = (
      <section className="cartao p-6 text-suave">
        O envio parou em {porcentagem(midia.bytes_recebidos, midia.tamanho_total)}%. Volte ao Início e escolha o mesmo arquivo
        de novo para continuar de onde parou.
      </section>
    );
  } else if (midia.status === "erro") {
    preparacao = (
      <section className="cartao flex gap-2 p-6 text-vermelho">
        <CircleAlert className="mt-0.5 size-5 shrink-0" aria-hidden />
        {midia.erro || "Não foi possível preparar esta gravação."}
      </section>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      {voltar}
      {erro ? (
        <p role="alert" className="mt-4 rounded-xl border border-vermelho/40 bg-vermelho/10 px-4 py-3 text-sm text-vermelho">
          {erro}
        </p>
      ) : null}

      {pronta ? (
        <div className="mt-4 overflow-hidden rounded-3xl border border-borda bg-surface">
          <div className="relative aspect-[16/9] w-full">
            {midia.capa_versao ? (
              <Image
                src={urlBanner(midia.id, midia.capa_versao)}
                alt=""
                fill
                unoptimized
                priority
                sizes="(min-width: 1152px) 1152px, 100vw"
                className="object-cover"
              />
            ) : (
              <div className="absolute inset-0 bg-gradient-to-br from-violeta/40 via-ink to-laranja/20" />
            )}
          </div>
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          {midia.ficha.serie ? (
            <p className="text-xs font-semibold uppercase tracking-wider text-laranja">Série: {midia.ficha.serie}</p>
          ) : null}
          <h1 className="font-display text-2xl font-bold sm:text-3xl">{midia.nome}</h1>
          {detalhes.length > 0 ? <p className="mt-1 text-sm text-suave">{detalhes.join(" · ")}</p> : null}
        </div>
        <button type="button" onClick={excluir} className="botao-contorno px-4 py-2 text-sm">
          <Trash2 className="size-4" aria-hidden /> Excluir
        </button>
      </div>

      {preparacao}

      {pronta ? (
        <>
          <nav aria-label="Seções do culto" className="mt-6 -mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <ul className="flex min-w-max gap-1 border-b border-borda">
              {ABAS.map((item) => {
                const atual = item.id === aba;
                return (
                  <li key={item.id}>
                    <Link
                      href={`/app/midias/${id}?aba=${item.id}`}
                      scroll={false}
                      aria-current={atual ? "page" : undefined}
                      className={`inline-flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition sm:px-4 ${
                        atual ? "border-b-2 border-laranja text-texto" : "border-b-2 border-transparent text-suave hover:text-texto"
                      }`}
                    >
                      {item.id === "visao" ? <BookOpen className="size-4" aria-hidden /> : null}
                      {item.id === "cortes" ? <Clapperboard className="size-4" aria-hidden /> : null}
                      {item.id === "versiculos" ? <Quote className="size-4" aria-hidden /> : null}
                      {item.id === "estudo" ? <ScrollText className="size-4" aria-hidden /> : null}
                      {item.id === "transcricao" ? <FileText className="size-4" aria-hidden /> : null}
                      {item.id === "gravacao" ? <Video className="size-4" aria-hidden /> : null}
                      {item.rotulo}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
          <div className="mt-6">
            <ConteudoDaAba aba={aba} midia={midia} aoMudar={setMidia} />
          </div>
        </>
      ) : null}
    </main>
  );
}

export default function PaginaMidia() {
  return (
    <Suspense fallback={<main className="mx-auto max-w-6xl px-4 py-10 text-suave sm:px-6">Carregando o culto...</main>}>
      <PaginaCulto />
    </Suspense>
  );
}
