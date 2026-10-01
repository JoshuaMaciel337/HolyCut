"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { chamarApi, ErroApi } from "@/lib/api";
import { useEventosJobs } from "@/lib/eventos";
import type { Blocos, Job } from "@/lib/tipos";

/** Os blocos do culto, atualizados quando o job termina. aoTerminar avisa que a pregação pode ter mudado. */
export function useBlocos(midiaId: string, aoTerminar?: () => void) {
  const [dados, setDados] = useState<Blocos | null>(null);
  const [erro, setErro] = useState("");
  const avisar = useRef(aoTerminar);
  useEffect(() => {
    avisar.current = aoTerminar;
  }, [aoTerminar]);

  const carregar = useCallback(() => {
    chamarApi<Blocos>(`/midias/${midiaId}/blocos`)
      .then(setDados)
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar os blocos."));
  }, [midiaId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEventosJobs((job) => {
    if (job.entrada.midia_id !== midiaId) return;
    if (job.tipo === "blocos_culto" || job.tipo === "transcricao") carregar();
    if (job.tipo === "blocos_culto" && job.status === "concluido") avisar.current?.();
  });

  async function pedir() {
    setErro("");
    try {
      await chamarApi<Job>(`/midias/${midiaId}/blocos`, { metodo: "POST" });
      carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível separar os blocos.");
    }
  }

  const andando = dados?.status === "pendente" || dados?.status === "executando";
  return { dados, erro, pedir, andando };
}
