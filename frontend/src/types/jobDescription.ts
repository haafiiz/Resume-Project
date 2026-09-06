export type JobDescriptionStatus = "created" | "extracted" | "needs_review" | "verified";

export type RequirementType =
  | "required_skill"
  | "preferred_skill"
  | "technology"
  | "responsibility"
  | "education"
  | "experience"
  | "domain"
  | "keyword"
  | "soft_skill";

export type Importance = "required" | "preferred" | "nice_to_have";

export interface JDRequirement {
  id: string;
  requirement_type: RequirementType;
  name: string;
  normalized_name: string;
  importance: Importance;
  description: string | null;
  source_text: string | null;
  verified: boolean;
}

export interface JobDescriptionSummary {
  id: string;
  title: string | null;
  company: string | null;
  status: JobDescriptionStatus;
  created_at: string;
  updated_at: string;
}

export interface JobDescription {
  id: string;
  title: string | null;
  company: string | null;
  description: string;
  status: JobDescriptionStatus;
  extraction_error: string | null;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
  requirements: JDRequirement[];
}

export interface JobDescriptionCreatePayload {
  title?: string | null;
  company?: string | null;
  description: string;
}

// --- Editable "draft" shape used by the requirements editor -------------

export interface JDRequirementDraft {
  id?: string;
  requirement_type: RequirementType;
  name: string;
  importance: Importance;
  description?: string | null;
  source_text?: string | null;
  verified: boolean;
}

export interface JobDescriptionUpdatePayload {
  title?: string | null;
  company?: string | null;
  description?: string | null;
  requirements?: JDRequirementDraft[];
}

export const REQUIREMENT_TYPE_LABELS: Record<RequirementType, string> = {
  required_skill: "Required skill",
  preferred_skill: "Preferred skill",
  technology: "Technology",
  responsibility: "Responsibility",
  education: "Education",
  experience: "Experience",
  domain: "Domain",
  keyword: "Keyword",
  soft_skill: "Soft skill",
};

export const IMPORTANCE_LABELS: Record<Importance, string> = {
  required: "Required",
  preferred: "Preferred",
  nice_to_have: "Nice to have",
};
