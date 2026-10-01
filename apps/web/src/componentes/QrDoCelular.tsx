"use client";

import { QrCode, X } from "lucide-react";
import { useState } from "react";

import { chamarApi, ErroApi } from "@/lib/api";
import { formatarData } from "@/lib/formatar";

type Link = { caminho: string; expira_em: string };

/** O QR code que leva o vídeo para o celular: aponte a câmera e o download começa, sem entrar na conta. */
export function QrDoCelular({ exportacaoId }: { exportacaoId: string }) {
  const [link, setLink] = useState<{ url: string; expira_em: string } | null>(null);
  const [erro, setErro] = useState("");
  const local = typeof window !== "undefined" && ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname);

  async function gerar() {
    setErro("");
    try {
      const novo = await chamarApi<Link>(`/exportacoes/${exportacaoId}/link-celular`, { metodo: "POST" });
      setLink({ url: `${window.location.origin}${novo.caminho}`, expira_em: novo.expira_em });
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível gerar o QR code.");
    }
  }

  if (!link) {
    return (
      <div>
        <button type="button" onClick={gerar} className="botao-contorno w-full px-3 py-2 text-sm">
          <QrCode className="size-4" aria-hidden /> Baixar no celular
        </button>
        {erro ? <p className="mt-2 text-sm text-vermelho">{erro}</p> : null}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-borda bg-surface p-4 text-center">
      <div className="flex w-full items-center justify-between">
        <p className="text-sm font-semibold">Aponte a câmera do celular</p>
        <button type="button" onClick={() => setLink(null)} aria-label="Fechar o QR code" className="text-suave hover:text-texto">
          <X className="size-4" aria-hidden />
        </button>
      </div>
      {/* eslint-disable-next-line @next/next/no-img-element -- SVG gerado na hora pela API, sem otimização */}
      <img src={`/api/qrcode.svg?texto=${encodeURIComponent(link.url)}`} alt="QR code para baixar o vídeo no celular" width={200} height={200} className="rounded-lg bg-white" />
      <p className="text-xs text-suave">O link vale até {formatarData(link.expira_em)} e só baixa este vídeo. Gerar outro desliga este.</p>
      {local ? (
        <p className="text-xs text-amarelo">
          O celular não encontra &quot;{window.location.host}&quot;. Abra o HolyCut pelo endereço do túnel ou pelo IP deste computador na rede e gere
          o QR de novo.
        </p>
      ) : null}
    </div>
  );
}
