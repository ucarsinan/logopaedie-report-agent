// frontend/src/components/WorkflowStepper.tsx
"use client";

import React, { useState, useEffect } from "react";

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
  const [infoDismissed, setInfoDismissed] = useState(false);

  // Re-show info box whenever the step changes
  useEffect(() => {
    setInfoDismissed(false);
  }, [currentStep]);

  return (
    <div style={{ marginBottom: "16px" }}>
      {/* Step-Reihe */}
      <div style={{ display: "flex", alignItems: "center", marginBottom: "10px" }}>
        {steps.map((step, i) => {
          const isDone = i < currentStep;
          const isActive = i === currentStep;

          return (
            <React.Fragment key={i}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                <button
                  onClick={() => isDone && onStepClick?.(i)}
                  disabled={!isDone || !onStepClick}
                  style={{
                    width: "28px",
                    height: "28px",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "11px",
                    fontWeight: "700",
                    border: isDone
                      ? "2px solid var(--accent)"
                      : isActive
                      ? "none"
                      : "2px solid var(--border)",
                    background: isActive ? "var(--accent)" : "transparent",
                    color: isDone ? "var(--accent)" : isActive ? "white" : "var(--muted-foreground)",
                    opacity: !isDone && !isActive ? 0.4 : 1,
                    cursor: isDone && onStepClick ? "pointer" : "default",
                    transition: "all 0.15s ease",
                  }}
                  title={isDone && onStepClick ? `Zurück zu: ${step.label}` : undefined}
                >
                  {isDone ? "✓" : i + 1}
                </button>
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: isActive ? "600" : "400",
                    color: isActive ? "var(--accent)" : "var(--muted-foreground)",
                    opacity: !isDone && !isActive ? 0.4 : 1,
                    textDecoration: isDone ? "line-through" : "none",
                    whiteSpace: "nowrap",
                  }}
                >
                  {step.label}
                </span>
              </div>
              {i < steps.length - 1 && (
                <div
                  style={{
                    flex: 1,
                    height: "2px",
                    background: i < currentStep ? "var(--accent)" : "var(--border)",
                    margin: "0 6px",
                    marginBottom: "14px",
                    opacity: i >= currentStep ? 0.3 : 1,
                    transition: "background 0.2s ease",
                  }}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Info-Box */}
      {!infoDismissed && (
        <div
          style={{
            borderLeft: `3px solid ${steps[currentStep]?.infoVariant === "success" ? "#4ade80" : "var(--accent)"}`,
            border: "1px solid var(--border)",
            borderLeftWidth: "3px",
            borderRadius: "0 6px 6px 0",
            padding: "8px 12px",
            background: "var(--surface)",
            display: "flex",
            alignItems: "flex-start",
            gap: "8px",
          }}
        >
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: "13px", fontWeight: "600", margin: "0 0 2px 0", color: "var(--foreground)" }}>
              {steps[currentStep]?.infoTitle}
            </p>
            <p style={{ fontSize: "11px", color: "var(--muted-foreground)", margin: 0, lineHeight: "1.5" }}>
              {steps[currentStep]?.infoText}
            </p>
          </div>
          <button
            onClick={() => setInfoDismissed(true)}
            style={{
              flexShrink: 0,
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--muted-foreground)",
              fontSize: "14px",
              lineHeight: 1,
              padding: "0 2px",
              marginTop: "1px",
            }}
            title="Hinweis ausblenden"
            aria-label="Hinweis ausblenden"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
