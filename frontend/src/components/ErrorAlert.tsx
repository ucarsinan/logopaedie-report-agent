import { AlertIcon } from "@/components/icons";

interface ErrorAlertProps {
  message: string;
}

export function ErrorAlert({ message }: ErrorAlertProps) {
  return (
    <div
      role="alert"
      className="rounded-lg bg-error-surface border border-error-border px-5 py-4 text-sm text-error-text flex items-start gap-3 print:hidden"
    >
      <AlertIcon />
      <span>{message}</span>
    </div>
  );
}
