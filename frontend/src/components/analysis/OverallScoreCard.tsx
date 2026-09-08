import ScoreBar from "./ScoreBar";
import type { Analysis } from "../../types/analysis";

function overallColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 50) return "text-amber-600";
  return "text-red-600";
}

export default function OverallScoreCard({ analysis }: { analysis: Analysis }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">Overall match score</p>
          <p className={`text-5xl font-bold ${overallColor(analysis.overall_score)}`}>
            {analysis.overall_score}
            <span className="text-2xl text-slate-400">/100</span>
          </p>
        </div>
        <p className="max-w-xs text-xs text-slate-500">
          Computed deterministically from weighted category scores - the same
          resume and job description will always produce this exact number.
        </p>
      </div>

      <div className="mt-6 space-y-4">
        {analysis.category_breakdown.map((category) => (
          <ScoreBar key={category.category} category={category} />
        ))}
      </div>
    </div>
  );
}
