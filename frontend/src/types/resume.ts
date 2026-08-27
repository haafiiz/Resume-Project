export type ResumeStatus = "uploaded" | "parsed" | "needs_review" | "verified";
export type SourceType = "resume" | "user";

export interface Skill {
  id: string;
  name: string;
  category: string | null;
  source: SourceType;
  verified: boolean;
}

export interface Experience {
  id: string;
  job_title: string | null;
  company: string | null;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  description: string | null;
  source: SourceType;
  verified: boolean;
}

export interface Project {
  id: string;
  name: string | null;
  description: string | null;
  technologies: string | null;
  source: SourceType;
  verified: boolean;
}

export interface Education {
  id: string;
  institution: string | null;
  degree: string | null;
  field_of_study: string | null;
  start_date: string | null;
  end_date: string | null;
  source: SourceType;
  verified: boolean;
}

export interface Certification {
  id: string;
  name: string;
  issuer: string | null;
  issue_date: string | null;
  source: SourceType;
  verified: boolean;
}

export interface ResumeSection {
  id: string;
  section_type: string;
  heading: string | null;
  content: string;
  sort_order: number;
}

export interface ResumeSummary {
  id: string;
  original_filename: string;
  status: ResumeStatus;
  full_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResumeUploadResponse {
  id: string;
  original_filename: string;
  status: ResumeStatus;
  parse_error: string | null;
}

export interface ResumeProfile {
  id: string;
  original_filename: string;
  status: ResumeStatus;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  summary: string | null;
  parse_error: string | null;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
  sections: ResumeSection[];
  skills: Skill[];
  experiences: Experience[];
  projects: Project[];
  education_entries: Education[];
  certifications: Certification[];
}

// --- Editable "draft" shapes used by the editor forms --------------------
// These mirror the *_In schemas on the backend: no source field (the
// backend sets it), id optional (present for existing items).

export interface SkillDraft {
  id?: string;
  name: string;
  category?: string | null;
  verified: boolean;
}

export interface ExperienceDraft {
  id?: string;
  job_title: string | null;
  company: string | null;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  description: string | null;
  verified: boolean;
}

export interface ProjectDraft {
  id?: string;
  name: string | null;
  description: string | null;
  technologies: string | null;
  verified: boolean;
}

export interface EducationDraft {
  id?: string;
  institution: string | null;
  degree: string | null;
  field_of_study: string | null;
  start_date: string | null;
  end_date: string | null;
  verified: boolean;
}

export interface CertificationDraft {
  id?: string;
  name: string;
  issuer: string | null;
  issue_date: string | null;
  verified: boolean;
}

export interface ResumeUpdatePayload {
  full_name?: string | null;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  summary?: string | null;
  skills?: SkillDraft[];
  experiences?: ExperienceDraft[];
  projects?: ProjectDraft[];
  education_entries?: EducationDraft[];
  certifications?: CertificationDraft[];
}
