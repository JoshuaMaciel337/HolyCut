export function BarraProgresso({ valor, erro = false, rotulo }: { valor: number; erro?: boolean; rotulo: string }) {
  return (
    <div
      className="h-2 overflow-hidden rounded-full bg-ink"
      role="progressbar"
      aria-label={rotulo}
      aria-valuenow={valor}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-full transition-[width] duration-500"
        style={{
          width: `${Math.max(valor, 2)}%`,
          backgroundImage: erro ? "none" : "var(--hc-gradient-cta)",
          backgroundColor: erro ? "var(--hc-red)" : undefined,
        }}
      />
    </div>
  );
}
