"use client";

import { Library, LogOut, Music, Palette } from "lucide-react";
import Link from "next/link";

import { Logo } from "@/componentes/Logo";
import { useSessao } from "@/lib/sessao";

export function Cabecalho() {
  const { sessao, sair } = useSessao();
  return (
    <header className="border-b border-borda bg-surface/70 backdrop-blur print:hidden">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link href="/app" aria-label="Início">
          <Logo altura={30} prioridade />
        </Link>
        <div className="flex items-center gap-3">
          <Link href="/app/acervo" className="inline-flex items-center gap-1.5 rounded-full px-3 py-2 text-sm text-suave hover:text-texto">
            <Library className="size-4" aria-hidden /> <span className="hidden sm:inline">Acervo</span>
          </Link>
          <Link href="/app/musicas" className="inline-flex items-center gap-1.5 rounded-full px-3 py-2 text-sm text-suave hover:text-texto">
            <Music className="size-4" aria-hidden /> <span className="hidden sm:inline">Músicas</span>
          </Link>
          <Link href="/app/identidade" className="inline-flex items-center gap-1.5 rounded-full px-3 py-2 text-sm text-suave hover:text-texto">
            <Palette className="size-4" aria-hidden /> <span className="hidden sm:inline">Sua Identidade</span>
          </Link>
          <div className="hidden text-right sm:block">
            <p className="text-sm font-medium">{sessao.organizacao.nome}</p>
            <p className="text-xs text-suave">{sessao.usuario.nome}</p>
          </div>
          <button type="button" onClick={sair} className="botao-contorno px-4 py-2 text-sm">
            <LogOut className="size-4" aria-hidden /> Sair
          </button>
        </div>
      </div>
    </header>
  );
}
