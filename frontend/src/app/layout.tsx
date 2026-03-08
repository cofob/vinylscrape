import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import Providers from "@/components/Providers";
import CartIcon from "@/components/CartIcon";
import PwaController from "@/components/PwaController";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://vinylscrape.cfb.wtf"),
  title: {
    template: "%s | VinylScrape",
    default: "VinylScrape — Search Vinyl Records from Georgian Shops",
  },
  description:
    "Search and compare vinyl records from Georgian shops",
  applicationName: "VinylScrape",
  manifest: "/manifest.webmanifest",
  alternates: {
    canonical: "/",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "VinylScrape",
  },
  formatDetection: {
    telephone: false,
  },
  icons: {
    apple: "/apple-icon",
  },
  openGraph: {
    type: "website",
    siteName: "VinylScrape",
    locale: "en_US",
    url: "https://vinylscrape.cfb.wtf",
    title: "VinylScrape — Search Vinyl Records from Georgian Shops",
    description: "Search and compare vinyl records from Georgian shops",
    images: [{ url: "/og/main.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "VinylScrape",
    description: "Search and compare vinyl records from Georgian shops",
    images: ["/og/main.png"],
  },
};

export const viewport: Viewport = {
  themeColor: "#d97706",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const websiteJsonLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "VinylScrape",
    url: "https://vinylscrape.cfb.wtf",
    potentialAction: {
      "@type": "SearchAction",
      target: "https://vinylscrape.cfb.wtf/?q={search_term_string}",
      "query-input": "required name=search_term_string",
    },
  };

  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen`}
      >
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteJsonLd) }}
        />
        <Providers>
          <PwaController />
          <header className="border-b border-neutral-200 dark:border-neutral-800">
            <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
              <Link href="/" className="text-xl font-bold tracking-tight">
                Vinyl<span className="text-amber-500">Scrape</span>
              </Link>
              <nav className="flex items-center gap-4 text-sm text-neutral-600 dark:text-neutral-400">
                <Link href="/" className="hover:text-foreground transition-colors">
                  Catalog
                </Link>
                <Link href="/about" className="hover:text-foreground transition-colors">
                  About
                </Link>
                <Link href="/docs/api" className="hover:text-foreground transition-colors">
                  API
                </Link>
                <a
                  href="https://github.com/cofob/vinylscrape"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="GitHub repository"
                  className="hover:text-foreground transition-colors"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    className="w-5 h-5"
                    aria-hidden="true"
                  >
                    <path d="M12 2C6.477 2 2 6.477 2 12c0 4.418 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.009-.868-.013-1.703-2.782.604-3.369-1.342-3.369-1.342-.454-1.154-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0 1 12 6.836a9.59 9.59 0 0 1 2.504.337c1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.163 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
                  </svg>
                </a>
                <CartIcon />
              </nav>
            </div>
          </header>
          <main>{children}</main>
        </Providers>
      </body>
    </html>
  );
}
