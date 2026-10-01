"use client";

import { Quote } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { chamarApi, ErroApi } from "@/lib/api";
import { useEventosJobs } from "@/lib/eventos";
import { formatarTempo } from "@/lib/formatar";
import type { Transcricao } from "@/lib/tipos";

export function VersiculosDoCulto({ midiaId }: { midiaId: string }) {
  const [dados, setDados] = useState<Transcricao | null>(null);
  const [erro, setErro] = useState("");

  const carregar = useCallback(() => {
    chamarApi<Transcricao>(`/midias/${midiaId}/transcricao`)
      .then(setDados)
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar os versículos."));
  }, [midiaId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEventosJobs((job) => {
    if (job.tipo === "transcricao" && job.entrada.midia_id === midiaId) carregar();
  });

  const andando = dados?.status === "pendente" || dados?.status === "executando";
  const versiculos = dados?.versiculos ?? [];

  return (
    <section className="cartao p-6" aria-labelledby="titulo-versiculos">
      <h2 id="titulo-versiculos" className="flex items-center gap-2 font-display text-lg font-bold">
        <Quote className="size-5 text-ciano" aria-hidden /> Versículos da pregação
      </h2>
      <p className="mt-2 text-sm text-suave">
        Só entra a referência que dá para ler na fala: livro, capítulo e versículo. O texto é o que foi dito, não uma tradução da Bíblia.
      </p>
      {erro ? <p className="mt-3 text-sm text-vermelho" role="alert">{erro}</p> : null}
      {andando ? (
        <p className="mt-4 text-sm text-suave" role="status">{dados?.mensagem || "Na fila"} · {dados?.progresso ?? 0}%</p>
      ) : null}
      {dados?.status === "pronta" && versiculos.length === 0 ? (
        <p className="mt-4 text-sm text-suave">Nenhuma referência completa apareceu nesta transcrição.</p>
      ) : null}
      {dados?.status === "ausente" ? (
        <p className="mt-4 text-sm text-suave">Os versículos aparecem quando a transcrição fica pronta.</p>
      ) : null}
      {versiculos.length > 0 ? (
        <ul className="mt-4 flex flex-col gap-3">
          {versiculos.map((item) => (
            <li key={`${item.referencia}-${item.inicio}`} className="rounded-xl border border-borda p-4">
              <p className="font-medium">{item.referencia}</p>
              <p className="mt-1 text-sm text-suave">{item.citacao}</p>
              <p className="mt-2 text-xs tabular-nums text-suave">{formatarTempo(item.inicio)}</p>
            </li>
          ))}
        </ul>
      ) : null}
      {dados?.gerado_por_ia ? <p className="mt-4 text-xs text-suave">Gerado por IA. Revise a referência.</p> : null}
    </section>
  );
}
