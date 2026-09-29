import type { NextConfig } from "next";

// Endereço da API vista pelo servidor do Next. No Docker é http://api:8000.
const apiUrlInterna = process.env.API_URL_INTERNA ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  // O navegador sempre fala com /api no mesmo endereço do site.
  // Assim o cookie de sessão funciona igual em casa, no túnel e em produção.
  async rewrites() {
    return [{ source: "/api/:caminho*", destination: `${apiUrlInterna}/api/:caminho*` }];
  },
};

export default nextConfig;
