import { createBrowserRouter } from "react-router-dom";

import AppLayout from "../layout/AppLayout";
import Analysis from "../pages/Analysis";
import Dashboard from "../pages/Dashboard";
import JobDescriptions from "../pages/JobDescriptions";
import Resumes from "../pages/Resumes";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "resumes", element: <Resumes /> },
      { path: "job-descriptions", element: <JobDescriptions /> },
      { path: "analysis", element: <Analysis /> },
    ],
  },
]);
