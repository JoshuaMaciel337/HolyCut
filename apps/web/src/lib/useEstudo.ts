"use client";

import { useCallback, useEffect, useState } from "react";

import { chamarApi, ErroApi } from "@/lib/api";
import { useEventosJobs } from "@/lib/eventos";
import type { Estudo, Job } from "@/lib/tipos";

/** O HolyStudy da pregação, atualizado quando o job termina. Usado no resumo, no guia e na impressão. */
export function useEstudo(midiaId: string) {
  const [dados, setDados] = useState<Estudo | null>(null);
  const [erro, setErro] = useState("");

  const carregar = useCallback(() => {
    chamarApi<Estudo>(`/midias/${midiaId}/estudo`)
      .then(setDados)
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar o estudo."));
  }, [midiaId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEventosJobs((job) => {
    if ((job.tipo === "estudo_culto" || job.tipo === "transcricao") && job.entrada.midia_id === midiaId) carregar();
  });

  async function pedir() {
    setErro("");
    try {
      await chamarApi<Job>(`/midias/${midiaId}/estudo`, { metodo: "POST" });
      carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível preparar o estudo.");
    }
  }

  const andando = dados?.status === "pendente" || dados?.status === "executando";
  return { dados, erro, pedir, andando };
}
