"use client";

export interface StepConfig {
  label: string;
  infoTitle: string;
  infoText: string;
  infoVariant?: "default" | "success";
}

interface WorkflowStepperProps {
  steps: StepConfig[];
  currentStep: number;
  onStepClick?: (index: number) => void;
}

export function WorkflowStepper({ steps, currentStep, onStepClick }: WorkflowStepperProps) {
  return (
    <nav className="flex items-center gap-1.5 text-xs font-medium select-none">
      {steps.map((step, i) => {
        const isDone = i < currentStep;
        const isActive = i === currentStep;
        const clickable = isDone && !!onStepClick;

        return (
          <div key={i} className="flex items-center gap-1.5">
            {i > 0 && (
              <span className={`text-[10px] ${isDone ? "text-accent" : "text-border-strong"}`}>
                /
              </span>
            )}
            <button
              onClick={() => clickable && onStepClick?.(i)}
              disabled={!clickable}
              className={[
                "inline-flex items-center gap-1 rounded-full px-2.5 py-1 transition-all duration-150",
                isActive && "bg-accent text-white",
                isDone && "text-accent hover:bg-accent/10 cursor-pointer",
                !isDone && !isActive && "text-muted-foreground/40 cursor-default",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              {isDone && (
                <svg className="size-3" viewBox="0 0 16 16" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
              {step.label}
            </button>
          </div>
        );
      })}
    </nav>
  );
}
