"use client";

import { useEffect, useState } from "react";

import { chamarApi } from "@/lib/api";
import type { Sistema } from "@/lib/tipos";

const INTERVALO_MS = 15_000;

/** Workers online e modo de IA, atualizado a cada 15 segundos. */
export function useSistema(): Sistema | null {
  const [sistema, setSistema] = useState<Sistema | null>(null);

  useEffect(() => {
    const atualizar = () =>
      chamarApi<Sistema>("/sistema")
        .then(setSistema)
        .catch(() => setSistema(null));
    atualizar();
    const intervalo = setInterval(atualizar, INTERVALO_MS);
    return () => clearInterval(intervalo);
  }, []);

  return sistema;
}
