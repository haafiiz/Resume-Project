import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import ResumeNew from "./ResumeNew";

const mockUploadResume = vi.fn();

vi.mock("../api/resumes", async () => {
  const actual = await vi.importActual("../api/resumes");
  return {
    ...actual,
    uploadResume: (...args: unknown[]) => mockUploadResume(...args),
  };
});

function renderWithRouter() {
  return render(
    <MemoryRouter initialEntries={["/resumes/new"]}>
      <Routes>
        <Route path="/resumes/new" element={<ResumeNew />} />
        <Route path="/resumes/:id" element={<div>Resume detail page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function getFileInput() {
  return screen
    .getByLabelText(/upload resume file/i)
    .parentElement!.querySelector("input")! as HTMLInputElement;
}

describe("ResumeNew", () => {
  afterEach(() => {
    mockUploadResume.mockReset();
  });

  it("renders the upload prompt", () => {
    renderWithRouter();

    expect(screen.getByText(/drag and drop your resume/i)).toBeInTheDocument();
    expect(screen.getByText(/pdf, docx/i)).toBeInTheDocument();
  });

  it("uploads a selected file and navigates to the resume detail page", async () => {
    mockUploadResume.mockResolvedValueOnce({
      id: "abc123",
      original_filename: "resume.pdf",
      status: "parsed",
      parse_error: null,
    });

    renderWithRouter();

    const file = new File(["dummy content"], "resume.pdf", { type: "application/pdf" });
    const input = getFileInput();
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/resume detail page/i)).toBeInTheDocument();
    });

    expect(mockUploadResume).toHaveBeenCalledWith(file);
  });

  it("shows an error message when the upload fails", async () => {
    mockUploadResume.mockImplementationOnce(() =>
      Promise.reject(new ApiError("Unsupported file type.", 400)),
    );

    renderWithRouter();

    const file = new File(["dummy content"], "resume.txt", { type: "text/plain" });
    const input = getFileInput();
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/unsupported file type/i)).toBeInTheDocument();
    });
  });
});
