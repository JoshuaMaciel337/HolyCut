"use client";

import { CircleAlert, Download, Share2, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { BarraProgresso } from "@/componentes/BarraProgresso";
import { chamarApi, ErroApi } from "@/lib/api";
import { useEventosJobs } from "@/lib/eventos";
import { formatarBytes, formatarData, formatarTempo } from "@/lib/formatar";
import type { Exportacao } from "@/lib/tipos";

function podeCompartilharArquivos(): boolean {
  if (typeof navigator === "undefined" || !navigator.canShare) return false;
  try {
    return navigator.canShare({ files: [new File([""], "teste.mp4", { type: "video/mp4" })] });
  } catch {
    return false;
  }
}

function nomeDoArquivo(nome: string): string {
  const base = nome
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60);
  return `${base || "holycut"}.mp4`;
}

/** Vídeos exportados de um projeto, com progresso ao vivo, download e compartilhamento pelo celular. */
export function ListaExportacoes({ projetoId, nova }: { projetoId: string; nova: Exportacao | null }) {
  const [exportacoes, setExportacoes] = useState<Exportacao[] | null>(null);
  const [erro, setErro] = useState("");
  const [compartilhar] = useState(podeCompartilharArquivos);

  const carregar = useCallback(() => {
    chamarApi<Exportacao[]>(`/exportacoes?projeto_id=${projetoId}`)
      .then(setExportacoes)
      .catch(() => setErro("Não foi possível carregar os vídeos exportados."));
  }, [projetoId]);

  useEffect(() => {
    carregar();
  }, [carregar, nova]);

  const atualizar = useCallback((id: string) => {
    chamarApi<Exportacao>(`/exportacoes/${id}`)
      .then((atual) => setExportacoes((lista) => lista?.map((e) => (e.id === id ? atual : e)) ?? lista))
      .catch(() => undefined);
  }, []);

  useEventosJobs((job) => {
    const id = job.entrada?.exportacao_id;
    if (job.tipo !== "renderizacao" || typeof id !== "string") return;
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
    if (!window.confirm("Excluir este vídeo exportado?")) return;
    try {
      await chamarApi(`/exportacoes/${exportacao.id}`, { metodo: "DELETE" });
      setExportacoes((lista) => lista?.filter((e) => e.id !== exportacao.id) ?? lista);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível excluir.");
    }
  }

  async function enviarPeloCelular(exportacao: Exportacao) {
    try {
      const resposta = await fetch(`/api/exportacoes/${exportacao.id}/arquivos/video.mp4`, { credentials: "same-origin" });
      const arquivo = new File([await resposta.blob()], nomeDoArquivo(exportacao.nome), { type: "video/mp4" });
      await navigator.share({ files: [arquivo], title: exportacao.nome });
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError")) setErro("Não foi possível compartilhar. Use o botão Baixar.");
    }
  }

  if (exportacoes === null) return <p className="text-sm text-suave">{erro || "Carregando..."}</p>;
  if (exportacoes.length === 0) {
    return <p className="text-sm text-suave">Nenhum vídeo exportado ainda. Quando estiver bom, clique em Exportar.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {erro ? <p className="text-sm text-vermelho">{erro}</p> : null}
      <ul className="grid gap-4 sm:grid-cols-2">
        {exportacoes.map((exportacao) => {
          const base = `/api/exportacoes/${exportacao.id}/arquivos`;
          return (
            <li key={exportacao.id} className="flex flex-col gap-3 rounded-2xl border border-borda bg-surface-2/60 p-3">
              {exportacao.status === "pronta" ? (
                <video
                  src={`${base}/video.mp4`}
                  poster={exportacao.arquivos.includes("capa.jpg") ? `${base}/capa.jpg` : undefined}
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
                  <a href={`${base}/video.mp4?baixar=true`} className="botao-cta flex-1 px-3 py-2 text-sm">
                    <Download className="size-4" aria-hidden /> Baixar
                  </a>
                  {compartilhar ? (
                    <button type="button" onClick={() => enviarPeloCelular(exportacao)} className="botao-contorno flex-1 px-3 py-2 text-sm">
                      <Share2 className="size-4" aria-hidden /> Compartilhar
                    </button>
                  ) : null}
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
