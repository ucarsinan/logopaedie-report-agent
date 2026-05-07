"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { AuditLogTable } from "@/features/auth/components/AuditLogTable";

export default function AdminAuditPage() {
  const { state } = useAuth();
  const router = useRouter();

  if (state.status === "loading") return null;
  if (state.status === "unauthenticated" || state.user.role !== "admin") {
    router.replace("/");
    return null;
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-6">Audit-Log</h1>
      <AuditLogTable />
    </div>
  );
}
