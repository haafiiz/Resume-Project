import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { getAnalysis, getAnalysisMatches } from "../api/analyses";
import MatchList from "../components/analysis/MatchList";
import OverallScoreCard from "../components/analysis/OverallScoreCard";
import type { Analysis, AnalysisMatches } from "../types/analysis";

export default function AnalysisDetail() {
  const { id } = useParams<{ id: string }>();

  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [matchData, setMatchData] = useState<AnalysisMatches | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    Promise.all([getAnalysis(id), getAnalysisMatches(id)])
      .then(([analysisData, matches]) => {
        if (cancelled) return;
        setAnalysis(analysisData);
        setMatchData(matches);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load analysis.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <section>
        <h1 className="text-2xl font-semibold text-slate-900">Analysis</h1>
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      </section>
    );
  }

  if (!analysis || !matchData) {
    return (
      <section>
        <p className="text-sm text-slate-500">Loading…</p>
      </section>
    );
  }

  return (
    <section>
      <h1 className="text-2xl font-semibold text-slate-900">Match analysis</h1>
      <p className="mt-1 text-sm text-slate-500">
        Run on {new Date(analysis.created_at).toLocaleString()}
      </p>

      <div className="mt-6">
        <OverallScoreCard analysis={analysis} />
      </div>

      <div className="mt-6">
        <MatchList
          matches={matchData.matches}
          extraResumeSkills={matchData.extra_resume_skills}
        />
      </div>
    </section>
  );
}
