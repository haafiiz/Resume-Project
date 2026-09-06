import type { JobDescriptionStatus } from "../../types/jobDescription";

const STATUS_STYLES: Record<JobDescriptionStatus, string> = {
  created: "bg-slate-100 text-slate-700",
  extracted: "bg-blue-100 text-blue-700",
  needs_review: "bg-amber-100 text-amber-800",
  verified: "bg-green-100 text-green-800",
};

const STATUS_LABELS: Record<JobDescriptionStatus, string> = {
  created: "Saved",
  extracted: "Extracted",
  needs_review: "Needs review",
  verified: "Verified",
};

export default function JDStatusBadge({ status }: { status: JobDescriptionStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
