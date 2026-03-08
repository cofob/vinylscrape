"use client";

import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import Image from "next/image";
import Link from "next/link";
import { useCart } from "@/lib/cart";
import { getVinyl } from "@/lib/api";
import PriceTag from "@/components/PriceTag";
import type { VinylDetail } from "@/types/vinyl";

const RETROMANIA_WARNING =
  "Retromania.ge does not report availability status, you should check if items available";

function hasRetromaniaSource(detail: VinylDetail | undefined) {
  return detail?.sources.some((source) => source.source_name.toLowerCase() === "retromania.ge");
}

function formatShopPrice(price: number, currency: string) {
  return `${currency === "GEL" ? "₾" : currency} ${price.toFixed(2)}`;
}

export default function CartPage() {
  const { items, remove, clear, total } = useCart();

  // Fetch full detail (with sources) for every cart item so we can
  // compute per-shop totals.
  const detailQueries = useQueries({
    queries: items.map((item) => ({
      queryKey: ["vinyl", item.id],
      queryFn: () => getVinyl(item.id),
      staleTime: 5 * 60 * 1000,
    })),
  });

  // Build a map id → VinylDetail for successfully loaded items
  const detailMap = useMemo(() => {
    const m = new Map<string, VinylDetail>();
    for (const q of detailQueries) {
      if (q.data) m.set(q.data.id, q.data);
    }
    return m;
  }, [detailQueries]);

  const shopGroups = useMemo(() => {
    const shops = new Map<string, {
      name: string;
      total: number;
      count: number;
      currency: string;
      items: Array<{
        id: string;
        title: string;
        artist: string;
        image_url: string | null;
        price: number;
        currency: string;
        external_url: string;
      }>;
    }>();

    for (const item of items) {
      const detail = detailMap.get(item.id);
      if (!detail) continue;

      for (const src of detail.sources) {
        const entry = shops.get(src.source_name) ?? {
          name: src.source_name,
          total: 0,
          count: 0,
          currency: src.currency,
          items: [],
        };

        entry.total += Number(src.price) || 0;
        entry.count += 1;
        entry.items.push({
          id: item.id,
          title: item.title,
          artist: item.artist,
          image_url: item.image_url,
          price: Number(src.price) || 0,
          currency: src.currency,
          external_url: src.external_url,
        });
        shops.set(src.source_name, entry);
      }
    }

    return [...shops.values()]
      .map((shop) => ({
        ...shop,
        items: [...shop.items].sort((a, b) => a.artist.localeCompare(b.artist) || a.title.localeCompare(b.title)),
      }))
      .sort((a, b) => a.total - b.total);
  }, [items, detailMap]);

  const allLoaded = detailQueries.every((q) => !q.isLoading);
  const hasRetromaniaItems = items.some((item) => hasRetromaniaSource(detailMap.get(item.id)));

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 sm:py-8">
      <h1 className="text-2xl font-bold mb-6">Your Cart</h1>

      {items.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-5xl mb-4">🛒</p>
          <p className="text-neutral-500 mb-4">Your cart is empty</p>
          <Link
            href="/"
            className="inline-block px-4 py-2 rounded-lg bg-amber-500 text-white font-medium text-sm hover:bg-amber-600 transition-colors"
          >
            Browse catalog
          </Link>
        </div>
      ) : (
        <>
          {allLoaded && hasRetromaniaItems && (
            <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-200">
              {RETROMANIA_WARNING}
            </div>
          )}

          {allLoaded && shopGroups.length > 0 && (
            <div className="space-y-4 sm:space-y-6">
              {shopGroups.map((shop) => (
                <div
                  key={shop.name}
                  className="border border-neutral-200 dark:border-neutral-800 rounded-xl overflow-hidden"
                >
                  <div className="flex flex-col gap-2 bg-neutral-50 px-4 py-3 dark:bg-neutral-800/50 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
                    <div>
                      <h2 className="text-sm font-semibold">{shop.name}</h2>
                      <p className="text-xs text-neutral-500 dark:text-neutral-400">
                        {shop.count}/{items.length} item{shop.count !== 1 ? "s" : ""}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs uppercase tracking-wide text-neutral-400">Total</p>
                      <p className="font-semibold text-amber-600 dark:text-amber-400">
                        {formatShopPrice(shop.total, shop.currency)}
                      </p>
                    </div>
                  </div>

                  <div className="divide-y divide-neutral-200 dark:divide-neutral-800">
                    {shop.items.map((item) => (
                      <div key={`${shop.name}-${item.id}`} className="bg-white p-4 dark:bg-neutral-900">
                        <div className="flex items-start gap-3 sm:items-center sm:gap-4">
                        <Link
                          href={`/vinyl/${item.id}`}
                          className="relative h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-neutral-100 dark:bg-neutral-800 sm:h-16 sm:w-16"
                        >
                          {item.image_url ? (
                            <Image
                              src={item.image_url}
                              alt={`${item.artist} - ${item.title}`}
                              fill
                              unoptimized
                              className="object-cover"
                              sizes="64px"
                            />
                          ) : (
                            <div className="flex items-center justify-center h-full text-neutral-400 text-xl">
                              ♫
                            </div>
                          )}
                        </Link>

                        <div className="min-w-0 flex-1">
                          <Link
                            href={`/vinyl/${item.id}`}
                            className="hover:text-amber-500 transition-colors"
                          >
                            <p className="text-sm text-neutral-500 dark:text-neutral-400 truncate">
                              {item.artist}
                            </p>
                            <p className="font-medium truncate">{item.title}</p>
                          </Link>
                          <a
                            href={item.external_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-1 inline-block text-xs text-amber-600 hover:underline dark:text-amber-400"
                          >
                            View on shop
                          </a>
                        </div>

                        <div className="hidden shrink-0 text-right sm:block">
                          <PriceTag price={item.price} currency={item.currency} />
                        </div>

                        <button
                          onClick={() => remove(item.id)}
                          title="Remove from cart"
                          className="shrink-0 p-1.5 rounded-lg text-neutral-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth={2}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            className="w-4 h-4"
                          >
                            <path d="M18 6 6 18" />
                            <path d="m6 6 12 12" />
                          </svg>
                        </button>
                        </div>

                        <div className="mt-3 flex items-center justify-between gap-3 sm:hidden">
                          <PriceTag price={item.price} currency={item.currency} />
                          <button
                            onClick={() => remove(item.id)}
                            className="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs text-neutral-600 transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          {!allLoaded && items.length > 0 && (
            <div className="mt-6 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 text-sm text-neutral-500 animate-pulse">
              Loading shop totals...
            </div>
          )}

          {/* Summary */}
          <div className="mt-4 flex flex-col items-stretch justify-between gap-4 rounded-xl border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-800 dark:bg-neutral-900 sm:flex-row sm:items-center">
            <div>
              <p className="text-sm text-neutral-500">
                {items.length} item{items.length !== 1 ? "s" : ""}
              </p>
              <p className="text-xl font-bold">
                Total:{" "}
                <span className="text-amber-600 dark:text-amber-400">
                  ₾ {total.toFixed(2)}
                </span>
              </p>
              <p className="text-xs text-neutral-400">
                Based on lowest price per item
              </p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <button
                onClick={clear}
                className="rounded-lg border border-neutral-300 px-4 py-2 text-sm transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
              >
                Clear cart
              </button>
              <Link
                href="/"
                className="rounded-lg bg-amber-500 px-4 py-2 text-center text-sm font-medium text-white transition-colors hover:bg-amber-600"
              >
                Continue shopping
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
