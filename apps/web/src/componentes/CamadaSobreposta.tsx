"use client";

import Image from "next/image";

import { type PedidoCamada, useCamada } from "@/lib/useCamada";

/** Uma camada de arte (logo ou texto) por cima da prévia, igual à que vai para o vídeo. */
export function CamadaSobreposta({ pedido, visivel = true }: { pedido: PedidoCamada | null; visivel?: boolean }) {
  const url = useCamada(pedido);
  if (!url) return null;
  return (
    <Image
      src={url}
      alt=""
      fill
      unoptimized
      sizes="400px"
      className="pointer-events-none transition-opacity duration-150"
      style={{ opacity: visivel ? 1 : 0 }}
    />
  );
}
