"use client";

import { Check, CircleAlert, MessageSquareText } from "lucide-react";
import Image from "next/image";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Logo } from "@/componentes/Logo";
import { chamarApi, ErroApi } from "@/lib/api";
import { formatarData, formatarTempo } from "@/lib/formatar";
import type { AprovacaoPublica } from "@/lib/tipos";

const CHAVE_NOME = "holycut-aprovador";

function lerNomeSalvo(): string {
  try {
    return window.localStorage.getItem(CHAVE_NOME) ?? "";
  } catch {
    return "";
  }
}

/** Página aberta pelo link do WhatsApp: quem aprova assiste ao vídeo e responde, sem conta. */
export default function PaginaAprovar() {
  const { token } = useParams<{ token: string }>();
  const [pedido, setPedido] = useState<AprovacaoPublica | null>(null);
  const [erro, setErro] = useState("");
  const [nome, setNome] = useState("");
  const [comentario, setComentario] = useState("");
  const [pedindoAjuste, setPedindoAjuste] = useState(false);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    chamarApi<AprovacaoPublica>(`/aprovar/${token}`)
      .then((dados) => {
        setPedido(dados);
        setNome(lerNomeSalvo() || dados.aprovacao.para);
      })
      .catch((e) => setErro(e instanceof ErroApi ? e.message : "Não foi possível abrir o vídeo."));
  }, [token]);

  async function responder(decisao: "aprovado" | "ajustes") {
    setEnviando(true);
    setErro("");
    try {
      setPedido(await chamarApi<AprovacaoPublica>(`/aprovar/${token}`, { metodo: "POST", corpo: { decisao, nome: nome.trim(), comentario } }));
      try {
        window.localStorage.setItem(CHAVE_NOME, nome.trim());
      } catch {
        // sem armazenamento no navegador: só não lembra o nome da próxima vez
      }
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível enviar a resposta.");
    } finally {
      setEnviando(false);
    }
  }

  const base = `/api/aprovar/${token}/arquivos`;
  const aprovacao = pedido?.aprovacao;
  const respondido = aprovacao && aprovacao.status !== "pendente";

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col gap-5 px-4 py-6">
      <Logo altura={26} />
      {!pedido ? (
        <p className={erro ? "rounded-xl border border-vermelho/40 bg-vermelho/10 px-4 py-3 text-sm text-vermelho" : "text-suave"}>
          {erro || "Carregando o vídeo..."}
        </p>
      ) : (
        <>
          <div>
            <p className="text-sm text-suave">{pedido.igreja} pede sua aprovação</p>
            <h1 className="mt-1 font-display text-2xl font-bold">{pedido.nome}</h1>
            {pedido.duracao ? <p className="text-sm text-suave">{formatarTempo(pedido.duracao)}</p> : null}
          </div>

          {aprovacao?.expirada ? (
            <p className="rounded-xl border border-amarelo/40 bg-amarelo/10 px-4 py-3 text-sm">
              Este link expirou em {formatarData(aprovacao.expira_em)}. Peça um novo a quem enviou.
            </p>
          ) : pedido.formato === "imagem" ? (
            <Image
              src={`${base}/imagem.jpg`}
              alt={pedido.nome}
              width={pedido.largura}
              height={pedido.altura}
              unoptimized
              className="h-auto w-full rounded-2xl bg-black"
            />
          ) : (
            <video
              src={`${base}/video.mp4`}
              poster={pedido.arquivos.includes("capa.jpg") ? `${base}/capa.jpg` : undefined}
              controls
              playsInline
              preload="metadata"
              className="w-full rounded-2xl bg-black"
              style={{ aspectRatio: `${pedido.largura} / ${pedido.altura}` }}
            />
          )}

          {respondido ? (
            <div
              className={`rounded-2xl border px-4 py-4 ${aprovacao.status === "aprovado" ? "border-ciano/40 bg-ciano/10" : "border-amarelo/40 bg-amarelo/10"}`}
              data-resposta={aprovacao.status}
            >
              <p className="flex items-center gap-2 font-semibold">
                {aprovacao.status === "aprovado" ? <Check className="size-5 text-ciano" aria-hidden /> : <MessageSquareText className="size-5 text-amarelo" aria-hidden />}
                {aprovacao.status === "aprovado" ? "Vídeo aprovado" : "Pedido de ajuste enviado"}
              </p>
              <p className="mt-1 text-sm text-suave">
                Por {aprovacao.respondido_por}
                {aprovacao.respondido_em ? `, em ${formatarData(aprovacao.respondido_em)}` : ""}. Obrigado!
              </p>
              {aprovacao.comentario ? <p className="mt-2 whitespace-pre-line text-sm">{aprovacao.comentario}</p> : null}
            </div>
          ) : !aprovacao?.expirada ? (
            <div className="flex flex-col gap-3">
              <label className="flex flex-col gap-2">
                <span className="text-sm font-medium">Seu nome</span>
                <input
                  value={nome}
                  onChange={(evento) => setNome(evento.target.value)}
                  maxLength={60}
                  autoComplete="name"
                  className="rounded-xl border border-borda bg-ink px-4 py-3 outline-none focus:border-violeta"
                />
              </label>
              {pedindoAjuste ? (
                <>
                  <label className="flex flex-col gap-2">
                    <span className="text-sm font-medium">O que precisa mudar?</span>
                    <textarea
                      value={comentario}
                      onChange={(evento) => setComentario(evento.target.value)}
                      maxLength={500}
                      rows={4}
                      autoFocus
                      className="rounded-xl border border-borda bg-ink px-4 py-3 outline-none focus:border-violeta"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => responder("ajustes")}
                    disabled={enviando || !nome.trim() || !comentario.trim()}
                    className="botao-cta py-3"
                  >
                    <MessageSquareText className="size-5" aria-hidden /> Enviar pedido de ajuste
                  </button>
                  <button type="button" onClick={() => setPedindoAjuste(false)} className="text-sm text-suave">
                    Voltar
                  </button>
                </>
              ) : (
                <>
                  <button type="button" onClick={() => responder("aprovado")} disabled={enviando || !nome.trim()} className="botao-cta py-3">
                    <Check className="size-5" aria-hidden /> Aprovar
                  </button>
                  <button type="button" onClick={() => setPedindoAjuste(true)} disabled={enviando} className="botao-contorno py-3">
                    <MessageSquareText className="size-5" aria-hidden /> Pedir ajuste
                  </button>
                </>
              )}
            </div>
          ) : null}
          {erro ? (
            <p role="alert" className="flex gap-1.5 text-sm text-vermelho">
              <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden /> {erro}
            </p>
          ) : null}
        </>
      )}
    </main>
  );
}
