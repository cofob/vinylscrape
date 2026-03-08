"use client";

import Link from "next/link";
import { useCart } from "@/lib/cart";

export default function CartIcon() {
  const { count, total } = useCart();

  return (
    <Link
      href="/cart"
      className="flex items-center gap-1.5 hover:text-foreground transition-colors"
      title="Cart"
    >
      <div className="relative">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="w-5 h-5"
        >
          <circle cx="8" cy="21" r="1" />
          <circle cx="19" cy="21" r="1" />
          <path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12" />
        </svg>
        {count > 0 && (
          <span className="absolute -top-2 -right-2 bg-amber-500 text-white text-[10px] font-bold w-4 h-4 flex items-center justify-center rounded-full">
            {count > 99 ? "99" : count}
          </span>
        )}
      </div>
      {count > 0 && (
        <span className="text-xs font-semibold text-amber-600 dark:text-amber-400">
          ₾ {total.toFixed(2)}
        </span>
      )}
    </Link>
  );
}
