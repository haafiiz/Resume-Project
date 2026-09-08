import { apiRequest } from "./client";
import type { Analysis, AnalysisCreatePayload, AnalysisMatches } from "../types/analysis";

export async function createAnalysis(payload: AnalysisCreatePayload): Promise<Analysis> {
  return apiRequest<Analysis>("/analyses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getAnalysis(id: string): Promise<Analysis> {
  return apiRequest<Analysis>(`/analyses/${id}`);
}

export async function getAnalysisMatches(id: string): Promise<AnalysisMatches> {
  return apiRequest<AnalysisMatches>(`/analyses/${id}/matches`);
}
