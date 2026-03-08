import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/cart", "/offline"],
      },
    ],
    sitemap: "https://vinylscrape.cfb.wtf/sitemap.xml",
  };
}
