"use client";

import { ArrowLeft, Check, CircleAlert, Clapperboard, Pencil, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { BarraProgresso } from "@/componentes/BarraProgresso";
import { FaixaDeMiniaturas } from "@/componentes/FaixaDeMiniaturas";
import { FormaDeOnda } from "@/componentes/FormaDeOnda";
import { chamarApi, ErroApi } from "@/lib/api";
import { useEventosJobs } from "@/lib/eventos";
import { formatarBytes, formatarData, formatarTempo, porcentagem } from "@/lib/formatar";
import type { FormaDeOnda as DadosFormaDeOnda, Midia } from "@/lib/tipos";

function Informacao({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-borda py-2.5 text-sm last:border-0">
      <dt className="text-suave">{rotulo}</dt>
      <dd className="text-right font-medium">{valor}</dd>
    </div>
  );
}

function TituloEditavel({ midia, aoSalvar }: { midia: Midia; aoSalvar: (nome: string) => Promise<void> }) {
  const [editando, setEditando] = useState(false);
  const [salvando, setSalvando] = useState(false);

  async function salvar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const nome = String(new FormData(evento.currentTarget).get("nome") ?? "").trim();
    if (!nome || nome === midia.nome) {
      setEditando(false);
      return;
    }
    setSalvando(true);
    await aoSalvar(nome);
    setSalvando(false);
    setEditando(false);
  }

  if (!editando) {
    return (
      <div className="flex min-w-0 items-center gap-2">
        <h1 className="truncate font-display text-2xl font-bold sm:text-3xl">{midia.nome}</h1>
        <button type="button" onClick={() => setEditando(true)} aria-label="Renomear" title="Renomear" className="shrink-0 text-suave hover:text-texto">
          <Pencil className="size-4" aria-hidden />
        </button>
      </div>
    );
  }
  return (
    <form onSubmit={salvar} className="flex min-w-0 flex-1 items-center gap-2">
      <input
        name="nome"
        defaultValue={midia.nome}
        maxLength={120}
        autoFocus
        aria-label="Nome da gravação"
        className="min-w-0 flex-1 rounded-xl border border-borda bg-ink px-3 py-2 font-display text-xl font-bold outline-none focus:border-violeta"
      />
      <button type="submit" disabled={salvando} aria-label="Salvar nome" className="botao-cta size-10 p-0">
        <Check className="size-4" aria-hidden />
      </button>
      <button type="button" onClick={() => setEditando(false)} aria-label="Cancelar" className="botao-contorno size-10 p-0">
        <X className="size-4" aria-hidden />
      </button>
    </form>
  );
}

