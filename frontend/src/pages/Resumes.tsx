import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, listResumes } from "../api/resumes";
import StatusBadge from "../components/resume/StatusBadge";
import type { ResumeSummary } from "../types/resume";

export default function Resumes() {
  const [resumes, setResumes] = useState<ResumeSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    listResumes()
      .then((data) => {
        if (!cancelled) setResumes(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load resumes.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Resumes</h1>
        <Link
          to="/resumes/new"
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          Upload resume
        </Link>
      </div>

      <p className="mt-2 text-slate-600">
        Upload a resume to build your verified profile. Only what's in your
        verified profile will ever be used to tailor a resume for a job.
      </p>

      {error && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      {resumes === null && !error && (
        <p className="mt-6 text-sm text-slate-500">Loading…</p>
      )}

      {resumes !== null && resumes.length === 0 && (
        <div className="mt-6 rounded-lg border border-dashed border-slate-300 p-8 text-center text-slate-500">
          No resumes uploaded yet.
        </div>
      )}

      {resumes !== null && resumes.length > 0 && (
        <ul className="mt-6 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
          {resumes.map((resume) => (
            <li key={resume.id}>
              <Link
                to={`/resumes/${resume.id}`}
                className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-slate-50"
              >
                <div>
                  <p className="font-medium text-slate-900">
                    {resume.full_name || resume.original_filename}
                  </p>
                  <p className="text-xs text-slate-500">{resume.original_filename}</p>
                </div>
                <StatusBadge status={resume.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
