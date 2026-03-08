"use client";

import {
  createContext,
  useCallback,
  useContext,
  useSyncExternalStore,
  type ReactNode,
} from "react";

// ── Types ────────────────────────────────────────────────────────────
export interface CartItem {
  id: string;
  title: string;
  artist: string;
  image_url: string | null;
  price: number | null;
  currency: string;
}

interface CartContextValue {
  items: CartItem[];
  add: (item: CartItem) => void;
  remove: (id: string) => void;
  clear: () => void;
  has: (id: string) => boolean;
  count: number;
  total: number;
}

// ── Helpers ──────────────────────────────────────────────────────────
const STORAGE_KEY = "vinylscrape_cart";
const CART_UPDATED_EVENT = "vinylscrape-cart-updated";
const EMPTY_CART: CartItem[] = [];
let cachedCartRaw: string | null = null;
let cachedCartItems: CartItem[] = EMPTY_CART;

function loadCart(): CartItem[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = localStorage.getItem(STORAGE_KEY);

    if (raw === cachedCartRaw) {
      return cachedCartItems;
    }

    cachedCartRaw = raw;
    cachedCartItems = raw ? (JSON.parse(raw) as CartItem[]) : EMPTY_CART;
    return cachedCartItems;
  } catch {
    cachedCartRaw = null;
    cachedCartItems = EMPTY_CART;
    return EMPTY_CART;
  }
}

function saveCart(items: CartItem[]) {
  try {
    const raw = JSON.stringify(items);
    localStorage.setItem(STORAGE_KEY, raw);
    cachedCartRaw = raw;
    cachedCartItems = items.length > 0 ? items : EMPTY_CART;
  } catch {
    // quota exceeded — silently ignore
  }
}

function emitCartUpdated() {
  if (typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(new Event(CART_UPDATED_EVENT));
}

function subscribe(onStoreChange: () => void) {
  if (typeof window === "undefined") {
    return () => {};
  }

  const handleStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY) {
      onStoreChange();
    }
  };

  window.addEventListener("storage", handleStorage);
  window.addEventListener(CART_UPDATED_EVENT, onStoreChange);

  return () => {
    window.removeEventListener("storage", handleStorage);
    window.removeEventListener(CART_UPDATED_EVENT, onStoreChange);
  };
}

function getCartSnapshot() {
  return loadCart();
}

// ── Context ──────────────────────────────────────────────────────────
const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const items = useSyncExternalStore(subscribe, getCartSnapshot, () => EMPTY_CART);

  const add = useCallback((item: CartItem) => {
    const currentItems = loadCart();

    if (currentItems.some((existingItem) => existingItem.id === item.id)) {
      return;
    }

    saveCart([...currentItems, item]);
    emitCartUpdated();
  }, []);

  const remove = useCallback((id: string) => {
    saveCart(loadCart().filter((item) => item.id !== id));
    emitCartUpdated();
  }, []);

  const clear = useCallback(() => {
    saveCart([]);
    emitCartUpdated();
  }, []);

  const has = useCallback(
    (id: string) => items.some((i) => i.id === id),
    [items],
  );

  const count = items.length;
  const total = items.reduce((sum, i) => sum + (Number(i.price) || 0), 0);

  return (
    <CartContext.Provider value={{ items, add, remove, clear, has, count, total }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within <CartProvider>");
  return ctx;
}
