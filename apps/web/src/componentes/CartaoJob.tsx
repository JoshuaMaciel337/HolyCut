import { CircleAlert, CircleCheck, Clock, Cpu, LoaderCircle, Zap } from "lucide-react";

import type { Job, StatusJob } from "@/lib/tipos";

const NOMES_TIPO: Record<string, string> = {
  teste: "Pipeline de teste",
  diagnostico_gpu: "Diagnóstico da GPU",
  ingestao: "Preparação da gravação",
};

const ESTILOS_STATUS: Record<StatusJob, { rotulo: string; classe: string }> = {
  pendente: { rotulo: "Na fila", classe: "border-borda text-suave" },
  executando: { rotulo: "Processando", classe: "border-violeta/50 text-violeta" },
  concluido: { rotulo: "Concluído", classe: "border-ciano/40 text-ciano" },
  erro: { rotulo: "Erro", classe: "border-vermelho/50 text-vermelho" },
};

function IconeStatus({ status }: { status: StatusJob }) {
  if (status === "executando") return <LoaderCircle className="size-4 animate-spin" aria-hidden />;
  if (status === "concluido") return <CircleCheck className="size-4" aria-hidden />;
  if (status === "erro") return <CircleAlert className="size-4" aria-hidden />;
  return <Clock className="size-4" aria-hidden />;
}

function hora(iso: string) {
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function CartaoJob({ job, gpuOnline }: { job: Job; gpuOnline: boolean }) {
  const estilo = ESTILOS_STATUS[job.status];
  const aguardandoGpu = job.status === "pendente" && job.recurso === "gpu" && !gpuOnline;
  const saidaGpu = job.tipo === "diagnostico_gpu" && job.status === "concluido" ? job.saida : null;

  return (
    <li className="rounded-2xl border border-borda bg-surface-2/60 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {job.recurso === "gpu" ? (
            <Zap className="size-4 text-amarelo" aria-label="GPU" />
          ) : (
            <Cpu className="size-4 text-suave" aria-label="CPU" />
          )}
          <span className="font-medium">{NOMES_TIPO[job.tipo] ?? job.tipo}</span>
          <span className="text-xs text-suave">{hora(job.criado_em)}</span>
        </div>
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${estilo.classe}`}>
          <IconeStatus status={job.status} />
          {estilo.rotulo}
        </span>
      </div>

      <div
        className="mt-3 h-2 overflow-hidden rounded-full bg-ink"
        role="progressbar"
        aria-valuenow={job.progresso}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full transition-[width] duration-500"
          style={{
            width: `${job.progresso}%`,
            backgroundImage: job.status === "erro" ? "none" : "var(--hc-gradient-cta)",
            backgroundColor: job.status === "erro" ? "var(--hc-red)" : undefined,
          }}
        />
      </div>

      <div className="mt-2 flex flex-wrap justify-between gap-2 text-sm text-suave">
        <span>{aguardandoGpu ? "Aguardando o notebook com GPU ficar online" : job.mensagem}</span>
        <span>
          {job.progresso}% · tentativa {Math.max(job.tentativas, 1)} de {job.max_tentativas}
        </span>
      </div>

      {job.erro ? <p className="mt-2 text-sm text-vermelho">{job.erro}</p> : null}
      {saidaGpu ? (
        <pre className="mt-3 overflow-x-auto rounded-xl bg-ink p-3 text-xs text-suave">
          {JSON.stringify(saidaGpu, null, 2)}
        </pre>
      ) : null}
    </li>
  );
}
