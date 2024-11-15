import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "BenTech",
    short_name: "BenTech",
    description: "アタッチメント式のスマートトイレデバイスをコントロールするアプリ",
    start_url: "/",
    display: "fullscreen",
    background_color: "#ffffff",
    theme_color: "#000000",
    icons: [
      {
        src: "icon-512.png",
        sizes: "512x512",
        type: "image/png",
      }
    ]
  }
}