import Link from "next/link";

export default function OfflinePage() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-xl flex-col items-center justify-center px-6 py-16 text-center">
      <div className="mb-6 rounded-full bg-amber-100 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">
        Offline Mode
      </div>
      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
        Vinyl<span className="text-amber-500">Scrape</span> is temporarily offline
      </h1>
      <p className="mt-4 text-sm text-neutral-600 dark:text-neutral-300 sm:text-base">
        Your cart and recently cached pages can still work. Reconnect to refresh catalog data.
      </p>
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <Link
          href="/"
          className="rounded-xl bg-amber-500 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-amber-600"
        >
          Try catalog again
        </Link>
        <Link
          href="/cart"
          className="rounded-xl border border-neutral-300 px-5 py-3 text-sm font-medium transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
        >
          Open cart
        </Link>
      </div>
    </div>
  );
}
