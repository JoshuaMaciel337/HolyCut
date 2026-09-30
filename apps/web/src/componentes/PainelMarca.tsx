"use client";

import Link from "next/link";

import type { Marca, PosicaoLogo } from "@/lib/tipos";

const CANTOS: { valor: PosicaoLogo; rotulo: string; classe: string }[] = [
  { valor: "topo_esquerda", rotulo: "Em cima, à esquerda", classe: "items-start justify-start" },
  { valor: "topo_direita", rotulo: "Em cima, à direita", classe: "items-start justify-end" },
  { valor: "base_esquerda", rotulo: "Embaixo, à esquerda", classe: "items-end justify-start" },
  { valor: "base_direita", rotulo: "Embaixo, à direita", classe: "items-end justify-end" },
];

export function PainelMarca({ marca, temLogo, aoMudar }: { marca: Marca; temLogo: boolean; aoMudar: (marca: Marca) => void }) {
  const ativo = temLogo && marca.logo;
  return (
    <section className="cartao p-6" aria-labelledby="titulo-marca">
      <h2 id="titulo-marca" className="font-display text-lg font-bold">
        Logo da igreja
      </h2>
      {!temLogo ? (
        <p className="mt-2 text-sm text-suave">
          A igreja ainda não tem logo.{" "}
          <Link href="/app/identidade" className="font-medium text-laranja hover:underline">
            Envie em Sua Identidade
          </Link>
          .
        </p>
      ) : (
        <>
          <label className="mt-4 flex items-center gap-3 text-sm">
            <input
              type="checkbox"
              checked={marca.logo}
              onChange={(evento) => aoMudar({ ...marca, logo: evento.target.checked })}
              className="size-4 accent-[var(--hc-orange)]"
            />
            Mostrar o logo no vídeo
          </label>
          <div className={`mt-4 flex flex-wrap items-start gap-6 ${ativo ? "" : "pointer-events-none opacity-50"}`}>
            <div role="radiogroup" aria-label="Posição do logo" className="grid w-20 grid-cols-2 gap-1 rounded-xl border border-borda bg-ink p-1" style={{ aspectRatio: "9 / 12" }}>
              {CANTOS.map((canto) => (
                <button
                  key={canto.valor}
                  type="button"
                  role="radio"
                  aria-checked={marca.posicao === canto.valor}
                  aria-label={canto.rotulo}
                  title={canto.rotulo}
                  onClick={() => aoMudar({ ...marca, posicao: canto.valor })}
                  className={`flex rounded-lg p-1 ${canto.classe} ${marca.posicao === canto.valor ? "bg-laranja/20" : "hover:bg-surface-2"}`}
                >
                  <span className={`size-3 rounded-sm ${marca.posicao === canto.valor ? "bg-laranja" : "bg-borda"}`} />
                </button>
              ))}
            </div>
            <div className="flex min-w-48 flex-1 flex-col gap-3 text-sm">
              <label className="flex items-center gap-3">
                <span className="w-20 shrink-0 text-suave">Tamanho</span>
                <input
                  type="range"
                  min={0.06}
                  max={0.4}
                  step={0.01}
                  value={marca.tamanho}
                  onChange={(evento) => aoMudar({ ...marca, tamanho: Number(evento.target.value) })}
                  className="w-full accent-[var(--hc-orange)]"
                />
              </label>
              <label className="flex items-center gap-3">
                <span className="w-20 shrink-0 text-suave">Opacidade</span>
                <input
                  type="range"
                  min={0.2}
                  max={1}
                  step={0.05}
                  value={marca.opacidade}
                  onChange={(evento) => aoMudar({ ...marca, opacidade: Number(evento.target.value) })}
                  className="w-full accent-[var(--hc-orange)]"
                />
              </label>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
