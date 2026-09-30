"use client";

import { ArrowLeft, FolderOpen } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { CartaoJob } from "@/componentes/CartaoJob";
import { PainelSistema } from "@/componentes/PainelSistema";
import { chamarApi, ErroApi } from "@/lib/api";
import type { Job } from "@/lib/tipos";
import { useJobsAoVivo } from "@/lib/useJobsAoVivo";
import { useSistema } from "@/lib/useSistema";

export default function PaginaDiagnostico() {
  const sistema = useSistema();
  const { jobs, adicionar } = useJobsAoVivo();
  const [criando, setCriando] = useState(false);
  const [erro, setErro] = useState("");
  const gpuOnline = sistema?.workers.some((w) => w.recursos.includes("gpu")) ?? false;

  async function criarJob(corpo: { tipo: string; duracao?: number; falhar?: boolean }) {
    setCriando(true);
    setErro("");
    try {
      adicionar(await chamarApi<Job>("/jobs", { metodo: "POST", corpo }));
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível criar o job.");
    } finally {
      setCriando(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <Link href="/app" className="inline-flex items-center gap-2 text-sm text-suave hover:text-texto">
        <ArrowLeft className="size-4" aria-hidden /> Início
      </Link>
      <h1 className="mt-4 font-display text-3xl font-bold">Diagnóstico</h1>
      <p className="mt-1 text-suave">Confere se a fila, os workers e a GPU estão funcionando.</p>

      {erro ? (
        <p role="alert" className="mt-6 rounded-xl border border-vermelho/40 bg-vermelho/10 px-4 py-3 text-sm text-vermelho">
          {erro}
        </p>
      ) : null}

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_320px]">
        <section className="cartao p-6" aria-labelledby="titulo-teste">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 id="titulo-teste" className="font-display text-lg font-bold">
                Teste do pipeline
              </h2>
              <p className="mt-1 max-w-xl text-sm text-suave">
                Cria um job na fila. O worker pega, processa e o progresso aparece aqui ao vivo.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="button" className="botao-cta px-4 py-2 text-sm" disabled={criando} onClick={() => criarJob({ tipo: "teste", duracao: 10 })}>
                Rodar job de teste
              </button>
              <button type="button" className="botao-contorno px-4 py-2 text-sm" disabled={criando} onClick={() => criarJob({ tipo: "teste", duracao: 6, falhar: true })}>
                Simular falha
              </button>
              <button type="button" className="botao-contorno px-4 py-2 text-sm" disabled={criando} onClick={() => criarJob({ tipo: "diagnostico_gpu" })}>
                Testar GPU
              </button>
            </div>
          </div>

          {jobs.length === 0 ? (
            <div className="mt-8 flex flex-col items-center gap-2 rounded-2xl border border-dashed border-borda py-10 text-center text-suave">
              <FolderOpen className="size-8" aria-hidden />
              <p>Nenhum job ainda. Rode o job de teste para ver a fila funcionando.</p>
            </div>
          ) : (
            <ul className="mt-6 flex flex-col gap-3">
              {jobs.map((job) => (
                <CartaoJob key={job.id} job={job} gpuOnline={gpuOnline} />
              ))}
            </ul>
          )}
        </section>

        <PainelSistema sistema={sistema} />
      </div>
    </main>
  );
}
