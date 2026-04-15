import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 dark:bg-neutral-950 p-4">
      <div
        data-testid="auth-card"
        className="w-full max-w-md rounded-2xl bg-white dark:bg-neutral-900 shadow-lg p-8"
      >
        {children}
      </div>
    </div>
  );
}
