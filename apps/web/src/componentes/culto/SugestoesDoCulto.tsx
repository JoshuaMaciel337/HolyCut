"use client";

import { Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { chamarApi, ErroApi } from "@/lib/api";
import { useEventosJobs } from "@/lib/eventos";
import { formatarTempo } from "@/lib/formatar";
import type { Job, Projeto, Sugestoes } from "@/lib/tipos";

export function SugestoesDoCulto({ midiaId }: { midiaId: string }) {
  const router = useRouter();
  const [dados, setDados] = useState<Sugestoes | null>(null);
  const [erro, setErro] = useState("");
  const [abrindo, setAbrindo] = useState("");

  const carregar = useCallback(() => {
    chamarApi<Sugestoes>(`/midias/${midiaId}/sugestoes`)
      .then(setDados)
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar os cortes."));
  }, [midiaId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEventosJobs((job) => {
    if (job.tipo === "sugestao_cortes" && job.entrada.midia_id === midiaId) carregar();
  });

  async function pedir() {
    setErro("");
    try {
      await chamarApi<Job>(`/midias/${midiaId}/sugestoes`, { metodo: "POST" });
      carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível sugerir os cortes.");
    }
  }

  async function abrir(corteId: string) {
    setAbrindo(corteId);
    setErro("");
    try {
      const projeto = await chamarApi<Projeto>(`/midias/${midiaId}/sugestoes/${corteId}/reel`, { metodo: "POST" });
      router.push(`/app/projetos/${projeto.id}`);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível abrir o corte.");
      setAbrindo("");
    }
  }

  const andando = dados?.status === "pendente" || dados?.status === "executando";

  return (
    <section className="cartao p-6" aria-labelledby="titulo-sugestoes">
      <h2 id="titulo-sugestoes" className="flex items-center gap-2 font-display text-lg font-bold">
        <Sparkles className="size-5 text-ciano" aria-hidden /> Cortes sugeridos
      </h2>
      <p className="mt-2 text-sm text-suave">
        A IA escolhe trechos da pregação. O título é uma frase que o pastor disse. Revise antes de postar.
      </p>
      {erro ? <p className="mt-3 text-sm text-vermelho" role="alert">{erro}</p> : null}
      {andando ? (
        <p className="mt-4 text-sm text-suave" role="status">
          {dados?.mensagem || "Na fila"} · {dados?.progresso ?? 0}%
        </p>
      ) : null}
      {dados?.status === "erro" ? (
        <p className="mt-4 text-sm text-vermelho" role="alert">{dados.erro || "Não foi possível sugerir os cortes."}</p>
      ) : null}
      {dados && dados.cortes.length > 0 ? (
        <ul className="mt-4 flex flex-col gap-3">
          {dados.cortes.map((corte) => {
            const duracao = corte.partes.reduce((soma, parte) => soma + (parte.fim - parte.inicio), 0);
            return (
              <li key={corte.id} className="rounded-xl border border-borda p-4">
                <p className="font-medium">{corte.titulo}</p>
                <p className="mt-1 text-sm text-suave">{corte.motivo}</p>
                <p className="mt-2 text-xs text-suave">
                  Nota {corte.nota.toLocaleString("pt-BR")} · {formatarTempo(duracao)}
                  {corte.partes.length > 1 ? ` · ${corte.partes.length} partes` : ""}
                </p>
                <p className="mt-2 text-sm">{corte.legenda_post}</p>
                {corte.hashtags.length > 0 ? (
                  <p className="mt-1 text-sm text-ciano">{corte.hashtags.join(" ")}</p>
                ) : null}
                <p className="mt-1 text-xs text-suave">Gerado por IA. Confira antes de publicar.</p>
                <button type="button" onClick={() => abrir(corte.id)} disabled={abrindo === corte.id} className="botao-contorno mt-3 px-4 py-2 text-sm">
                  {abrindo === corte.id ? "Abrindo..." : "Abrir no editor"}
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
      {!andando ? (
        <button type="button" onClick={pedir} className="botao-contorno mt-4 px-4 py-2 text-sm">
          {dados?.cortes.length ? "Sugerir de novo" : "Sugerir cortes"}
        </button>
      ) : null}
    </section>
  );
}