export default function PaginaMidia() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [midia, setMidia] = useState<Midia | null>(null);
  const [forma, setForma] = useState<DadosFormaDeOnda | null>(null);
  const [erro, setErro] = useState("");
  const [tempo, setTempo] = useState(0);
  const player = useRef<HTMLVideoElement & HTMLAudioElement>(null);

  const carregar = useCallback(() => {
    chamarApi<Midia>(`/midias/${id}`)
      .then(setMidia)
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar a gravação."));
  }, [id]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const temForma = midia?.arquivos.includes("forma_de_onda.json") ?? false;
  useEffect(() => {
    if (!temForma) return;
    let cancelado = false;
    fetch(`/api/midias/${id}/arquivos/forma_de_onda.json`, { credentials: "same-origin" })
      .then((resposta) => (resposta.ok ? resposta.json() : null))
      .then((dados) => {
        if (!cancelado && dados) setForma(dados);
      })
      .catch(() => undefined);
    return () => {
      cancelado = true;
    };
  }, [id, temForma]);

  useEventosJobs((job) => {
    if (job.tipo !== "ingestao" || job.entrada?.midia_id !== id) return;
    setMidia((atual) =>
      atual ? { ...atual, processamento: { status: job.status, progresso: job.progresso, mensagem: job.mensagem } } : atual,
    );
    if (job.status === "concluido" || job.status === "erro") carregar();
  });

  // Enquanto toca, acompanha o tempo a cada quadro para a forma de onda andar sem saltos
  useEffect(() => {
    const elemento = player.current;
    if (!elemento) return;
    let quadro = 0;
    const acompanhar = () => {
      setTempo(elemento.currentTime);
      if (!elemento.paused) quadro = requestAnimationFrame(acompanhar);
    };
    const tocar = () => {
      cancelAnimationFrame(quadro);
      quadro = requestAnimationFrame(acompanhar);
    };
    const atualizar = () => setTempo(elemento.currentTime);
    elemento.addEventListener("play", tocar);
    elemento.addEventListener("seeked", atualizar);
    elemento.addEventListener("pause", atualizar);
    return () => {
      cancelAnimationFrame(quadro);
      elemento.removeEventListener("play", tocar);
      elemento.removeEventListener("seeked", atualizar);
      elemento.removeEventListener("pause", atualizar);
    };
  }, [midia?.status]);

  function buscar(segundos: number) {
    if (player.current) player.current.currentTime = segundos;
    setTempo(segundos);
  }

  async function renomear(nome: string) {
    try {
      setMidia(await chamarApi<Midia>(`/midias/${id}`, { metodo: "PATCH", corpo: { nome } }));
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível renomear.");
    }
  }

  async function excluir() {
    if (!midia || !window.confirm(`Excluir "${midia.nome}"? A gravação e tudo o que foi gerado a partir dela serão apagados.`)) return;
    try {
      await chamarApi(`/midias/${id}`, { metodo: "DELETE" });
      router.replace("/app");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível excluir.");
    }
  }

  const voltar = (
    <Link href="/app" className="inline-flex items-center gap-2 text-sm text-suave hover:text-texto">
      <ArrowLeft className="size-4" aria-hidden /> Início
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

  const video = midia.video;
  const emPe = video ? video.altura > video.largura : false;
  const base = `/api/midias/${midia.id}/arquivos`;

  let conteudo: React.ReactNode;
  if (midia.status === "pronta") {
    conteudo = (
      <section className="cartao flex flex-col gap-4 p-4 sm:p-6" aria-label="Prévia">
        {video ? (
          <video
            ref={player}
            src={`${base}/proxy.mp4`}
            poster={midia.arquivos.includes("capa.jpg") ? `${base}/capa.jpg` : undefined}
            controls
            playsInline
            preload="metadata"
            className={`mx-auto w-full rounded-xl bg-black ${emPe ? "max-h-[70vh] w-auto" : ""}`}
            style={{ aspectRatio: `${video.largura} / ${video.altura}` }}
          />
        ) : (
          <audio ref={player} src={`${base}/proxy.m4a`} controls preload="metadata" className="w-full" />
        )}
        {forma && midia.duracao ? (
          <div>
            <FormaDeOnda picos={forma.picos} duracao={midia.duracao} tempo={tempo} aoBuscar={buscar} />
            <p className="mt-2 text-right text-xs tabular-nums text-suave">
              {formatarTempo(tempo)} / {formatarTempo(midia.duracao)}
            </p>
          </div>
        ) : null}
        {midia.miniaturas && midia.arquivos.includes("miniaturas.jpg") ? (
          <FaixaDeMiniaturas midiaId={midia.id} miniaturas={midia.miniaturas} tempo={tempo} aoBuscar={buscar} />
        ) : null}
      </section>
    );
  } else if (midia.status === "processando") {
    const progresso = midia.processamento?.progresso ?? 0;
    conteudo = (
      <section className="cartao flex flex-col gap-3 p-6">
        <h2 className="font-display text-lg font-bold">Preparando a gravação</h2>
        <BarraProgresso valor={progresso} rotulo="Preparação" />
        <p className="text-sm text-suave">
          {midia.processamento?.mensagem || "Na fila"} · {progresso}%
        </p>
      </section>
    );
  } else if (midia.status === "enviando") {
    conteudo = (
      <section className="cartao p-6 text-suave">
        O envio parou em {porcentagem(midia.bytes_recebidos, midia.tamanho_total)}%. Volte ao Início e escolha o mesmo arquivo
        de novo para continuar de onde parou.
      </section>
    );
  } else {
    conteudo = (
      <section className="cartao flex gap-2 p-6 text-vermelho">
        <CircleAlert className="mt-0.5 size-5 shrink-0" aria-hidden />
        {midia.erro || "Não foi possível preparar esta gravação."}
      </section>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      {voltar}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
        <TituloEditavel midia={midia} aoSalvar={renomear} />
        <button type="button" onClick={excluir} className="botao-contorno px-4 py-2 text-sm">
          <Trash2 className="size-4" aria-hidden /> Excluir
        </button>
      </div>
      {erro ? (
        <p role="alert" className="mt-4 rounded-xl border border-vermelho/40 bg-vermelho/10 px-4 py-3 text-sm text-vermelho">
          {erro}
        </p>
      ) : null}

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="min-w-0">{conteudo}</div>
        <aside className="flex flex-col gap-6">
          <section className="cartao p-6" aria-labelledby="titulo-info">
            <h2 id="titulo-info" className="font-display text-lg font-bold">
              Detalhes
            </h2>
            <dl className="mt-3">
              <Informacao rotulo="Duração" valor={formatarTempo(midia.duracao)} />
              {video ? (
                <>
                  <Informacao rotulo="Resolução" valor={`${video.largura} × ${video.altura}`} />
                  <Informacao rotulo="Quadros por segundo" valor={video.fps ? String(Math.round(video.fps * 100) / 100) : "—"} />
                </>
              ) : null}
              {midia.audio ? (
                <Informacao rotulo="Áudio" valor={`${midia.audio.canais === 1 ? "Mono" : "Estéreo"} · ${Math.round(midia.audio.taxa / 1000)} kHz`} />
              ) : null}
              <Informacao rotulo="Tamanho" valor={formatarBytes(midia.tamanho_total)} />
              <Informacao rotulo="Enviada em" valor={midia.enviado_em ? formatarData(midia.enviado_em) : "—"} />
              <Informacao rotulo="Arquivo" valor={midia.nome_original} />
            </dl>
          </section>
          <section className="cartao p-6" aria-labelledby="titulo-proximos">
            <h2 id="titulo-proximos" className="font-display text-lg font-bold">
              Próximos passos
            </h2>
            <p className="mt-2 text-sm text-suave">
              Em breve: cortar os silêncios, escolher o trecho e exportar em 9:16 com legenda.
            </p>
            <button type="button" disabled className="botao-cta mt-4 w-full">
              <Clapperboard className="size-4" aria-hidden /> Criar um Reel
            </button>
          </section>
        </aside>
      </div>
    </main>
  );
}
