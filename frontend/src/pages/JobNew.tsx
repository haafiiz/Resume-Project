import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { createJobDescription } from "../api/jobDescriptions";
import { inputClass, labelClass, textareaClass } from "../components/resume/editorStyles";

export default function JobNew() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!description.trim()) {
      setError("Please paste the job description text before saving.");
      return;
    }

    setError(null);
    setIsSaving(true);
    try {
      const job = await createJobDescription({
        title: title.trim() || null,
        company: company.trim() || null,
        description,
      });
      navigate(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save job description.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section>
      <h1 className="text-2xl font-semibold text-slate-900">Add a job description</h1>
      <p className="mt-2 text-slate-600">
        Paste the full job posting text below. You'll be able to extract and
        review its requirements after saving.
      </p>

      <form onSubmit={(e) => void handleSubmit(e)} className="mt-6 space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className={labelClass}>Job title (optional)</label>
            <input
              className={inputClass}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. QA Automation Engineer"
            />
          </div>
          <div>
            <label className={labelClass}>Company (optional)</label>
            <input
              className={inputClass}
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="e.g. Example Company"
            />
          </div>
        </div>

        <div>
          <label className={labelClass}>Job description</label>
          <textarea
            className={`${textareaClass} min-h-[280px]`}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Paste the full job posting text here…"
          />
        </div>

        {error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
        )}

        <button
          type="submit"
          disabled={isSaving}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {isSaving ? "Saving…" : "Save job description"}
        </button>
      </form>
    </section>
  );
}
