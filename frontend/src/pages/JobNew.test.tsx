import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import JobNew from "./JobNew";

const mockCreateJobDescription = vi.fn();

vi.mock("../api/jobDescriptions", async () => {
  const actual = await vi.importActual("../api/jobDescriptions");
  return {
    ...actual,
    createJobDescription: (...args: unknown[]) => mockCreateJobDescription(...args),
  };
});

function renderWithRouter() {
  return render(
    <MemoryRouter initialEntries={["/jobs/new"]}>
      <Routes>
        <Route path="/jobs/new" element={<JobNew />} />
        <Route path="/jobs/:id" element={<div>Job detail page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("JobNew", () => {
  afterEach(() => {
    mockCreateJobDescription.mockReset();
  });

  it("renders the form fields", () => {
    renderWithRouter();

    expect(screen.getByText(/add a job description/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/qa automation engineer/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/paste the full job posting/i)).toBeInTheDocument();
  });

  it("rejects submission with an empty description without calling the API", async () => {
    renderWithRouter();

    fireEvent.click(screen.getByRole("button", { name: /save job description/i }));

    await waitFor(() => {
      expect(screen.getByText(/paste the job description text/i)).toBeInTheDocument();
    });
    expect(mockCreateJobDescription).not.toHaveBeenCalled();
  });

  it("saves a job description and navigates to its detail page", async () => {
    mockCreateJobDescription.mockResolvedValueOnce({
      id: "jd-123",
      title: "QA Automation Engineer",
      company: null,
      description: "Some JD text",
      status: "created",
      extraction_error: null,
      verified_at: null,
      created_at: "2026-01-01T00:00:00",
      updated_at: "2026-01-01T00:00:00",
      requirements: [],
    });

    renderWithRouter();

    fireEvent.change(screen.getByPlaceholderText(/paste the full job posting/i), {
      target: { value: "Some JD text" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save job description/i }));

    await waitFor(() => {
      expect(screen.getByText(/job detail page/i)).toBeInTheDocument();
    });

    expect(mockCreateJobDescription).toHaveBeenCalledWith({
      title: null,
      company: null,
      description: "Some JD text",
    });
  });

  it("shows an error message when saving fails", async () => {
    mockCreateJobDescription.mockRejectedValueOnce(new ApiError("Something went wrong.", 500));

    renderWithRouter();

    fireEvent.change(screen.getByPlaceholderText(/paste the full job posting/i), {
      target: { value: "Some JD text" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save job description/i }));

    await waitFor(() => {
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });
  });
});
