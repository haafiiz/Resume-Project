import { API_BASE_URL, ApiError, apiRequest } from "./client";
import type {
  ResumeProfile,
  ResumeSummary,
  ResumeUpdatePayload,
  ResumeUploadResponse,
} from "../types/resume";

export { ApiError };

export async function listResumes(): Promise<ResumeSummary[]> {
  return apiRequest<ResumeSummary[]>("/resumes");
}

export async function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<ResumeUploadResponse>("/resumes", {
    method: "POST",
    body: formData,
  });
}

export async function getResumeProfile(resumeId: string): Promise<ResumeProfile> {
  return apiRequest<ResumeProfile>(`/resumes/${resumeId}/profile`);
}

export async function updateResume(
  resumeId: string,
  payload: ResumeUpdatePayload,
): Promise<ResumeProfile> {
  return apiRequest<ResumeProfile>(`/resumes/${resumeId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function verifyResume(resumeId: string): Promise<ResumeProfile> {
  return apiRequest<ResumeProfile>(`/resumes/${resumeId}/verify`, {
    method: "POST",
  });
}

// Exposed for callers that need the raw base URL (not currently used,
// but avoids every module having to re-derive it from env vars).
export { API_BASE_URL };
