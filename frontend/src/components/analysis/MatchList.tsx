import { MATCH_TYPE_LABELS, type SkillMatch } from "../../types/analysis";

const MATCH_TYPE_STYLES: Record<string, string> = {
  exact: "bg-green-100 text-green-800",
  normalized: "bg-green-100 text-green-800",
  related: "bg-blue-100 text-blue-800",
  partial: "bg-amber-100 text-amber-800",
  missing: "bg-red-100 text-red-800",
  unknown: "bg-slate-100 text-slate-600",
};

function MatchRow({ match }: { match: SkillMatch }) {
  return (
    <li className="rounded-md border border-slate-200 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium text-slate-900">{match.requirement_name}</span>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${MATCH_TYPE_STYLES[match.match_type]}`}
        >
          {MATCH_TYPE_LABELS[match.match_type]}
        </span>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        {match.requirement_type.replace(/_/g, " ")} · confidence{" "}
        {Math.round(match.confidence * 100)}%
      </p>
      <p className="mt-2 text-sm text-slate-600">{match.explanation}</p>
    </li>
  );
}

export default function MatchList({
  matches,
  extraResumeSkills,
}: {
  matches: SkillMatch[];
  extraResumeSkills: string[];
}) {
  const matched = matches.filter((m) => ["exact", "normalized", "related"].includes(m.match_type));
  const partial = matches.filter((m) => m.match_type === "partial");
  const missing = matches.filter((m) => m.match_type === "missing");
  const unknown = matches.filter((m) => m.match_type === "unknown");

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">
          Matched requirements ({matched.length})
        </h3>
        {matched.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No fully matched requirements.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {matched.map((m) => (
              <MatchRow key={m.id} match={m} />
            ))}
          </ul>
        )}
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-900">
          Partial matches ({partial.length})
        </h3>
        {partial.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No partial matches.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {partial.map((m) => (
              <MatchRow key={m.id} match={m} />
            ))}
          </ul>
        )}
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-900">
          Missing requirements ({missing.length})
        </h3>
        <p className="text-xs text-slate-500">
          Present in the job description but not found in the verified resume
          profile.
        </p>
        {missing.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">Nothing missing.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {missing.map((m) => (
              <MatchRow key={m.id} match={m} />
            ))}
          </ul>
        )}
      </div>

      {unknown.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Unable to compare ({unknown.length})
          </h3>
          <ul className="mt-3 space-y-2">
            {unknown.map((m) => (
              <MatchRow key={m.id} match={m} />
            ))}
          </ul>
        </div>
      )}

      {extraResumeSkills.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Additional resume skills ({extraResumeSkills.length})
          </h3>
          <p className="text-xs text-slate-500">
            On the verified resume but not requested by this job description -
            informational only, not scored.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {extraResumeSkills.map((skill) => (
              <span
                key={skill}
                className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
