import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

// Isolate the rendering test from network calls - the Dashboard page
// pings the backend health endpoint, which we don't want to depend on
// a running server for in a unit test.
vi.mock("./api/client", () => ({
  getHealth: vi.fn().mockResolvedValue({ status: "ok" }),
}));

describe("App", () => {
  it("renders the application shell with navigation and the dashboard page", async () => {
    render(<App />);

    // Navigation is present.
    expect(
      screen.getByRole("link", { name: /dashboard/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /resumes/i })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /job descriptions/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /analysis/i })).toBeInTheDocument();

    // Default route (Dashboard) renders its heading.
    expect(
      screen.getByRole("heading", { name: /dashboard/i }),
    ).toBeInTheDocument();

    // Let the async backend status check resolve before the test ends.
    await waitFor(() =>
      expect(screen.getByText(/connected/i)).toBeInTheDocument(),
    );
  });
});
