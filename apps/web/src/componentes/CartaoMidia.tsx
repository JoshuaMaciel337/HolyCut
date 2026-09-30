"use client";

import { AudioLines, CircleAlert, Film, Pause, Play, Trash2, X } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { BarraProgresso } from "@/componentes/BarraProgresso";
import { type Envio, useEnvios } from "@/lib/envios";
import { formatarBytes, formatarTempo, porcentagem } from "@/lib/formatar";
import type { Midia } from "@/lib/tipos";

function resolucao(midia: Midia): string {
  if (!midia.video) return "Áudio";
  const lado = Math.min(midia.video.largura, midia.video.altura);
  const fps = midia.video.fps ? ` · ${Math.round(midia.video.fps)} fps` : "";
  const emPe = midia.video.altura > midia.video.largura ? " · em pé" : "";
  return `${lado}p${fps}${emPe}`;
}

function BotaoIcone({ rotulo, onClick, children }: { rotulo: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={rotulo}
      aria-label={rotulo}
      className="flex size-8 items-center justify-center rounded-full border border-borda text-suave transition hover:border-suave hover:text-texto"
    >
      {children}
    </button>
  );
}

function SituacaoEnvio({ envio }: { envio: Envio }) {
  const { pausar, retomar, cancelar } = useEnvios();
  const valor = porcentagem(envio.enviado, envio.tamanho);
  const texto = envio.estado === "erro" ? envio.erro : envio.estado === "pausado" ? `Pausado em ${valor}%` : `Enviando ${valor}%`;
  return (
    <>
      <BarraProgresso valor={valor} erro={envio.estado === "erro"} rotulo="Envio" />
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className={`text-sm ${envio.estado === "erro" ? "text-vermelho" : "text-suave"}`}>{texto}</p>
          {envio.estado !== "erro" ? (
            <p className="text-xs tabular-nums text-suave">
              {formatarBytes(envio.enviado)} de {formatarBytes(envio.tamanho)}
            </p>
          ) : null}
        </div>
        <div className="flex shrink-0 gap-1.5">
          {envio.estado === "enviando" || envio.estado === "preparando" ? (
            <BotaoIcone rotulo="Pausar" onClick={() => pausar(envio.chave)}>
              <Pause className="size-4" aria-hidden />
            </BotaoIcone>
          ) : (
            <BotaoIcone rotulo={envio.estado === "erro" ? "Tentar de novo" : "Continuar"} onClick={() => retomar(envio.chave)}>
              <Play className="size-4" aria-hidden />
            </BotaoIcone>
          )}
          <BotaoIcone rotulo="Cancelar envio" onClick={() => cancelar(envio.chave)}>
            <X className="size-4" aria-hidden />
          </BotaoIcone>
        </div>
      </div>
    </>
  );
}

export function CartaoMidia({ midia, envio, aoExcluir }: { midia: Midia; envio?: Envio; aoExcluir: (midia: Midia) => void }) {
  const pronta = midia.status === "pronta";
  const temCapa = midia.arquivos.includes("capa.jpg");
  const excluir = (
    <BotaoIcone rotulo="Excluir" onClick={() => aoExcluir(midia)}>
      <Trash2 className="size-4" aria-hidden />
    </BotaoIcone>
  );

  const miniatura = (
    <div className="relative aspect-video bg-ink">
      {temCapa ? (
        <Image
          src={`/api/midias/${midia.id}/arquivos/capa.jpg`}
          alt=""
          fill
          unoptimized
          sizes="(min-width: 1024px) 280px, 50vw"
          className="object-cover"
        />
      ) : (
        <div className="flex size-full items-center justify-center text-suave">
          {midia.video === null && midia.status === "pronta" ? (
            <AudioLines className="size-10" aria-hidden />
          ) : (
            <Film className="size-10" aria-hidden />
          )}
        </div>
      )}
      {midia.duracao ? (
        <span className="absolute bottom-2 right-2 rounded-md bg-black/75 px-1.5 py-0.5 text-xs font-medium">
          {formatarTempo(midia.duracao)}
        </span>
      ) : null}
    </div>
  );

  let situacao: React.ReactNode;
  if (envio) {
    situacao = <SituacaoEnvio envio={envio} />;
  } else if (midia.status === "enviando") {
    const valor = porcentagem(midia.bytes_recebidos, midia.tamanho_total);
    situacao = (
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-suave">
          Envio interrompido em {valor}%. Escolha o mesmo arquivo de novo para continuar.
        </p>
        {excluir}
      </div>
    );
  } else if (midia.status === "processando") {
    const progresso = midia.processamento?.progresso ?? 0;
    situacao = (
      <>
        <BarraProgresso valor={progresso} rotulo="Preparação" />
        <p className="text-sm text-suave">
          {midia.processamento?.mensagem || "Na fila"} · {progresso}%
        </p>
      </>
    );
  } else if (midia.status === "erro") {
    situacao = (
      <div className="flex items-start justify-between gap-2">
        <p className="flex gap-1.5 text-sm text-vermelho">
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
          {midia.erro || "Não foi possível preparar esta gravação."}
        </p>
        {excluir}
      </div>
    );
  } else {
    situacao = (
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-suave">
          {resolucao(midia)} · {formatarBytes(midia.tamanho_total)}
        </p>
        {excluir}
      </div>
    );
  }

  return (
    <li className="cartao flex flex-col overflow-hidden">
      {pronta ? (
        <Link href={`/app/midias/${midia.id}`} className="group block focus-visible:outline-2 focus-visible:outline-laranja">
          {miniatura}
          <p className="truncate px-4 pt-4 font-medium group-hover:text-laranja" title={midia.nome}>
            {midia.nome}
          </p>
        </Link>
      ) : (
        <>
          {miniatura}
          <p className="truncate px-4 pt-4 font-medium" title={midia.nome}>
            {midia.nome}
          </p>
        </>
      )}
      <div className="flex flex-1 flex-col justify-end gap-2 p-4 pt-2">{situacao}</div>
    </li>
  );
}
