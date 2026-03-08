"use client";

import { useEffect, useRef, useState } from "react";

export default function PwaController() {
  const [updateReady, setUpdateReady] = useState(false);
  const [isOffline, setIsOffline] = useState(
    () => typeof window !== "undefined" && !window.navigator.onLine,
  );
  const hasReloadedRef = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  useEffect(() => {
    if (!("serviceWorker" in navigator)) {
      return;
    }

    const registerServiceWorker = async () => {
      try {
        const registration = await navigator.serviceWorker.register("/sw.js", {
          scope: "/",
        });

        const markUpdateReady = () => {
          if (registration.waiting) {
            setUpdateReady(true);
          }
        };

        markUpdateReady();

        registration.addEventListener("updatefound", () => {
          const installingWorker = registration.installing;

          if (!installingWorker) {
            return;
          }

          installingWorker.addEventListener("statechange", () => {
            if (installingWorker.state === "installed" && navigator.serviceWorker.controller) {
              markUpdateReady();
            }
          });
        });

        navigator.serviceWorker.addEventListener("controllerchange", () => {
          if (hasReloadedRef.current) {
            return;
          }

          hasReloadedRef.current = true;
          window.location.reload();
        });
      } catch {
        // Ignore service worker registration errors in unsupported environments.
      }
    };

    registerServiceWorker();
  }, []);

  const applyUpdate = async () => {
    const registration = await navigator.serviceWorker.getRegistration();
    registration?.waiting?.postMessage({ type: "SKIP_WAITING" });
  };

  if (!updateReady && !isOffline) {
    return null;
  }

  return (
    <div className="fixed inset-x-0 bottom-4 z-50 flex justify-center px-4">
      <div className="flex max-w-md items-center gap-3 rounded-full border border-neutral-300 bg-white px-4 py-3 text-sm shadow-lg dark:border-neutral-700 dark:bg-neutral-900">
        <span className="flex-1 text-neutral-700 dark:text-neutral-200">
          {updateReady ? "An app update is ready." : "You are offline. Cached pages stay available."}
        </span>
        {updateReady && (
          <button
            onClick={applyUpdate}
            className="rounded-full bg-amber-500 px-3 py-1.5 font-medium text-white transition-colors hover:bg-amber-600"
          >
            Refresh
          </button>
        )}
      </div>
    </div>
  );
}
