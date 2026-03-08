import type { Metadata } from "next";
import { Suspense } from "react";
import HomeContent from "./HomeContent";

export const metadata: Metadata = {
  title: "Search Vinyl Records from Georgian Shops",
  description:
    "Search and compare vinyl records from Georgian shops. Compare prices, check availability, and find the best deals on vinyl records in Georgia.",
  alternates: {
    canonical: "/",
  },
};

export default function HomePage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-7xl mx-auto px-4 py-8 text-center">
          <div className="animate-pulse space-y-4">
            <div className="h-10 w-48 mx-auto bg-neutral-200 dark:bg-neutral-800 rounded" />
            <div className="h-12 max-w-2xl mx-auto bg-neutral-200 dark:bg-neutral-800 rounded-xl" />
          </div>
        </div>
      }
    >
      <HomeContent />
    </Suspense>
  );
}
