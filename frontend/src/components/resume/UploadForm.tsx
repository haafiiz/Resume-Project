import { useRef, useState } from "react";

import { ApiError, uploadResume } from "../../api/resumes";

interface UploadFormProps {
  onUploaded: (resumeId: string) => void;
}

export default function UploadForm({ onUploaded }: UploadFormProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    setIsUploading(true);
    try {
      const result = await uploadResume(file);
      onUploaded(result.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          void handleFile(e.dataTransfer.files[0]);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload resume file"
        className={[
          "cursor-pointer rounded-lg border-2 border-dashed p-10 text-center transition-colors",
          isDragging ? "border-slate-900 bg-slate-50" : "border-slate-300 bg-white",
        ].join(" ")}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => void handleFile(e.target.files?.[0])}
        />
        {isUploading ? (
          <p className="text-slate-600">Uploading and parsing…</p>
        ) : (
          <>
            <p className="font-medium text-slate-900">
              Drag and drop your resume, or click to browse
            </p>
            <p className="mt-1 text-sm text-slate-500">Supported formats: PDF, DOCX</p>
          </>
        )}
      </div>

      {error && (
        <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}
    </div>
  );
}
