export type MatchType = "exact" | "normalized" | "related" | "partial" | "missing" | "unknown";

export interface CategoryScore {
  category: string;
  weight: number;
  requirement_count: number;
  score: number;
  weighted_contribution: number;
}

export interface Analysis {
  id: string;
  resume_id: string;
  job_description_id: string;
  overall_score: number;
  required_skills_score: number;
  responsibilities_score: number;
  experience_score: number;
  education_score: number;
  preferred_skills_score: number;
  keywords_score: number;
  category_breakdown: CategoryScore[];
  weights: Record<string, number>;
  created_at: string;
}

export interface SkillMatch {
  id: string;
  jd_requirement_id: string;
  requirement_type: string;
  requirement_name: string;
  scoring_category: string;
  resume_skill_id: string | null;
  matched_resume_label: string | null;
  matched_resume_text: string | null;
  match_type: MatchType;
  confidence: number;
  explanation: string;
}

export interface AnalysisMatches {
  analysis_id: string;
  matches: SkillMatch[];
  extra_resume_skills: string[];
}

export interface AnalysisCreatePayload {
  resume_id: string;
  job_description_id: string;
}

export const CATEGORY_LABELS: Record<string, string> = {
  required_skills: "Required Skills",
  responsibilities: "Responsibilities",
  experience: "Experience",
  education: "Education",
  preferred_skills: "Preferred Skills",
  keywords: "Keywords",
};

export const MATCH_TYPE_LABELS: Record<MatchType, string> = {
  exact: "Exact match",
  normalized: "Equivalent match",
  related: "Related match",
  partial: "Partial match",
  missing: "Missing",
  unknown: "Unknown",
};
