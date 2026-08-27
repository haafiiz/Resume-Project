import { useNavigate } from "react-router-dom";

import UploadForm from "../components/resume/UploadForm";

export default function ResumeNew() {
  const navigate = useNavigate();

  return (
    <section>
      <h1 className="text-2xl font-semibold text-slate-900">Upload a resume</h1>
      <p className="mt-2 text-slate-600">
        We'll extract your contact info, skills, experience, education,
        projects, and certifications automatically. You'll be able to
        review and correct everything before verifying your profile.
      </p>

      <div className="mt-6">
        <UploadForm onUploaded={(resumeId) => navigate(`/resumes/${resumeId}`)} />
      </div>
    </section>
  );
}
