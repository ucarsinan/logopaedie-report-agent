"use client";

import { useRef, useState } from "react";
import type { UploadedFile } from "@/types";
import { FileIcon } from "@/components/icons";

interface PreUploadViewProps {
  uploadedFiles: UploadedFile[];
  consentChecked: boolean;
  onConsentChange: (checked: boolean) => void;
  onFiles: (files: FileList) => void;
  onSkip: () => void;
  onProceed: () => void;
}

export function PreUploadView({
  uploadedFiles,
  consentChecked,
  onConsentChange,
  onFiles,
  onSkip,
  onProceed,
}: PreUploadViewProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="mx-auto w-full max-w-lg space-y-4">
      {/* Compact header */}
      <div className="text-center">
        <h2 className="text-base font-semibold text-foreground">
          Vorhandene Unterlagen
        </h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Laden Sie frühere Berichte oder Diagnostik hoch — der Assistent berücksichtigt diese im Gespräch.
        </p>
      </div>

      {/* Compact drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          if (e.dataTransfer.files.length) onFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={[
          "flex items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-8 cursor-pointer transition-colors",
          isDragOver
            ? "border-accent bg-accent/5"
            : "border-border-strong bg-surface/50 hover:bg-surface hover:border-border-strong/80",
        ].join(" ")}
      >
        <svg className="size-6 shrink-0 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
        </svg>
        <div>
          <p className="text-sm text-foreground">
            Dateien hierher ziehen oder <span className="text-accent font-medium">durchsuchen</span>
          </p>
          <p className="text-xs text-muted-foreground">PDF, DOCX oder TXT · Max. 10 MB</p>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          onChange={(e) => {
            if (e.target.files?.length) onFiles(e.target.files);
          }}
          className="hidden"
        />
      </div>

      {/* Uploaded files */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-1.5">
          {uploadedFiles.map((f, i) => (
            <div
              key={i}
              className="flex items-center gap-2.5 rounded-lg bg-surface border border-border px-3 py-2 text-sm"
            >
              <FileIcon />
              <span className="flex-1 truncate text-foreground">{f.filename}</span>
              <span className="text-xs text-muted-foreground shrink-0">
                {f.extracted_text.length} Zeichen
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Consent + actions */}
      {uploadedFiles.length > 0 && (
        <label className="flex items-start gap-2.5 cursor-pointer rounded-lg border border-border px-3 py-2.5 bg-surface hover:border-accent/50 transition-colors">
          <input
            type="checkbox"
            checked={consentChecked}
            onChange={(e) => onConsentChange(e.target.checked)}
            className="mt-0.5 accent-accent size-4 shrink-0"
          />
          <span className="text-xs text-muted-foreground leading-relaxed">
            Ich erteile die Einwilligung, dass die hochgeladenen Unterlagen
            für die Gesprächsführung und Berichterstellung verwendet werden.
          </span>
        </label>
      )}

      <div className="flex gap-2.5 justify-center items-center">
        <button
          onClick={onSkip}
          className="px-4 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Ohne Unterlagen fortfahren
        </button>
        {uploadedFiles.length > 0 && (
          <button
            onClick={onProceed}
            disabled={!consentChecked}
            className="px-5 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Weiter {"\u2192"}
          </button>
        )}
      </div>
    </div>
  );
}
