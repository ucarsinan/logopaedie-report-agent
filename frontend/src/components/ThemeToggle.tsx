"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div className="w-8 h-[18px]" aria-hidden="true" />;
  }

  const isDark = resolvedTheme === "dark";

  return (
    <div className="flex items-center gap-1.5" title={isDark ? "Light Mode aktivieren" : "Dark Mode aktivieren"}>
      <span className="text-[12px] select-none leading-none" style={{ opacity: isDark ? 0.4 : 1, transition: "opacity 0.2s" }}>☀</span>
      <button
        onClick={() => setTheme(isDark ? "light" : "dark")}
        role="switch"
        aria-checked={isDark}
        aria-label={isDark ? "Light Mode aktivieren" : "Dark Mode aktivieren"}
        className="relative w-8 h-[18px] rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        style={{ background: isDark ? "var(--accent)" : "var(--border-strong)" }}
      >
        <span
          className="absolute top-[2px] left-0 w-[14px] h-[14px] rounded-full bg-white shadow-sm transition-transform duration-200"
          style={{ transform: isDark ? "translateX(16px)" : "translateX(2px)" }}
        />
      </button>
      <span className="text-[12px] select-none leading-none" style={{ opacity: isDark ? 1 : 0.4, transition: "opacity 0.2s" }}>🌙</span>
    </div>
  );
}
