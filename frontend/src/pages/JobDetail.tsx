import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import {
  extractRequirements,
  getJobDescription,
  updateJobDescription,
  verifyJobDescription,
} from "../api/jobDescriptions";
import JDStatusBadge from "../components/job/JDStatusBadge";
import RequirementsEditor from "../components/job/RequirementsEditor";
import { inputClass, labelClass, textareaClass } from "../components/resume/editorStyles";
import type { JDRequirementDraft, JobDescription } from "../types/jobDescription";

export default function JobDetail() {
  const { id } = useParams<{ id: string }>();

  const [job, setJob] = useState<JobDescription | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [description, setDescription] = useState("");
  const [requirements, setRequirements] = useState<JDRequirementDraft[]>([]);

  function loadIntoForm(data: JobDescription) {
    setJob(data);
    setTitle(data.title ?? "");
    setCompany(data.company ?? "");
    setDescription(data.description);
    setRequirements(
      data.requirements.map((r) => ({
        id: r.id,
        requirement_type: r.requirement_type,
        name: r.name,
        importance: r.importance,
        description: r.description,
        source_text: r.source_text,
        verified: r.verified,
      })),
    );
  }

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    getJobDescription(id)
      .then((data) => {
        if (!cancelled) loadIntoForm(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(err instanceof ApiError ? err.message : "Failed to load job description.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  const isVerified = job?.status === "verified";

  async function handleExtract() {
    if (!id) return;
    setActionError(null);
    setStatusMessage(null);
    setIsExtracting(true);
    try {
      const updated = await extractRequirements(id);
      loadIntoForm(updated);
      if (updated.status === "needs_review") {
        setStatusMessage(null);
      } else {
        setStatusMessage(`Extraction found ${updated.requirements.length} requirement(s).`);
      }
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to extract requirements.");
    } finally {
      setIsExtracting(false);
    }
  }

  async function handleSave() {
    if (!id) return;
    setActionError(null);
    setStatusMessage(null);
    setIsSaving(true);
    try {
      const updated = await updateJobDescription(id, {
        title,
        company,
        description,
        requirements,
      });
      loadIntoForm(updated);
      setStatusMessage("Changes saved.");
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to save changes.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleVerify() {
    if (!id) return;
    setActionError(null);
    setStatusMessage(null);
    setIsVerifying(true);
    try {
      const updated = await verifyJobDescription(id);
      loadIntoForm(updated);
      setStatusMessage("Job description verified.");
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to verify job description.");
    } finally {
      setIsVerifying(false);
    }
  }

  if (loadError) {
    return (
      <section>
        <h1 className="text-2xl font-semibold text-slate-900">Job description</h1>
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{loadError}</p>
      </section>
    );
  }

  if (!job) {
    return (
      <section>
        <p className="text-sm text-slate-500">Loading…</p>
      </section>
    );
  }

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            {job.title || "Untitled role"}
            {job.company ? ` · ${job.company}` : ""}
          </h1>
        </div>
        <JDStatusBadge status={job.status} />
      </div>

      {job.extraction_error && (
        <p className="mt-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {job.extraction_error}
        </p>
      )}

      {isVerified && (
        <p className="mt-4 rounded-md bg-green-50 px-3 py-2 text-sm text-green-800">
          This job description is verified. To make further corrections, add a
          new job description.
        </p>
      )}

      {actionError && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{actionError}</p>
      )}
      {statusMessage && (
        <p className="mt-4 rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-700">
          {statusMessage}
        </p>
      )}

      <fieldset disabled={isVerified} className="mt-6 space-y-6 disabled:opacity-60">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-900">Job details</h3>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className={labelClass}>Title</label>
              <input className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div>
              <label className={labelClass}>Company</label>
              <input
                className={inputClass}
                value={company}
                onChange={(e) => setCompany(e.target.value)}
              />
            </div>
          </div>
          <div className="mt-3">
            <label className={labelClass}>Description</label>
            <textarea
              className={`${textareaClass} min-h-[200px]`}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Requirements</h3>
            {!isVerified && (
              <button
                type="button"
                onClick={() => void handleExtract()}
                disabled={isExtracting}
                className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                {isExtracting ? "Extracting…" : "Extract requirements"}
              </button>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Extraction reads the description above; it never adds a
            requirement that isn't explicitly present in the text.
          </p>
        </div>

        <RequirementsEditor requirements={requirements} onChange={setRequirements} />
      </fieldset>

      {!isVerified && (
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={isSaving}
            className="rounded-md bg-white px-4 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 disabled:opacity-50"
          >
            {isSaving ? "Saving…" : "Save changes"}
          </button>
          <button
            type="button"
            onClick={() => void handleVerify()}
            disabled={isVerifying}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            {isVerifying ? "Verifying…" : "Mark Requirements as Verified"}
          </button>
        </div>
      )}
    </section>
  );
}
