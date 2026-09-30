"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

import { chamarApi } from "@/lib/api";
import type { Job } from "@/lib/tipos";

export type EstadoConexao = "conectando" | "ao-vivo" | "reconectando" | "consulta";
type Ouvinte = (job: Job) => void;

// Sem o evento "pronto" nesse prazo, algum proxy está segurando o fluxo
// (o túnel rápido da Cloudflare não entrega Server-Sent Events).
const ESPERA_PRONTO_MS = 5_000;
const INTERVALO_CONSULTA_MS = 3_000;
const LIMITE_CONSULTA = 20;

type ContextoEventos = {
  conexao: EstadoConexao;
  ouvir: (ouvinte: Ouvinte) => () => void;
};

const Contexto = createContext<ContextoEventos | null>(null);

/**
 * Uma conexão só por aba com o /api/eventos, repassada a quem quiser ouvir.
 * Se o fluxo não chegar, consulta /api/jobs a cada 3 segundos e repassa o que mudou.
 */
export function ProvedorEventos({ children }: { children: React.ReactNode }) {
  const [conexao, setConexao] = useState<EstadoConexao>("conectando");
  const ouvintes = useRef(new Set<Ouvinte>());

  useEffect(() => {
    let cancelado = false;
    let recebeuPronto = false;
    let consulta: ReturnType<typeof setInterval> | undefined;
    const vistos = new Map<string, string>(); // id do job → atualizado_em já repassado

    const repassar = (job: Job) => {
      if (vistos.get(job.id) === job.atualizado_em) return;
      vistos.set(job.id, job.atualizado_em);
      ouvintes.current.forEach((ouvinte) => ouvinte(job));
    };
    const consultar = () =>
      chamarApi<Job[]>(`/jobs?limite=${LIMITE_CONSULTA}`)
        .then((lista) => {
          if (!cancelado) lista.forEach(repassar);
        })
        .catch(() => undefined);

    const fonte = new EventSource("/api/eventos");
    fonte.addEventListener("pronto", () => {
      recebeuPronto = true;
      setConexao("ao-vivo");
      consultar(); // recupera o que mudou enquanto a conexão estava fora
    });
    fonte.addEventListener("job", (evento) => repassar(JSON.parse((evento as MessageEvent<string>).data) as Job));
    fonte.onerror = () => {
      if (recebeuPronto) setConexao("reconectando");
    };

    const espera = setTimeout(() => {
      if (recebeuPronto || cancelado) return;
      fonte.close();
      setConexao("consulta");
      consultar();
      consulta = setInterval(consultar, INTERVALO_CONSULTA_MS);
    }, ESPERA_PRONTO_MS);

    return () => {
      cancelado = true;
      clearTimeout(espera);
      clearInterval(consulta);
      fonte.close();
    };
  }, []);

  const ouvir = useCallback((ouvinte: Ouvinte) => {
    ouvintes.current.add(ouvinte);
    return () => {
      ouvintes.current.delete(ouvinte);
    };
  }, []);

  return <Contexto.Provider value={{ conexao, ouvir }}>{children}</Contexto.Provider>;
}

function useContexto(): ContextoEventos {
  const contexto = useContext(Contexto);
  if (!contexto) throw new Error("Os eventos precisam estar dentro de ProvedorEventos");
  return contexto;
}

export function useConexao(): EstadoConexao {
  return useContexto().conexao;
}

/** Chama ouvinte a cada job novo ou atualizado da igreja. */
export function useEventosJobs(ouvinte: Ouvinte) {
  const { ouvir } = useContexto();
  const atual = useRef(ouvinte);
  useEffect(() => {
    atual.current = ouvinte;
  });
  useEffect(() => ouvir((job) => atual.current(job)), [ouvir]);
}
