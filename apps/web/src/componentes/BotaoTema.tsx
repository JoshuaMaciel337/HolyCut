"use client";

import { Moon, Sun } from "lucide-react";

export const CHAVE_TEMA = "holycut-tema";

/** Troca entre o tema escuro e o claro e lembra a escolha neste navegador. */
export function BotaoTema({ className = "" }: { className?: string }) {
  function trocar() {
    const claro = document.documentElement.dataset.tema !== "claro";
    if (claro) document.documentElement.dataset.tema = "claro";
    else delete document.documentElement.dataset.tema;
    try {
      localStorage.setItem(CHAVE_TEMA, claro ? "claro" : "escuro");
    } catch {
      // Sem armazenamento (aba anônima): o tema vale só até fechar a página
    }
  }

  return (
    <button
      type="button"
      onClick={trocar}
      className={`inline-flex size-9 items-center justify-center rounded-full border border-borda text-suave transition hover:text-texto ${className}`}
      aria-label="Trocar entre tema claro e escuro"
      title="Tema claro ou escuro"
    >
      <Sun className="so-escuro size-4" aria-hidden />
      <Moon className="so-claro size-4" aria-hidden />
    </button>
  );
}
