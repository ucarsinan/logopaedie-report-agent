"use client";

import { useMemo } from "react";
import { zxcvbn, zxcvbnOptions } from "@zxcvbn-ts/core";
import * as zxcvbnCommon from "@zxcvbn-ts/language-common";

zxcvbnOptions.setOptions({
  graphs: zxcvbnCommon.adjacencyGraphs,
  dictionary: zxcvbnCommon.dictionary,
});

const LABELS = ["Sehr schwach", "Schwach", "Okay", "Gut", "Stark"];
const COLORS = [
  "bg-red-500",
  "bg-orange-500",
  "bg-yellow-500",
  "bg-lime-500",
  "bg-green-500",
];

export function PasswordStrengthMeter({ password }: { password: string }) {
  const score = useMemo(() => (password ? zxcvbn(password).score : 0), [password]);
  const label = LABELS[score];

  return (
    <div className="mt-2">
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={4}
        aria-valuenow={score}
        aria-label="Stärke-Anzeige"
        className="h-2 w-full bg-neutral-200 dark:bg-neutral-800 rounded"
      >
        <div
          className={`h-full rounded ${COLORS[score]}`}
          style={{ width: `${(score / 4) * 100}%` }}
        />
      </div>
      <p className="text-xs mt-1 text-neutral-600 dark:text-neutral-400">
        {label}
      </p>
    </div>
  );
}
