"use client";

import type { DetailedError, Upload } from "tus-js-client";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

export type EstadoEnvio = "preparando" | "enviando" | "pausado" | "erro";

export type Envio = {
  chave: string;
  nome: string;
  tamanho: number;
  enviado: number;
  estado: EstadoEnvio;
  erro?: string;
  midiaId?: string;
};

// Pedaços abaixo de 10 MB: é o limite de corpo do Next e fica longe dos 100 MB da Cloudflare
const TAMANHO_PEDACO = 8 * 1024 * 1024;
// Se a internet cair, tenta de novo com espera crescente e continua de onde parou
const ESPERAS_MS = [0, 1_000, 3_000, 5_000, 10_000, 20_000, 30_000, 60_000];

// Mesma lista de core/config.py
const EXTENSOES_ACEITAS = [
  ".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".mts", ".m2ts", ".ts",
  ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac",
];
export const ACEITAR_ARQUIVOS = ["video/*", "audio/*", ...EXTENSOES_ACEITAS].join(",");

function extensaoAceita(nome: string): boolean {
  const indice = nome.lastIndexOf(".");
  return indice >= 0 && EXTENSOES_ACEITAS.includes(nome.slice(indice).toLowerCase());
}

function statusDoErro(erro: Error): number | undefined {
  return (erro as DetailedError).originalResponse?.getStatus() || undefined;
}

/** Tenta de novo em queda de rede e erro temporário do servidor, nunca em recusa (formato, tamanho, espaço). */
function deveTentarDeNovo(erro: DetailedError): boolean {
  const status = statusDoErro(erro);
  if (!status) return true;
  if (status === 409 || status === 423) return true;
  return status >= 500 && status !== 507;
}

function mensagemDoErro(erro: Error): string {
  const status = statusDoErro(erro);
  const corpo = (erro as DetailedError).originalResponse?.getBody()?.trim();
  if (status === 401) return "Sua sessão expirou. Entre de novo e selecione o arquivo para continuar.";
  if (status && corpo && corpo.length < 300 && !corpo.startsWith("<")) return corpo;
  if (!status) return "A conexão caiu. Tente de novo: o envio continua de onde parou.";
  return "O envio falhou. Tente de novo: ele continua de onde parou.";
}

type ContextoEnvios = {
  envios: Envio[];
  /** Muda sempre que uma mídia é criada ou termina de chegar, para as listas recarregarem. */
  versao: number;
  iniciar: (arquivos: File[]) => void;
  pausar: (chave: string) => void;
  retomar: (chave: string) => void;
  cancelar: (chave: string) => void;
  dispensar: (chave: string) => void;
};

const Contexto = createContext<ContextoEnvios | null>(null);

export function ProvedorEnvios({ children }: { children: React.ReactNode }) {
  const [envios, setEnvios] = useState<Envio[]>([]);
  const [versao, setVersao] = useState(0);
  const uploads = useRef(new Map<string, Upload>());

  const atualizar = useCallback((chave: string, campos: Partial<Envio>) => {
    setEnvios((lista) => lista.map((envio) => (envio.chave === chave ? { ...envio, ...campos } : envio)));
  }, []);

  const remover = useCallback((chave: string) => {
    uploads.current.delete(chave);
    setEnvios((lista) => lista.filter((envio) => envio.chave !== chave));
  }, []);

  const iniciar = useCallback(
    async (arquivos: File[]) => {
      const { Upload: ClasseUpload } = await import("tus-js-client");
      for (const arquivo of arquivos) {
        const chave = `${arquivo.name}-${arquivo.size}-${arquivo.lastModified}`;
        if (uploads.current.has(chave)) continue; // este arquivo já está sendo enviado
        const envio: Envio = { chave, nome: arquivo.name, tamanho: arquivo.size, enviado: 0, estado: "preparando" };
        if (!extensaoAceita(arquivo.name)) {
          envio.estado = "erro";
          envio.erro = "Formato não aceito. Envie um vídeo (MP4, MOV, MKV...) ou um áudio (MP3, WAV, M4A...).";
        }
        setEnvios((lista) => [envio, ...lista.filter((item) => item.chave !== chave)]);
        if (envio.estado === "erro") continue;

        const upload: Upload = new ClasseUpload(arquivo, {
          endpoint: "/api/uploads",
          chunkSize: TAMANHO_PEDACO,
          retryDelays: ESPERAS_MS,
          metadata: { filename: arquivo.name, filetype: arquivo.type },
          storeFingerprintForResuming: true,
          removeFingerprintOnSuccess: true,
          onShouldRetry: deveTentarDeNovo,
          onUploadUrlAvailable: () => {
            atualizar(chave, { estado: "enviando", midiaId: upload.url?.split("/").pop() });
            setVersao((valor) => valor + 1);
          },
          onProgress: (enviado, total) => atualizar(chave, { enviado, tamanho: total, estado: "enviando" }),
          onSuccess: () => {
            remover(chave);
            setVersao((valor) => valor + 1);
          },
          onError: (erro) => atualizar(chave, { estado: "erro", erro: mensagemDoErro(erro) }),
        });
        uploads.current.set(chave, upload);
        const anteriores = await upload.findPreviousUploads();
        if (anteriores.length > 0) upload.resumeFromPreviousUpload(anteriores[0]);
        upload.start();
      }
    },
    [atualizar, remover],
  );

  const pausar = useCallback(
    (chave: string) => {
      uploads.current.get(chave)?.abort();
      atualizar(chave, { estado: "pausado" });
    },
    [atualizar],
  );

  const retomar = useCallback(
    (chave: string) => {
      const upload = uploads.current.get(chave);
      if (!upload) return;
      atualizar(chave, { estado: "enviando", erro: undefined });
      upload.start();
    },
    [atualizar],
  );

  const cancelar = useCallback(
    (chave: string) => {
      const upload = uploads.current.get(chave);
      remover(chave);
      upload
        ?.abort(true)
        .catch(() => undefined)
        .finally(() => setVersao((valor) => valor + 1));
    },
    [remover],
  );

  // Avisa antes de fechar a aba no meio de um envio
  const enviando = envios.some((envio) => envio.estado === "enviando" || envio.estado === "preparando");
  useEffect(() => {
    if (!enviando) return;
    const avisar = (evento: BeforeUnloadEvent) => evento.preventDefault();
    window.addEventListener("beforeunload", avisar);
    return () => window.removeEventListener("beforeunload", avisar);
  }, [enviando]);

  return (
    <Contexto.Provider
      value={{
        envios,
        versao,
        iniciar: (arquivos) => void iniciar(arquivos),
        pausar,
        retomar,
        cancelar,
        dispensar: remover,
      }}
    >
      {children}
    </Contexto.Provider>
  );
}

export function useEnvios(): ContextoEnvios {
  const contexto = useContext(Contexto);
  if (!contexto) throw new Error("useEnvios precisa estar dentro de ProvedorEnvios");
  return contexto;
}
