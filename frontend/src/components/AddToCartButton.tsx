"use client";

import { useState } from "react";
import { useCart, type CartItem } from "@/lib/cart";

const AVAILABILITY_WARNING_STORAGE_KEY = "availability-warning-seen";

interface AddToCartButtonProps {
  item: CartItem;
  /** Compact mode for card grid (icon only) */
  compact?: boolean;
  warningMessage?: string;
}

export default function AddToCartButton({
  item,
  compact,
  warningMessage,
}: AddToCartButtonProps) {
  const { add, remove, has } = useCart();
  const inCart = has(item.id);
  const [isWarningOpen, setIsWarningOpen] = useState(false);

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault(); // prevent Link navigation when inside VinylCard
    e.stopPropagation();
    if (inCart) {
      remove(item.id);
    } else {
      add(item);
      if (
        warningMessage &&
        typeof window !== "undefined" &&
        !window.localStorage.getItem(AVAILABILITY_WARNING_STORAGE_KEY)
      ) {
        setIsWarningOpen(true);
      }
    }
  };

  const dismissWarning = () => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(AVAILABILITY_WARNING_STORAGE_KEY, "true");
    }

    setIsWarningOpen(false);
  };

  if (compact) {
    return (
      <button
        onClick={handleClick}
        title={inCart ? "Remove from cart" : "Add to cart"}
        className={`p-1.5 rounded-lg transition-colors ${
          inCart
            ? "bg-amber-500 text-white hover:bg-amber-600"
            : "bg-neutral-100 dark:bg-neutral-800 text-neutral-500 hover:bg-amber-100 hover:text-amber-600 dark:hover:bg-amber-900/30 dark:hover:text-amber-400"
        }`}
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
          {inCart ? (
            // Check icon
            <path d="M20 6 9 17l-5-5" />
          ) : (
            // Plus icon
            <>
              <path d="M12 5v14" />
              <path d="M5 12h14" />
            </>
          )}
        </svg>
      </button>
    );
  }

  return (
    <>
      <button
        onClick={handleClick}
        className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
          inCart
            ? "bg-amber-500 text-white hover:bg-amber-600"
            : "bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 hover:bg-neutral-700 dark:hover:bg-neutral-200"
        }`}
      >
        {inCart ? "In cart" : "Add to cart"}
      </button>

      {isWarningOpen && warningMessage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-md rounded-2xl border border-amber-200 bg-white p-5 shadow-2xl dark:border-amber-900/40 dark:bg-neutral-900">
            <p className="text-sm font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">
              Availability warning
            </p>
            <p className="mt-3 text-sm text-neutral-700 dark:text-neutral-300">
              {warningMessage}
            </p>
            <div className="mt-5 flex justify-end">
              <button
                onClick={dismissWarning}
                className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-600"
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
