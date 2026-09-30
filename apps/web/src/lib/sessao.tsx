"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { chamarApi, ErroApi } from "@/lib/api";
import type { Sessao } from "@/lib/tipos";

type ContextoSessao = {
  sessao: Sessao;
  sair: () => Promise<void>;
};

const Contexto = createContext<ContextoSessao | null>(null);

/** Carrega a sessão uma vez para toda a área logada. Se a API recusar, apaga o cookie e volta ao login. */
export function ProvedorSessao({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [sessao, setSessao] = useState<Sessao | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    chamarApi<Sessao>("/auth/eu")
      .then(setSessao)
      .catch(async (e) => {
        if (e instanceof ErroApi && e.status === 401) {
          await chamarApi("/auth/sair", { metodo: "POST" }).catch(() => undefined);
          router.replace(`/entrar?proximo=${encodeURIComponent(window.location.pathname)}`);
          return;
        }
        setErro(e instanceof ErroApi ? e.message : "Não foi possível carregar o painel.");
      });
  }, [router]);

  const sair = useCallback(async () => {
    await chamarApi("/auth/sair", { metodo: "POST" }).catch(() => undefined);
    router.replace("/entrar");
  }, [router]);

  if (!sessao) {
    return (
      <div className="flex min-h-dvh items-center justify-center px-4 text-center text-suave">
        {erro || "Carregando..."}
      </div>
    );
  }
  return <Contexto.Provider value={{ sessao, sair }}>{children}</Contexto.Provider>;
}

export function useSessao(): ContextoSessao {
  const contexto = useContext(Contexto);
  if (!contexto) throw new Error("useSessao precisa estar dentro de ProvedorSessao");
  return contexto;
}
