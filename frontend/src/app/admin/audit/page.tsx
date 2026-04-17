"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { AuditLogTable } from "@/features/auth/components/AuditLogTable";

export default function AdminAuditPage() {
  const { state } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (state.status === "authenticated" && state.user.role !== "admin") {
      router.replace("/");
    }
  }, [state, router]);

  if (state.status !== "authenticated" || state.user.role !== "admin") {
    return null;
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-6">Audit-Log</h1>
      <AuditLogTable />
    </div>
  );
}
