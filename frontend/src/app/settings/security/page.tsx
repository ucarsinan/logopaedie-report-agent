"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { PasswordChangeForm } from "@/features/auth/components/PasswordChangeForm";
import { TwoFactorSetup } from "@/features/auth/components/TwoFactorSetup";
import { ActiveSessionsList } from "@/features/auth/components/ActiveSessionsList";

export default function SecurityPage() {
  const { state } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (state.status === "unauthenticated") {
      router.replace("/login");
    }
  }, [state, router]);

  if (state.status !== "authenticated") {
    return null;
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-10">
      <section>
        <h2 className="text-xl font-semibold mb-4">Passwort ändern</h2>
        <PasswordChangeForm />
      </section>
      <section>
        <h2 className="text-xl font-semibold mb-4">Zwei-Faktor-Authentifizierung</h2>
        <TwoFactorSetup />
      </section>
      <section>
        <h2 className="text-xl font-semibold mb-4">Aktive Sitzungen</h2>
        <ActiveSessionsList />
      </section>
    </div>
  );
}
