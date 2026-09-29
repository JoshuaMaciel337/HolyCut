"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { CampoTexto } from "@/componentes/CampoTexto";
import { chamarApi, destinoSeguro, ErroApi } from "@/lib/api";
import type { Sessao } from "@/lib/tipos";

export default function PaginaEntrar() {
  const router = useRouter();
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const dados = new FormData(evento.currentTarget);
    setErro("");
    setEnviando(true);
    try {
      await chamarApi<Sessao>("/auth/entrar", {
        metodo: "POST",
        corpo: { email: dados.get("email"), senha: dados.get("senha") },
      });
      const proximo = new URLSearchParams(window.location.search).get("proximo");
      router.replace(destinoSeguro(proximo));
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível entrar. Tente de novo.");
      setEnviando(false);
    }
  }

  return (
    <>
      <h1 className="font-display text-2xl font-bold">Entrar</h1>
      <p className="mt-1 text-sm text-suave">Acesse a mídia da sua igreja.</p>
      <form onSubmit={enviar} className="mt-6 flex flex-col gap-4" noValidate>
        <CampoTexto rotulo="E-mail" name="email" type="email" autoComplete="email" required />
        <CampoTexto rotulo="Senha" name="senha" type="password" autoComplete="current-password" required />
        {erro ? (
          <p role="alert" className="rounded-xl border border-vermelho/40 bg-vermelho/10 px-4 py-3 text-sm text-vermelho">
            {erro}
          </p>
        ) : null}
        <button type="submit" className="botao-cta mt-2 w-full" disabled={enviando}>
          {enviando ? "Entrando..." : "Entrar"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-suave">
        Ainda não tem conta?{" "}
        <Link href="/cadastro" className="font-medium text-laranja hover:underline">
          Cadastre sua igreja
        </Link>
      </p>
    </>
  );
}
