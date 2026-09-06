import { apiRequest } from "./client";
import type {
  JobDescription,
  JobDescriptionCreatePayload,
  JobDescriptionSummary,
  JobDescriptionUpdatePayload,
} from "../types/jobDescription";

export async function listJobDescriptions(): Promise<JobDescriptionSummary[]> {
  return apiRequest<JobDescriptionSummary[]>("/job-descriptions");
}

export async function createJobDescription(
  payload: JobDescriptionCreatePayload,
): Promise<JobDescription> {
  return apiRequest<JobDescription>("/job-descriptions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getJobDescription(id: string): Promise<JobDescription> {
  return apiRequest<JobDescription>(`/job-descriptions/${id}`);
}

export async function extractRequirements(id: string): Promise<JobDescription> {
  return apiRequest<JobDescription>(`/job-descriptions/${id}/extract`, {
    method: "POST",
  });
}

export async function updateJobDescription(
  id: string,
  payload: JobDescriptionUpdatePayload,
): Promise<JobDescription> {
  return apiRequest<JobDescription>(`/job-descriptions/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function verifyJobDescription(id: string): Promise<JobDescription> {
  return apiRequest<JobDescription>(`/job-descriptions/${id}/verify`, {
    method: "POST",
  });
}
