"use client";

import { useState } from "react";

const GRADES: { grade: string; label: string; description: string }[] = [
  {
    grade: "M",
    label: "Mint",
    description: "Perfect, unplayed. Still sealed or indistinguishable from new.",
  },
  {
    grade: "NM",
    label: "Near Mint",
    description: "Nearly perfect. May show the slightest signs of handling.",
  },
  {
    grade: "VG+",
    label: "Very Good Plus",
    description: "Shows some signs of play. Light surface marks, but plays with minimal noise.",
  },
  {
    grade: "VG",
    label: "Very Good",
    description: "Noticeable marks and light scratches. Some surface noise during quiet passages.",
  },
  {
    grade: "G+",
    label: "Good Plus",
    description: "Heavily played. Significant surface noise throughout.",
  },
  {
    grade: "G",
    label: "Good",
    description: "Very heavy wear. Still plays through but with consistent noise.",
  },
  {
    grade: "F",
    label: "Fair",
    description: "Barely playable. Distortion and skipping likely.",
  },
  {
    grade: "P",
    label: "Poor",
    description: "Damaged beyond listenable use. Collectible only.",
  },
];

export default function ConditionBadge({ condition }: { condition: string }) {
  const [open, setOpen] = useState(false);

  const current = GRADES.find(
    (g) => g.grade.toLowerCase() === condition.toLowerCase()
  );

  return (
    <span className="relative inline-flex items-center gap-1.5">
      <span>{condition}</span>
      {current && (
        <span className="text-neutral-400 text-xs italic">({current.label})</span>
      )}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Condition grades explained"
        className="inline-flex items-center justify-center w-4 h-4 rounded-full border border-neutral-400 text-neutral-400 hover:border-amber-500 hover:text-amber-500 transition-colors text-[10px] font-bold leading-none shrink-0"
      >
        ?
      </button>

      {open && (
        <>
          {/* Backdrop */}
          <span
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
          />
          {/* Pop-up */}
          <div className="absolute left-0 top-6 z-20 w-80 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 shadow-xl p-4">
            <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
              Goldmine grading scale
            </p>
            <table className="w-full text-sm">
              <tbody>
                {GRADES.map((g) => (
                  <tr
                    key={g.grade}
                    className={
                      g.grade.toLowerCase() === condition.toLowerCase()
                        ? "bg-amber-50 dark:bg-amber-900/20 rounded"
                        : ""
                    }
                  >
                    <td className="pr-2 py-1 font-mono font-bold w-10 align-top">
                      {g.grade}
                    </td>
                    <td className="pr-2 py-1 font-medium align-top w-28 text-neutral-700 dark:text-neutral-300">
                      {g.label}
                    </td>
                    <td className="py-1 text-neutral-500 dark:text-neutral-400 text-xs">
                      {g.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </span>
  );
}
