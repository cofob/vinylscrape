import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Page Not Found",
  description: "The page you are looking for does not exist or has been moved.",
  openGraph: {
    title: "Page Not Found | VinylScrape",
    description:
      "The page you are looking for does not exist or has been moved.",
    images: [{ url: "/og/error.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Page Not Found | VinylScrape",
    description:
      "The page you are looking for does not exist or has been moved.",
    images: ["/og/error.png"],
  },
};

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <p className="mb-4 text-6xl font-bold text-amber-500">404</p>
      <h1 className="mb-2 text-2xl font-bold tracking-tight sm:text-3xl">
        Page Not Found
      </h1>
      <p className="mb-8 max-w-md text-neutral-600 dark:text-neutral-400">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        href="/"
        className="rounded-lg bg-amber-500 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-amber-600"
      >
        Back to catalog
      </Link>
    </div>
  );
}
