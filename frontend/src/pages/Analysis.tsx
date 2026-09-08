import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { createAnalysis } from "../api/analyses";
import { listJobDescriptions } from "../api/jobDescriptions";
import { listResumes } from "../api/resumes";
import { inputClass, labelClass } from "../components/resume/editorStyles";
import type { JobDescriptionSummary } from "../types/jobDescription";
import type { ResumeSummary } from "../types/resume";

export default function Analysis() {
  const navigate = useNavigate();

  const [resumes, setResumes] = useState<ResumeSummary[] | null>(null);
  const [jobs, setJobs] = useState<JobDescriptionSummary[] | null>(null);
  const [resumeId, setResumeId] = useState("");
  const [jobId, setJobId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    let cancelled = false;

    Promise.all([listResumes(), listJobDescriptions()])
      .then(([resumeList, jobList]) => {
        if (cancelled) return;
        setResumes(resumeList);
        setJobs(jobList);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load resumes/jobs.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const verifiedResumes = (resumes ?? []).filter((r) => r.status === "verified");
  const verifiedJobs = (jobs ?? []).filter((j) => j.status === "verified");

  async function handleRunAnalysis(e: React.FormEvent) {
    e.preventDefault();
    if (!resumeId || !jobId) {
      setError("Choose a verified resume and a verified job description.");
      return;
    }
    setError(null);
    setIsRunning(true);
    try {
      const analysis = await createAnalysis({
        resume_id: resumeId,
        job_description_id: jobId,
      });
      navigate(`/analysis/${analysis.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to run analysis.");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <section>
      <h1 className="text-2xl font-semibold text-slate-900">Analysis</h1>
      <p className="mt-2 text-slate-600">
        Compare a verified resume against a verified job description to see
        how well it matches - transparently and reproducibly, with no
        invented skills.
      </p>

      {error && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      {resumes !== null && verifiedResumes.length === 0 && (
        <p className="mt-6 text-sm text-slate-500">
          You don't have any verified resumes yet. Upload and verify a resume
          first.
        </p>
      )}
      {jobs !== null && verifiedJobs.length === 0 && (
        <p className="mt-2 text-sm text-slate-500">
          You don't have any verified job descriptions yet. Add and verify one
          first.
        </p>
      )}

      {verifiedResumes.length > 0 && verifiedJobs.length > 0 && (
        <form onSubmit={(e) => void handleRunAnalysis(e)} className="mt-6 space-y-4 max-w-lg">
          <div>
            <label className={labelClass} htmlFor="analysis-resume-select">
              Resume
            </label>
            <select
              id="analysis-resume-select"
              className={inputClass}
              value={resumeId}
              onChange={(e) => setResumeId(e.target.value)}
            >
              <option value="">Select a verified resume…</option>
              {verifiedResumes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.full_name || r.original_filename}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelClass} htmlFor="analysis-job-select">
              Job description
            </label>
            <select
              id="analysis-job-select"
              className={inputClass}
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
            >
              <option value="">Select a verified job description…</option>
              {verifiedJobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title || "Untitled role"}
                  {j.company ? ` · ${j.company}` : ""}
                </option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={isRunning}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {isRunning ? "Running analysis…" : "Run analysis"}
          </button>
        </form>
      )}
    </section>
  );
}
