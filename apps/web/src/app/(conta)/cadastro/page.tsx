"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { CampoTexto } from "@/componentes/CampoTexto";
import { chamarApi, ErroApi } from "@/lib/api";
import type { Sessao } from "@/lib/tipos";

export default function PaginaCadastro() {
  const router = useRouter();
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const dados = new FormData(evento.currentTarget);
    setErro("");
    setEnviando(true);
    try {
      await chamarApi<Sessao>("/auth/cadastro", {
        metodo: "POST",
        corpo: {
          nome_igreja: dados.get("nome_igreja"),
          nome: dados.get("nome"),
          email: dados.get("email"),
          senha: dados.get("senha"),
        },
      });
      router.replace("/app");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível criar a conta. Tente de novo.");
      setEnviando(false);
    }
  }

  return (
    <>
      <h1 className="font-display text-2xl font-bold">Cadastre sua igreja</h1>
      <p className="mt-1 text-sm text-suave">Você será o responsável pela conta e poderá convidar a equipe depois.</p>
      <form onSubmit={enviar} className="mt-6 flex flex-col gap-4" noValidate>
        <CampoTexto rotulo="Nome da igreja" name="nome_igreja" autoComplete="organization" required />
        <CampoTexto rotulo="Seu nome" name="nome" autoComplete="name" required />
        <CampoTexto rotulo="E-mail" name="email" type="email" autoComplete="email" required />
        <CampoTexto
          rotulo="Senha"
          name="senha"
          type="password"
          autoComplete="new-password"
          minLength={8}
          dica="Pelo menos 8 caracteres."
          required
        />
        {erro ? (
          <p role="alert" className="rounded-xl border border-vermelho/40 bg-vermelho/10 px-4 py-3 text-sm text-vermelho">
            {erro}
          </p>
        ) : null}
        <button type="submit" className="botao-cta mt-2 w-full" disabled={enviando}>
          {enviando ? "Criando conta..." : "Criar conta"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-suave">
        Já tem conta?{" "}
        <Link href="/entrar" className="font-medium text-laranja hover:underline">
          Entrar
        </Link>
      </p>
    </>
  );
}
