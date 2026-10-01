import type { MetadataRoute } from "next";

// Permite instalar o HolyCut no celular como um app (PWA)
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "HolyCut",
    short_name: "HolyCut",
    description: "Transforme momentos em histórias.",
    lang: "pt-BR",
    start_url: "/app",
    display: "standalone",
    background_color: "#0B0B0F",
    theme_color: "#0B0B0F",
    icons: [
      { src: "/brand/app-icon/icone-escuro-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/brand/app-icon/icone-escuro-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/brand/app-icon/icone-maskable-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/brand/app-icon/icone-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
