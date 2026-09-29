"use client";

import { useCallback, useEffect, useState } from "react";

import { chamarApi } from "@/lib/api";
import type { Job } from "@/lib/tipos";

export type EstadoConexao = "conectando" | "ao-vivo" | "reconectando";

const LIMITE_JOBS = 8;

function mesclar(lista: Job[], novo: Job): Job[] {
  const outros = lista.filter((job) => job.id !== novo.id);
  return [novo, ...outros]
    .sort((a, b) => b.criado_em.localeCompare(a.criado_em))
    .slice(0, LIMITE_JOBS);
}

/** Lista os jobs recentes e recebe cada mudança pelo /api/eventos (Server-Sent Events). */
export function useJobsAoVivo(ativo: boolean) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [conexao, setConexao] = useState<EstadoConexao>("conectando");

  useEffect(() => {
    if (!ativo) return;
    let cancelado = false;

    chamarApi<Job[]>(`/jobs?limite=${LIMITE_JOBS}`)
      .then((lista) => {
        if (!cancelado) setJobs((atuais) => lista.reduce(mesclar, atuais));
      })
      .catch(() => undefined);

    const fonte = new EventSource("/api/eventos");
    fonte.onopen = () => setConexao("ao-vivo");
    fonte.onerror = () => setConexao("reconectando");
    fonte.addEventListener("job", (evento) => {
      const job = JSON.parse((evento as MessageEvent<string>).data) as Job;
      setJobs((atuais) => mesclar(atuais, job));
    });

    return () => {
      cancelado = true;
      fonte.close();
    };
  }, [ativo]);

  const adicionar = useCallback((job: Job) => setJobs((atuais) => mesclar(atuais, job)), []);

  return { jobs, conexao, adicionar };
}
