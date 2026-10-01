"use client";

import { ScanFace } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { chamarApi, ErroApi } from "@/lib/api";
import { useEventosJobs } from "@/lib/eventos";
import { formatarTempo } from "@/lib/formatar";
import type { Job, Momentos } from "@/lib/tipos";

const ASSUNTOS: Record<string, string> = {
  pregador: "Pregador",
  plateia: "Plateia",
  luz: "Luz",
  outro: "Outro",
};

export function MomentosDoCulto({ midiaId }: { midiaId: string }) {
  const [dados, setDados] = useState<Momentos | null>(null);
  const [erro, setErro] = useState("");

  const carregar = useCallback(() => {
    chamarApi<Momentos>(`/midias/${midiaId}/momentos`)
      .then(setDados)
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar os momentos."));
  }, [midiaId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEventosJobs((job) => {
    if (job.tipo === "momentos" && job.entrada.midia_id === midiaId) carregar();
  });

  async function pedir() {
    setErro("");
    try {
      await chamarApi<Job>(`/midias/${midiaId}/momentos`, { metodo: "POST" });
      carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível marcar os momentos.");
    }
  }

  const andando = dados?.status === "pendente" || dados?.status === "executando";

  return (
    <section className="cartao p-6" aria-labelledby="titulo-momentos">
      <h2 id="titulo-momentos" className="flex items-center gap-2 font-display text-lg font-bold">
        <ScanFace className="size-5 text-ciano" aria-hidden /> Momentos
      </h2>
      <p className="mt-2 text-sm text-suave">
        Trechos em que a voz sobe e as trocas de cena. A nota visual, quando existe, só diz se aparece o pregador, a plateia, a luz ou outro.
      </p>
      {erro ? <p className="mt-3 text-sm text-vermelho" role="alert">{erro}</p> : null}
      {andando ? (
        <p className="mt-4 text-sm text-suave" role="status">{dados?.mensagem || "Na fila"} · {dados?.progresso ?? 0}%</p>
      ) : null}
      {dados?.status === "erro" ? (
        <p className="mt-4 text-sm text-vermelho" role="alert">{dados.erro || "Não foi possível marcar os momentos."}</p>
      ) : null}
      {dados?.status === "ausente" ? (
        <button type="button" onClick={pedir} className="botao-contorno mt-4 px-4 py-2 text-sm">
          Marcar os momentos
        </button>
      ) : null}
      {dados && dados.momentos.length > 0 ? (
        <ul className="mt-4 flex flex-col gap-3">
          {dados.momentos.map((momento) => (
            <li key={`${momento.inicio}-${momento.fim}`} className="rounded-xl border border-borda p-4">
              <p className="font-medium tabular-nums">
                {formatarTempo(momento.inicio)} – {formatarTempo(momento.fim)}
              </p>
              <p className="mt-1 text-sm text-suave">
                Energia {Math.round(momento.energia * 100)}%
                {momento.assunto ? ` · ${ASSUNTOS[momento.assunto] ?? momento.assunto}` : ""}
                {momento.nota != null ? ` · nota ${momento.nota}` : ""}
              </p>
            </li>
          ))}
        </ul>
      ) : null}
      {dados?.gerado_por_ia ? <p className="mt-4 text-xs text-suave">Nota visual gerada por IA.</p> : null}
    </section>
  );
}
