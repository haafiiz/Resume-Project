import { CATEGORY_LABELS, type CategoryScore } from "../../types/analysis";

function barColor(scorePercent: number): string {
  if (scorePercent >= 80) return "bg-green-500";
  if (scorePercent >= 50) return "bg-amber-500";
  return "bg-red-500";
}

export default function ScoreBar({ category }: { category: CategoryScore }) {
  const scorePercent = Math.round(category.score * 100);

  return (
    <div>
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-medium text-slate-700">
          {CATEGORY_LABELS[category.category] ?? category.category}
        </span>
        <span className="text-slate-500">
          {scorePercent}%{" "}
          <span className="text-xs">
            (weight {Math.round(category.weight * 100)}%, {category.requirement_count}{" "}
            requirement{category.requirement_count === 1 ? "" : "s"})
          </span>
        </span>
      </div>
      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full ${barColor(scorePercent)}`}
          style={{ width: `${scorePercent}%` }}
        />
      </div>
    </div>
  );
}
