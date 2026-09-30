// Formatação de números, tempos e datas para as telas, sempre em pt-BR.

/** 75 → "1:15", 3725 → "1:02:05". */
export function formatarTempo(segundos: number | null | undefined): string {
  if (segundos == null || !Number.isFinite(segundos)) return "--:--";
  const total = Math.max(0, Math.floor(segundos));
  const horas = Math.floor(total / 3600);
  const minutos = Math.floor((total % 3600) / 60);
  const resto = String(total % 60).padStart(2, "0");
  return horas > 0 ? `${horas}:${String(minutos).padStart(2, "0")}:${resto}` : `${minutos}:${resto}`;
}

/** 1536 → "1,5 KB", 2_700_000_000 → "2,5 GB". */
export function formatarBytes(bytes: number): string {
  const unidades = ["bytes", "KB", "MB", "GB", "TB"];
  let valor = bytes;
  let indice = 0;
  while (valor >= 1024 && indice < unidades.length - 1) {
    valor /= 1024;
    indice += 1;
  }
  const casas = indice === 0 || valor >= 100 ? 0 : 1;
  return `${valor.toLocaleString("pt-BR", { maximumFractionDigits: casas, minimumFractionDigits: casas })} ${unidades[indice]}`;
}

export function formatarData(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function porcentagem(parte: number, total: number): number {
  return total > 0 ? Math.min(100, Math.round((parte / total) * 100)) : 0;
}
