import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import Analysis from "./Analysis";

const mockListResumes = vi.fn();
const mockListJobDescriptions = vi.fn();
const mockCreateAnalysis = vi.fn();

vi.mock("../api/resumes", async () => {
  const actual = await vi.importActual("../api/resumes");
  return { ...actual, listResumes: () => mockListResumes() };
});

vi.mock("../api/jobDescriptions", async () => {
  const actual = await vi.importActual("../api/jobDescriptions");
  return { ...actual, listJobDescriptions: () => mockListJobDescriptions() };
});

vi.mock("../api/analyses", async () => {
  const actual = await vi.importActual("../api/analyses");
  return { ...actual, createAnalysis: (...args: unknown[]) => mockCreateAnalysis(...args) };
});

function renderWithRouter() {
  return render(
    <MemoryRouter initialEntries={["/analysis"]}>
      <Routes>
        <Route path="/analysis" element={<Analysis />} />
        <Route path="/analysis/:id" element={<div>Analysis detail page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

const VERIFIED_RESUME = {
  id: "r1",
  original_filename: "resume.docx",
  status: "verified",
  full_name: "Jane Doe",
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

const VERIFIED_JOB = {
  id: "j1",
  title: "QA Engineer",
  company: "Acme",
  status: "verified",
  created_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

describe("Analysis picker", () => {
  afterEach(() => {
    mockListResumes.mockReset();
    mockListJobDescriptions.mockReset();
    mockCreateAnalysis.mockReset();
  });

  it("shows a message when there are no verified resumes or jobs", async () => {
    mockListResumes.mockResolvedValueOnce([]);
    mockListJobDescriptions.mockResolvedValueOnce([]);

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText(/don't have any verified resumes/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/don't have any verified job descriptions/i)).toBeInTheDocument();
  });

  it("lets the user pick a verified resume and job, then runs the analysis", async () => {
    mockListResumes.mockResolvedValueOnce([VERIFIED_RESUME]);
    mockListJobDescriptions.mockResolvedValueOnce([VERIFIED_JOB]);
    mockCreateAnalysis.mockResolvedValueOnce({ id: "a1" });

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText(/run analysis/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/^resume$/i), { target: { value: "r1" } });
    fireEvent.change(screen.getByLabelText(/job description/i), { target: { value: "j1" } });
    fireEvent.click(screen.getByRole("button", { name: /run analysis/i }));

    await waitFor(() => {
      expect(screen.getByText(/analysis detail page/i)).toBeInTheDocument();
    });

    expect(mockCreateAnalysis).toHaveBeenCalledWith({
      resume_id: "r1",
      job_description_id: "j1",
    });
  });

  it("only offers verified resumes and job descriptions, not drafts", async () => {
    mockListResumes.mockResolvedValueOnce([
      VERIFIED_RESUME,
      { ...VERIFIED_RESUME, id: "r2", status: "parsed", full_name: "Draft Resume" },
    ]);
    mockListJobDescriptions.mockResolvedValueOnce([VERIFIED_JOB]);

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText(/run analysis/i)).toBeInTheDocument();
    });

    expect(screen.queryByText(/draft resume/i)).not.toBeInTheDocument();
  });
});
