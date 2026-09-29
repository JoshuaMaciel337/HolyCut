import { Radio } from "lucide-react";

import type { EstadoConexao } from "@/lib/useJobsAoVivo";
import type { Sistema } from "@/lib/tipos";

const ROTULOS_CONEXAO: Record<EstadoConexao, string> = {
  conectando: "conectando",
  "ao-vivo": "ao vivo",
  reconectando: "reconectando",
  consulta: "a cada 3 segundos",
};

function Indicador({ online, rotulo, detalhe }: { online: boolean; rotulo: string; detalhe: string }) {
  return (
    <div className="flex items-start gap-3">
      <span
        className={`mt-1.5 size-2.5 shrink-0 rounded-full ${online ? "bg-ciano shadow-[0_0_10px_var(--hc-cyan)]" : "bg-borda"}`}
        aria-hidden
      />
      <div>
        <p className="font-medium">{rotulo}</p>
        <p className="text-sm text-suave">{detalhe}</p>
      </div>
    </div>
  );
}

export function PainelSistema({ sistema, conexao }: { sistema: Sistema | null; conexao: EstadoConexao }) {
  const workersCpu = sistema?.workers.filter((w) => w.recursos.includes("cpu")) ?? [];
  const workersGpu = sistema?.workers.filter((w) => w.recursos.includes("gpu")) ?? [];

  return (
    <section className="cartao p-6" aria-labelledby="titulo-sistema">
      <h2 id="titulo-sistema" className="font-display text-lg font-bold">
        Sistema
      </h2>
      <div className="mt-5 flex flex-col gap-4">
        <div className="flex items-center gap-2 text-sm text-suave">
          <Radio className="size-4" aria-hidden />
          Atualização: {ROTULOS_CONEXAO[conexao]}
        </div>
        <Indicador
          online={workersCpu.length > 0}
          rotulo="Processamento"
          detalhe={workersCpu.length > 0 ? `${workersCpu.length} worker(s) online` : "Nenhum worker de CPU online"}
        />
        <Indicador
          online={workersGpu.length > 0}
          rotulo="IA com GPU"
          detalhe={workersGpu.length > 0 ? "Notebook com GPU online" : "Notebook com GPU desligado ou fora da rede"}
        />
        <p className="text-xs text-suave">Modo de IA: {sistema?.modo_ia ?? "—"}</p>
      </div>
    </section>
  );
}
