import type { NextConfig } from "next";

// Endereço da API vista pelo servidor do Next. No Docker é http://api:8000.
const apiUrlInterna = process.env.API_URL_INTERNA ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  experimental: {
    // Com o proxy.ts, o Next guarda o corpo de toda requisição na memória e corta em 10 MB,
    // inclusive o que vai para /api (medido). A música da biblioteca vai até 40 MB num envio só.
    // Os vídeos não dependem disso: vão pelo tus em pedaços de 8 MB.
    proxyClientMaxBodySize: "45mb",
  },
  // O navegador sempre fala com /api no mesmo endereço do site.
  // Assim o cookie de sessão funciona igual em casa, no túnel e em produção.
  async rewrites() {
    return [{ source: "/api/:caminho*", destination: `${apiUrlInterna}/api/:caminho*` }];
  },
};

export default nextConfig;
