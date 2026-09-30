"use client";

import { useCallback, useEffect, useState } from "react";

import { chamarApi } from "@/lib/api";
import { useEventosJobs } from "@/lib/eventos";
import type { Job } from "@/lib/tipos";

const LIMITE_JOBS = 8;

function mesclar(lista: Job[], novo: Job): Job[] {
  const atual = lista.find((job) => job.id === novo.id);
  if (atual && atual.atualizado_em > novo.atualizado_em) return lista;
  const outros = lista.filter((job) => job.id !== novo.id);
  return [novo, ...outros]
    .sort((a, b) => b.criado_em.localeCompare(a.criado_em))
    .slice(0, LIMITE_JOBS);
}

/** Jobs recentes da igreja, atualizados pela conexão de eventos do layout. */
export function useJobsAoVivo() {
  const [jobs, setJobs] = useState<Job[]>([]);

  useEffect(() => {
    let cancelado = false;
    chamarApi<Job[]>(`/jobs?limite=${LIMITE_JOBS}`)
      .then((lista) => {
        if (!cancelado) setJobs((atuais) => lista.reduce(mesclar, atuais));
      })
      .catch(() => undefined);
    return () => {
      cancelado = true;
    };
  }, []);

  useEventosJobs((job) => setJobs((atuais) => mesclar(atuais, job)));

  const adicionar = useCallback((job: Job) => setJobs((atuais) => mesclar(atuais, job)), []);
  return { jobs, adicionar };
}
