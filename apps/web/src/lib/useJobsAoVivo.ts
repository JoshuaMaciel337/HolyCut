"use client";

import { useCallback, useEffect, useState } from "react";

import { chamarApi } from "@/lib/api";
import type { Job } from "@/lib/tipos";

export type EstadoConexao = "conectando" | "ao-vivo" | "reconectando" | "consulta";

const LIMITE_JOBS = 8;
// Sem o evento "pronto" nesse prazo, algum proxy está segurando o fluxo
// (o túnel rápido da Cloudflare não entrega Server-Sent Events).
const ESPERA_PRONTO_MS = 5_000;
const INTERVALO_CONSULTA_MS = 3_000;

function mesclar(lista: Job[], novo: Job): Job[] {
  const atual = lista.find((job) => job.id === novo.id);
  if (atual && atual.atualizado_em > novo.atualizado_em) return lista;
  const outros = lista.filter((job) => job.id !== novo.id);
  return [novo, ...outros]
    .sort((a, b) => b.criado_em.localeCompare(a.criado_em))
    .slice(0, LIMITE_JOBS);
}

/**
 * Lista os jobs recentes e recebe cada mudança pelo /api/eventos (Server-Sent Events).
 * Se o fluxo não chegar, passa a consultar /api/jobs a cada 3 segundos.
 */
export function useJobsAoVivo(ativo: boolean) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [conexao, setConexao] = useState<EstadoConexao>("conectando");

  useEffect(() => {
    if (!ativo) return;
    let cancelado = false;
    let recebeuPronto = false;
    let consulta: ReturnType<typeof setInterval> | undefined;

    const carregar = () =>
      chamarApi<Job[]>(`/jobs?limite=${LIMITE_JOBS}`)
        .then((lista) => {
          if (!cancelado) setJobs((atuais) => lista.reduce(mesclar, atuais));
        })
        .catch(() => undefined);

    carregar();

    const fonte = new EventSource("/api/eventos");
    fonte.addEventListener("pronto", () => {
      recebeuPronto = true;
      setConexao("ao-vivo");
      carregar(); // recupera o que mudou enquanto a conexão estava fora
    });
    fonte.addEventListener("job", (evento) => {
      const job = JSON.parse((evento as MessageEvent<string>).data) as Job;
      setJobs((atuais) => mesclar(atuais, job));
    });
    fonte.onerror = () => {
      if (recebeuPronto) setConexao("reconectando");
    };

    const espera = setTimeout(() => {
      if (recebeuPronto || cancelado) return;
      fonte.close();
      setConexao("consulta");
      consulta = setInterval(carregar, INTERVALO_CONSULTA_MS);
    }, ESPERA_PRONTO_MS);

    return () => {
      cancelado = true;
      clearTimeout(espera);
      clearInterval(consulta);
      fonte.close();
    };
  }, [ativo]);

  const adicionar = useCallback((job: Job) => setJobs((atuais) => mesclar(atuais, job)), []);

  return { jobs, conexao, adicionar };
}
