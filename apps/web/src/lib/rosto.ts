import type { QuadroRosto } from "@/lib/tipos";

/** O quadro vigente naquele instante da gravação. O mesmo degrau de core/modelos/rosto.py. */
export function quadroEm(quadros: QuadroRosto[], tempo: number): QuadroRosto | null {
  let vigente: QuadroRosto | null = null;
  for (const quadro of quadros) {
    if (quadro.t <= tempo) vigente = quadro;
    else break;
  }
  return vigente;
}
