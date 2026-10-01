"use client";

import { CircleAlert, Download, ImagePlus, Share2, Trash2 } from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useRef, useState } from "react";

import { AprovacaoDoVideo } from "@/componentes/AprovacaoDoVideo";
import { BarraProgresso } from "@/componentes/BarraProgresso";
import { QrDoCelular } from "@/componentes/QrDoCelular";
import { chamarApi, ErroApi } from "@/lib/api";
import { useEventosJobs } from "@/lib/eventos";
import { formatarBytes, formatarData, formatarTempo } from "@/lib/formatar";
import type { Aprovacao, Exportacao } from "@/lib/tipos";

// Enquanto alguém ainda vai responder um pedido de aprovação, a lista confere de tempos em tempos
const INTERVALO_APROVACAO_MS = 15000;

function podeCompartilharArquivos(): boolean {
  if (typeof navigator === "undefined" || !navigator.canShare) return false;
  try {
    return navigator.canShare({ files: [new File([""], "teste.mp4", { type: "video/mp4" })] });
  } catch {
    return false;
  }
}

function nomeDoArquivo(nome: string, extensao = ".mp4"): string {
  const base = nome
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60);
  return `${base || "holycut"}${extensao}`;
}

/** Vídeos exportados de um projeto, com progresso ao vivo, download e compartilhamento pelo celular. */
export function ListaExportacoes({
  projetoId,
  midiaId,
  nova = null,
  vazio,
}: {
  projetoId?: string;
  midiaId?: string;
  nova?: Exportacao | null;
  vazio?: string;
}) {
  const [exportacoes, setExportacoes] = useState<Exportacao[] | null>(null);
  const [erro, setErro] = useState("");
  const [compartilhar] = useState(podeCompartilharArquivos);
  const [avisoCapa, setAvisoCapa] = useState<Record<string, string>>({});
  const players = useRef<Record<string, HTMLVideoElement | null>>({});

  const carregar = useCallback(() => {
    // De um projeto (no editor) ou de todos os projetos de um culto (na página do culto)
    const filtro = projetoId ? `projeto_id=${projetoId}` : `midia_id=${midiaId}`;
    chamarApi<Exportacao[]>(`/exportacoes?${filtro}&limite=60`)
      .then(setExportacoes)
      .catch(() => setErro("Não foi possível carregar os vídeos exportados."));
  }, [projetoId, midiaId]);

  useEffect(() => {
    carregar();
  }, [carregar, nova]);

  const atualizar = useCallback((id: string) => {
    chamarApi<Exportacao>(`/exportacoes/${id}`)
      .then((atual) => setExportacoes((lista) => lista?.map((e) => (e.id === id ? atual : e)) ?? lista))
      .catch(() => undefined);
  }, []);

  const aguardandoResposta = exportacoes?.some((e) => e.aprovacao?.status === "pendente" && !e.aprovacao.expirada) ?? false;
  useEffect(() => {
    if (!aguardandoResposta) return;
    const intervalo = setInterval(carregar, INTERVALO_APROVACAO_MS);
    return () => clearInterval(intervalo);
  }, [aguardandoResposta, carregar]);

  function mudarAprovacao(id: string, aprovacao: Aprovacao | null) {
    setExportacoes((lista) => lista?.map((e) => (e.id === id ? { ...e, aprovacao } : e)) ?? lista);
  }

  useEventosJobs((job) => {
    const id = job.entrada?.exportacao_id;
    if (typeof id !== "string") return;
    if (job.tipo === "capa_exportacao") {
      if (job.status === "concluido") {
        atualizar(id);
        setAvisoCapa((avisos) => ({ ...avisos, [id]: "Capa trocada." }));
      }
      return;
    }
    if (job.tipo !== "renderizacao" && job.tipo !== "renderizacao_nvenc") return;
    setExportacoes(
      (lista) =>
        lista?.map((e) =>
          e.id === id && e.status === "processando"
            ? { ...e, processamento: { status: job.status, progresso: job.progresso, mensagem: job.mensagem } }
            : e,
        ) ?? lista,
    );
    if (job.status === "concluido" || job.status === "erro") atualizar(id);
  });

  async function excluir(exportacao: Exportacao) {
    if (!window.confirm(exportacao.formato === "imagem" ? "Excluir esta imagem exportada?" : "Excluir este vídeo exportado?")) return;
    try {
      await chamarApi(`/exportacoes/${exportacao.id}`, { metodo: "DELETE" });
      setExportacoes((lista) => lista?.filter((e) => e.id !== exportacao.id) ?? lista);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível excluir.");
    }
  }

  async function usarQuadroNaCapa(exportacao: Exportacao) {
    const instante = Math.round((players.current[exportacao.id]?.currentTime ?? 0) * 100) / 100;
    try {
      await chamarApi(`/exportacoes/${exportacao.id}/capa`, { metodo: "POST", corpo: { instante } });
      setAvisoCapa((avisos) => ({ ...avisos, [exportacao.id]: `A capa vai ser o quadro de ${formatarTempo(instante)}. Leva alguns segundos.` }));
    } catch (e) {
      setAvisoCapa((avisos) => ({ ...avisos, [exportacao.id]: e instanceof ErroApi ? e.message : "Não foi possível trocar a capa." }));
    }
  }

  async function enviarPeloCelular(exportacao: Exportacao) {
    try {
      const imagem = exportacao.formato === "imagem";
      const resposta = await fetch(`/api/exportacoes/${exportacao.id}/arquivos/${imagem ? "imagem.jpg" : "video.mp4"}`, {
        credentials: "same-origin",
      });
      const arquivo = new File([await resposta.blob()], nomeDoArquivo(exportacao.nome, imagem ? ".jpg" : ".mp4"), {
        type: imagem ? "image/jpeg" : "video/mp4",
      });
      await navigator.share({ files: [arquivo], title: exportacao.nome });
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError")) setErro("Não foi possível compartilhar. Use o botão Baixar.");
    }
  }

  if (exportacoes === null) return <p className="text-sm text-suave">{erro || "Carregando..."}</p>;
  if (exportacoes.length === 0) {
    return <p className="text-sm text-suave">{vazio ?? "Nada exportado ainda. Quando estiver bom, exporte o vídeo ou a imagem."}</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {erro ? <p className="text-sm text-vermelho">{erro}</p> : null}
      <ul className="grid gap-4 sm:grid-cols-2">
        {exportacoes.map((exportacao) => {
          const base = `/api/exportacoes/${exportacao.id}/arquivos`;
          const imagem = exportacao.formato === "imagem";
          const arquivoPrincipal = imagem ? "imagem.jpg" : "video.mp4";
          return (
            <li key={exportacao.id} className="flex flex-col gap-3 rounded-2xl border border-borda bg-surface-2/60 p-3">
              {exportacao.status === "pronta" && imagem ? (
                <Image
                  src={`${base}/imagem.jpg`}
                  alt={`Imagem exportada de ${exportacao.nome}`}
                  width={exportacao.largura}
                  height={exportacao.altura}
                  unoptimized
                  className="mx-auto h-auto max-h-80 w-auto rounded-xl bg-black"
                />
              ) : exportacao.status === "pronta" ? (
                <video
                  ref={(elemento) => {
                    players.current[exportacao.id] = elemento;
                  }}
                  src={`${base}/video.mp4`}
                  poster={exportacao.arquivos.includes("capa.jpg") ? `${base}/capa.jpg?v=${exportacao.capa_versao}` : undefined}
                  controls
                  playsInline
                  preload="none"
                  className="mx-auto max-h-80 rounded-xl bg-black"
                  style={{ aspectRatio: `${exportacao.largura} / ${exportacao.altura}` }}
                />
              ) : exportacao.status === "processando" ? (
                <div className="flex flex-col gap-2 py-4">
                  <BarraProgresso valor={exportacao.processamento?.progresso ?? 0} rotulo="Exportação" />
                  <p className="text-sm text-suave">
                    {exportacao.processamento?.mensagem || "Na fila"} · {exportacao.processamento?.progresso ?? 0}%
                  </p>
                </div>
              ) : (
                <p className="flex gap-1.5 py-4 text-sm text-vermelho">
                  <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
                  {exportacao.erro || "A exportação falhou."}
                </p>
              )}
              <div className="flex items-center justify-between gap-2 text-xs text-suave">
                <span>
                  {imagem ? "Imagem · " : "Vídeo · "}
                  {formatarData(exportacao.criado_em)}
                  {exportacao.duracao ? ` · ${formatarTempo(exportacao.duracao)}` : ""}
                  {exportacao.tamanho ? ` · ${formatarBytes(exportacao.tamanho)}` : ""}
                </span>
                <button type="button" onClick={() => excluir(exportacao)} aria-label="Excluir vídeo" className="hover:text-texto">
                  <Trash2 className="size-4" aria-hidden />
                </button>
              </div>
              {exportacao.status === "pronta" ? (
                <div className="flex gap-2">
                  <a href={`${base}/${arquivoPrincipal}?baixar=true`} className="botao-cta flex-1 px-3 py-2 text-sm">
                    <Download className="size-4" aria-hidden /> Baixar
                  </a>
                  {compartilhar ? (
                    <button type="button" onClick={() => enviarPeloCelular(exportacao)} className="botao-contorno flex-1 px-3 py-2 text-sm">
                      <Share2 className="size-4" aria-hidden /> Compartilhar
                    </button>
                  ) : null}
                </div>
              ) : null}
              {exportacao.status === "pronta" && !imagem ? (
                <div className="flex flex-col gap-2">
                  <QrDoCelular exportacaoId={exportacao.id} />
                  <button
                    type="button"
                    onClick={() => usarQuadroNaCapa(exportacao)}
                    className="inline-flex items-center gap-1.5 self-start text-xs text-suave hover:text-texto"
                    title="Pause o vídeo no quadro que você quer e clique"
                  >
                    <ImagePlus className="size-3.5" aria-hidden /> Usar o quadro do player como capa
                  </button>
                  {avisoCapa[exportacao.id] ? <p className="text-xs text-ciano">{avisoCapa[exportacao.id]}</p> : null}
                </div>
              ) : null}
              {exportacao.status === "pronta" ? (
                <AprovacaoDoVideo exportacao={exportacao} aoMudar={(aprovacao) => mudarAprovacao(exportacao.id, aprovacao)} />
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
