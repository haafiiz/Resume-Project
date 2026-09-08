import { createBrowserRouter } from "react-router-dom";

import AppLayout from "../layout/AppLayout";
import Analysis from "../pages/Analysis";
import AnalysisDetail from "../pages/AnalysisDetail";
import Dashboard from "../pages/Dashboard";
import JobDetail from "../pages/JobDetail";
import JobNew from "../pages/JobNew";
import Jobs from "../pages/Jobs";
import ResumeDetail from "../pages/ResumeDetail";
import ResumeNew from "../pages/ResumeNew";
import Resumes from "../pages/Resumes";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "resumes", element: <Resumes /> },
      { path: "resumes/new", element: <ResumeNew /> },
      { path: "resumes/:id", element: <ResumeDetail /> },
      { path: "jobs", element: <Jobs /> },
      { path: "jobs/new", element: <JobNew /> },
      { path: "jobs/:id", element: <JobDetail /> },
      { path: "analysis", element: <Analysis /> },
      { path: "analysis/:id", element: <AnalysisDetail /> },
    ],
  },
]);
