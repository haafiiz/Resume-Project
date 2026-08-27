export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export interface HealthResponse {
  status: string;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * Shared fetch wrapper: resolves the base URL, parses JSON, and throws
 * an ApiError (with the backend's `detail` message when present) for
 * non-2xx responses so callers can surface a real error message rather
 * than a generic "request failed".
 */
export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response body wasn't JSON - fall back to the generic message
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export async function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health");
}
