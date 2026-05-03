import type { ReactNode } from "react";
import { BrandLogo } from "@/components/BrandLogo";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div
        data-testid="auth-card"
        className="w-full max-w-md rounded-lg border border-border bg-surface p-8 shadow-lg card-elevated"
      >
        <BrandLogo className="mb-8" />
        {children}
      </div>
    </div>
  );
}
