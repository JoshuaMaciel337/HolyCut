"use client";

import { Check, CircleAlert, Clock, Copy, MessageCircle, Send } from "lucide-react";
import { useState } from "react";

import { chamarApi, ErroApi } from "@/lib/api";
import { formatarData } from "@/lib/formatar";
import type { Aprovacao, Exportacao } from "@/lib/tipos";

/**
 * Pedir ao pastor ou líder que aprove o vídeo pelo celular: gera um link (válido por 7 dias) para
 * mandar pelo WhatsApp, e mostra a resposta quando ela chega.
 */
export function AprovacaoDoVideo({ exportacao, aoMudar }: { exportacao: Exportacao; aoMudar: (aprovacao: Aprovacao | null) => void }) {
  const [link, setLink] = useState("");
  const [copiado, setCopiado] = useState(false);
  const [erro, setErro] = useState("");
  const aprovacao = exportacao.aprovacao;

  async function pedir() {
    setErro("");
    setCopiado(false);
    try {
      const criada = await chamarApi<{ token: string; aprovacao: Aprovacao }>(`/exportacoes/${exportacao.id}/aprovacao`, {
        metodo: "POST",
        corpo: {},
      });
      setLink(`${window.location.origin}/aprovar/${criada.token}`);
      aoMudar(criada.aprovacao);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível pedir a aprovação.");
    }
  }

  async function cancelar() {
    try {
      await chamarApi(`/exportacoes/${exportacao.id}/aprovacao`, { metodo: "DELETE" });
      setLink("");
      aoMudar(null);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível cancelar o pedido.");
    }
  }

  async function copiar() {
    try {
      await navigator.clipboard.writeText(link);
      setCopiado(true);
    } catch {
      setErro("Não foi possível copiar. Selecione o link e copie.");
    }
  }

  const mensagem = `Pode aprovar este vídeo da igreja antes de postarmos? ${link}`;

  return (
    <div className="flex flex-col gap-2 text-sm" data-aprovacao={aprovacao?.status ?? "nenhuma"}>
      {!aprovacao ? (
        <button type="button" onClick={pedir} className="botao-contorno px-3 py-2 text-sm">
          <Send className="size-4" aria-hidden /> Pedir aprovação
        </button>
      ) : aprovacao.status === "aprovado" ? (
        <p className="flex items-start gap-1.5 text-ciano">
          <Check className="mt-0.5 size-4 shrink-0" aria-hidden />
          Aprovado por {aprovacao.respondido_por} {aprovacao.respondido_em ? `em ${formatarData(aprovacao.respondido_em)}` : ""}
        </p>
      ) : aprovacao.status === "ajustes" ? (
        <div className="rounded-xl border border-amarelo/40 bg-amarelo/10 px-3 py-2">
          <p className="flex items-start gap-1.5 font-semibold">
            <CircleAlert className="mt-0.5 size-4 shrink-0 text-amarelo" aria-hidden /> {aprovacao.respondido_por} pediu ajustes
          </p>
          <p className="mt-1 whitespace-pre-line">{aprovacao.comentario}</p>
          <button type="button" onClick={pedir} className="mt-2 text-xs text-suave underline hover:text-texto">
            Ajustei: pedir de novo
          </button>
        </div>
      ) : aprovacao.expirada ? (
        <p className="flex items-start gap-1.5 text-suave">
          <Clock className="mt-0.5 size-4 shrink-0" aria-hidden /> O link expirou sem resposta.{" "}
          <button type="button" onClick={pedir} className="underline hover:text-texto">
            Pedir de novo
          </button>
        </p>
      ) : (
        <p className="flex items-start gap-1.5 text-suave">
          <Clock className="mt-0.5 size-4 shrink-0" aria-hidden /> Aguardando aprovação{aprovacao.para ? ` de ${aprovacao.para}` : ""}.
        </p>
      )}

      {link && aprovacao?.status === "pendente" ? (
        <div className="flex flex-col gap-2 rounded-xl border border-borda bg-ink p-3">
          <code className="break-all text-xs" data-link-aprovacao>
            {link}
          </code>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={copiar} className="botao-contorno px-3 py-1.5 text-xs">
              {copiado ? <Check className="size-3.5" aria-hidden /> : <Copy className="size-3.5" aria-hidden />} {copiado ? "Copiado" : "Copiar link"}
            </button>
            <a
              href={`https://wa.me/?text=${encodeURIComponent(mensagem)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="botao-contorno px-3 py-1.5 text-xs"
            >
              <MessageCircle className="size-3.5" aria-hidden /> Enviar pelo WhatsApp
            </a>
          </div>
          <p className="text-xs text-suave">Quem abrir o link assiste e aprova sem precisar de conta. Vale por 7 dias.</p>
        </div>
      ) : null}
      {aprovacao?.status === "pendente" && !aprovacao.expirada ? (
        <div className="flex gap-3 text-xs text-suave">
          {!link ? (
            <button type="button" onClick={pedir} className="underline hover:text-texto">
              Gerar outro link
            </button>
          ) : null}
          <button type="button" onClick={cancelar} className="underline hover:text-texto">
            Cancelar pedido
          </button>
        </div>
      ) : null}
      {erro ? <p className="text-xs text-vermelho">{erro}</p> : null}
    </div>
  );
}
