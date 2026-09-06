import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listJobDescriptions } from "../api/jobDescriptions";
import { ApiError } from "../api/client";
import JDStatusBadge from "../components/job/JDStatusBadge";
import type { JobDescriptionSummary } from "../types/jobDescription";

export default function Jobs() {
  const [jobs, setJobs] = useState<JobDescriptionSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    listJobDescriptions()
      .then((data) => {
        if (!cancelled) setJobs(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load job descriptions.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Job Descriptions</h1>
        <Link
          to="/jobs/new"
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          Add job description
        </Link>
      </div>

      <p className="mt-2 text-slate-600">
        Paste a job description to extract its requirements. The job
        description describes what the employer wants - it's never treated
        as proof you have those skills.
      </p>

      {error && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      {jobs === null && !error && <p className="mt-6 text-sm text-slate-500">Loading…</p>}

      {jobs !== null && jobs.length === 0 && (
        <div className="mt-6 rounded-lg border border-dashed border-slate-300 p-8 text-center text-slate-500">
          No job descriptions added yet.
        </div>
      )}

      {jobs !== null && jobs.length > 0 && (
        <ul className="mt-6 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
          {jobs.map((job) => (
            <li key={job.id}>
              <Link
                to={`/jobs/${job.id}`}
                className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-slate-50"
              >
                <div>
                  <p className="font-medium text-slate-900">
                    {job.title || "Untitled role"}
                    {job.company ? ` · ${job.company}` : ""}
                  </p>
                </div>
                <JDStatusBadge status={job.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
