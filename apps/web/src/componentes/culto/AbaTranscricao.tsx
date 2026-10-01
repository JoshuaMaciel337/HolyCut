"use client";

import { FileText } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { BarraProgresso } from "@/componentes/BarraProgresso";
import { chamarApi, ErroApi } from "@/lib/api";
import { useEventosJobs } from "@/lib/eventos";
import { formatarTempo } from "@/lib/formatar";
import type { Job, Transcricao } from "@/lib/tipos";

/**
 * O texto da gravação, marcado como gerado por IA. O português fica como foi falado.
 */
export function AbaTranscricao({
  midiaId,
  pronta,
  temAudio,
}: {
  midiaId: string;
  pronta: boolean;
  temAudio: boolean;
}) {
  const [transcricao, setTranscricao] = useState<Transcricao | null>(null);
  const [erro, setErro] = useState("");
  const [pedindo, setPedindo] = useState(false);

  const carregar = useCallback(() => {
    chamarApi<Transcricao>(`/midias/${midiaId}/transcricao`)
      .then((dados) => {
        setTranscricao(dados);
        setErro("");
      })
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar a transcrição."));
  }, [midiaId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEventosJobs((job: Job) => {
    if (job.tipo !== "transcricao" || job.entrada?.midia_id !== midiaId) return;
    if (job.status === "concluido" || job.status === "erro") carregar();
    else {
      setTranscricao((atual) => ({
        status: job.status === "pendente" || job.status === "executando" ? job.status : "ausente",
        progresso: job.progresso,
        mensagem: job.mensagem,
        erro: job.erro,
        gerado_por_ia: atual?.gerado_por_ia ?? false,
        idioma: atual?.idioma ?? null,
        modelo: atual?.modelo ?? null,
        segmentos: atual?.segmentos ?? [],
        versiculos: atual?.versiculos ?? [],
      }));
    }
  });

  async function pedir() {
    setPedindo(true);
    setErro("");
    try {
      await chamarApi(`/midias/${midiaId}/transcricao`, { metodo: "POST" });
      carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível começar a transcrição.");
    } finally {
      setPedindo(false);
    }
  }

  if (!transcricao && !erro) {
    return <p className="text-sm text-suave">Carregando a transcrição...</p>;
  }

  const andando = transcricao?.status === "pendente" || transcricao?.status === "executando";
  const textoPronto = transcricao?.status === "pronta";
  const botao = pronta && temAudio ? (
    <button type="button" className="botao-cta mt-4 px-4 py-2 text-sm" disabled={pedindo} onClick={pedir}>
      {pedindo ? "Pedindo..." : transcricao?.status === "erro" ? "Tentar de novo" : "Transcrever esta gravação"}
    </button>
  ) : null;

  return (
    <section className="cartao p-6" aria-labelledby="titulo-transcricao">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-violeta/15">
            <FileText className="size-5 text-violeta" aria-hidden />
          </span>
          <div>
            <h2 id="titulo-transcricao" className="font-display text-lg font-bold">
              Transcrição
            </h2>
            <p className="mt-1 max-w-xl text-sm text-suave">
              O texto da pregação, no tempo da gravação. O português fica como foi falado.
            </p>
          </div>
        </div>
        {textoPronto ? (
          <div className="flex flex-wrap gap-2">
            <a className="botao-contorno px-3 py-2 text-sm" href={`/api/midias/${midiaId}/transcricao.srt`}>
              Baixar SRT
            </a>
            <a className="botao-contorno px-3 py-2 text-sm" href={`/api/midias/${midiaId}/transcricao.txt`}>
              Baixar TXT
            </a>
          </div>
        ) : null}
      </div>

      {erro ? <p className="mt-4 text-sm text-vermelho">{erro}</p> : null}

      {andando && transcricao ? (
        <div className="mt-6">
          <BarraProgresso valor={transcricao.progresso} rotulo="Progresso da transcrição" />
          <p className="mt-2 text-sm text-suave">
            {transcricao.mensagem || "Na fila"} · {transcricao.progresso}%
          </p>
        </div>
      ) : null}

      {transcricao?.status === "erro" ? (
        <div className="mt-4">
          <p className="text-sm text-vermelho">{transcricao.erro || "A transcrição falhou."}</p>
          {botao}
        </div>
      ) : null}

      {textoPronto && transcricao ? (
        <>
          <p className="mt-4 text-xs text-suave">Gerado por IA, para revisar. A fala não foi corrigida.</p>
          {transcricao.segmentos.length === 0 ? (
            <p className="mt-4 text-sm text-suave">Nenhuma fala foi encontrada nesta gravação.</p>
          ) : (
            <ol className="mt-4 flex max-h-[32rem] flex-col gap-2 overflow-y-auto" aria-label="Trechos da transcrição">
              {transcricao.segmentos.map((segmento) => (
                <li key={segmento.id} className="flex gap-3 rounded-xl border border-borda px-4 py-3">
                  <time className="w-14 shrink-0 pt-0.5 text-xs tabular-nums text-suave">
                    {formatarTempo(segmento.inicio)}
                  </time>
                  <p className="text-sm">{segmento.texto}</p>
                </li>
              ))}
            </ol>
          )}
        </>
      ) : null}

      {!andando && !textoPronto && transcricao?.status !== "erro" ? (
        <div className="mt-6">
          <p className="text-sm text-suave">
            A transcrição começa sozinha quando a gravação fica pronta. Se esta já estava no acervo, peça agora.
          </p>
          {botao}
        </div>
      ) : null}
    </section>
  );
}
