"use client";

import React, { useCallback, useRef, useState } from "react";

/**
 * Props for the FileUpload component.
 */
interface FileUploadProps {
  /** Callback invoked with the extracted text content of the uploaded file. */
  onTextExtracted: (text: string) => void;
  /** Whether the parent is currently processing a request. */
  isLoading: boolean;
}

/**
 * Accessible drag-and-drop file upload component.
 *
 * Supports `.txt` and `.md` files via drag-and-drop or the native file
 * picker. Includes full ARIA labelling, keyboard navigation, and visual
 * feedback for drag state.
 */
export default function FileUpload({
  onTextExtracted,
  isLoading,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [fileName, setFileName] = useState<string>("");
  const [error, setError] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const MAX_FILE_SIZE = 500_000; // 500 KB

  /** Read a File object and pass its text content upstream. */
  const processFile = useCallback(
    (file: File) => {
      setError("");

      if (file.size > MAX_FILE_SIZE) {
        setError("File too large. Maximum size is 500 KB.");
        return;
      }

      const validTypes = [
        "text/plain",
        "text/markdown",
        "application/octet-stream",
      ];
      const validExtensions = [".txt", ".md"];
      const hasValidExtension = validExtensions.some((ext) =>
        file.name.toLowerCase().endsWith(ext)
      );

      if (!validTypes.includes(file.type) && !hasValidExtension) {
        setError("Please upload a .txt or .md file.");
        return;
      }

      const reader = new FileReader();
      reader.onload = (event) => {
        const text = event.target?.result as string;
        if (text && text.trim().length >= 50) {
          setFileName(file.name);
          onTextExtracted(text);
        } else {
          setError("Contract text must be at least 50 characters.");
        }
      };
      reader.onerror = () => setError("Failed to read file. Please try again.");
      reader.readAsText(file);
    },
    [onTextExtracted]
  );

  /* ---- Drag-and-drop handlers ---- */

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  /** Open the native file picker on keyboard activation (Enter / Space). */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        fileInputRef.current?.click();
      }
    },
    []
  );

  return (
    <div className="w-full">
      {/* Hidden native file input */}
      <input
        ref={fileInputRef}
        id="contract-file-input"
        type="file"
        accept=".txt,.md"
        className="sr-only"
        onChange={handleFileSelect}
        aria-label="Upload contract file"
        disabled={isLoading}
      />

      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Drag and drop a contract file here, or press Enter to browse"
        aria-describedby="upload-instructions"
        aria-disabled={isLoading}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => !isLoading && fileInputRef.current?.click()}
        onKeyDown={handleKeyDown}
        className={`
          glass-card cursor-pointer p-10 text-center
          transition-all duration-300 ease-out
          ${isDragging
            ? "border-brand-400/60 bg-brand-500/10 scale-[1.01] shadow-brand-500/20"
            : "hover:border-white/10"
          }
          ${isLoading ? "opacity-50 pointer-events-none" : ""}
        `}
      >
        {/* Upload icon */}
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-500/10">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={`h-8 w-8 text-brand-400 transition-transform duration-300 ${
              isDragging ? "scale-110 -translate-y-1" : ""
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
            />
          </svg>
        </div>

        <p className="text-lg font-semibold text-surface-200">
          {isDragging ? "Drop your contract here" : "Upload Contract"}
        </p>

        <p
          id="upload-instructions"
          className="mt-2 text-sm text-surface-400"
        >
          Drag & drop a <span className="font-mono text-brand-300">.txt</span>{" "}
          or <span className="font-mono text-brand-300">.md</span> file, or{" "}
          <span className="text-brand-400 underline underline-offset-2">
            click to browse
          </span>
        </p>

        <p className="mt-1 text-xs text-surface-500">
          Maximum file size: 500 KB
        </p>

        {/* Success state */}
        {fileName && !error && (
          <div
            className="mt-4 inline-flex items-center gap-2 rounded-lg
                        bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400
                        ring-1 ring-emerald-500/25 animate-fade-in"
            role="status"
            aria-live="polite"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            {fileName}
          </div>
        )}

        {/* Error state */}
        {error && (
          <div
            className="mt-4 inline-flex items-center gap-2 rounded-lg
                        bg-red-500/10 px-4 py-2 text-sm text-red-400
                        ring-1 ring-red-500/25 animate-fade-in"
            role="alert"
            aria-live="assertive"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
              />
            </svg>
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
