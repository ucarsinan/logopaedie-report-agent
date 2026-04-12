"use client";

import { useRef, useState } from "react";
import type { UploadedFile } from "@/types";
import { UploadIcon, FileIcon } from "@/components/icons";

interface PreUploadViewProps {
  uploadedFiles: UploadedFile[];
  consentChecked: boolean;
  onConsentChange: (checked: boolean) => void;
  onFiles: (files: FileList) => void;
  onSkip: () => void;
  onProceed: () => void;
}

function DropZone({ onFiles }: { onFiles: (files: FileList) => void }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragOver(false);
        if (e.dataTransfer.files.length) onFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={`flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-8 py-12 cursor-pointer transition-colors ${
        isDragOver
          ? "border-accent bg-accent-muted"
          : "border-border-strong bg-surface/50 hover:bg-surface"
      }`}
    >
      <UploadIcon />
      <p className="text-sm text-muted-foreground">
        Dateien hierher ziehen oder <span className="text-accent-text">durchsuchen</span>
      </p>
      <p className="text-xs text-muted">PDF, DOCX oder TXT &middot; Max. 10 MB</p>
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
  );
}

export function PreUploadView({
  uploadedFiles,
  consentChecked,
  onConsentChange,
  onFiles,
  onSkip,
  onProceed,
}: PreUploadViewProps) {
  return (
    <>
      {/* Drop zone */}
      <DropZone onFiles={onFiles} />

      {/* File list */}
      {uploadedFiles.length > 0 && (
        <div className="flex flex-col gap-2">
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-widest">
            Hochgeladene Dateien
          </h2>
          {uploadedFiles.map((f, i) => (
            <div
              key={i}
              className="flex items-center gap-3 rounded-lg bg-surface border border-border px-4 py-3 text-sm"
            >
              <FileIcon />
              <span className="text-foreground">{f.filename}</span>
              <span className="text-xs text-muted ml-auto">
                {f.extracted_text.length} Zeichen extrahiert
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Consent checkbox */}
      {uploadedFiles.length > 0 && (
        <label className="flex items-start gap-3 cursor-pointer rounded-lg border border-border px-4 py-3 bg-surface hover:border-accent transition-colors">
          <input
            type="checkbox"
            checked={consentChecked}
            onChange={(e) => onConsentChange(e.target.checked)}
            className="mt-0.5 accent-accent h-4 w-4 shrink-0"
          />
          <span className="text-sm text-muted-foreground">
            Ich erteile die Einwilligung, dass die hochgeladenen Unterlagen
            für die Gesprächsführung und Berichterstellung verwendet werden.
          </span>
        </label>
      )}

      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={onSkip}
          className="px-5 py-2.5 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground hover:border-border-strong transition-colors"
        >
          Ohne Unterlagen starten
        </button>
        {uploadedFiles.length > 0 && (
          <button
            onClick={onProceed}
            disabled={!consentChecked}
            className="px-5 py-2.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors btn-accent-glow disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Mit Einwilligung fortfahren {"\u2192"}
          </button>
        )}
      </div>
    </>
  );
}
