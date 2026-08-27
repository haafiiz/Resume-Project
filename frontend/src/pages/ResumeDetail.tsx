import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { ApiError, getResumeProfile, updateResume, verifyResume } from "../api/resumes";
import CertificationEditor from "../components/resume/CertificationEditor";
import EducationEditor from "../components/resume/EducationEditor";
import ExperienceEditor from "../components/resume/ExperienceEditor";
import ProjectEditor from "../components/resume/ProjectEditor";
import SkillsEditor from "../components/resume/SkillsEditor";
import StatusBadge from "../components/resume/StatusBadge";
import { inputClass, labelClass, textareaClass } from "../components/resume/editorStyles";
import type {
  CertificationDraft,
  EducationDraft,
  ExperienceDraft,
  ProjectDraft,
  ResumeProfile,
  SkillDraft,
} from "../types/resume";

export default function ResumeDetail() {
  const { id } = useParams<{ id: string }>();

  const [profile, setProfile] = useState<ResumeProfile | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [location, setLocation] = useState("");
  const [summary, setSummary] = useState("");
  const [skills, setSkills] = useState<SkillDraft[]>([]);
  const [experiences, setExperiences] = useState<ExperienceDraft[]>([]);
  const [projects, setProjects] = useState<ProjectDraft[]>([]);
  const [educationEntries, setEducationEntries] = useState<EducationDraft[]>([]);
  const [certifications, setCertifications] = useState<CertificationDraft[]>([]);

  function loadIntoForm(data: ResumeProfile) {
    setProfile(data);
    setFullName(data.full_name ?? "");
    setEmail(data.email ?? "");
    setPhone(data.phone ?? "");
    setLocation(data.location ?? "");
    setSummary(data.summary ?? "");
    setSkills(data.skills.map((s) => ({ id: s.id, name: s.name, category: s.category, verified: s.verified })));
    setExperiences(
      data.experiences.map((e) => ({
        id: e.id,
        job_title: e.job_title,
        company: e.company,
        location: e.location,
        start_date: e.start_date,
        end_date: e.end_date,
        is_current: e.is_current,
        description: e.description,
        verified: e.verified,
      })),
    );
    setProjects(
      data.projects.map((p) => ({
        id: p.id,
        name: p.name,
        description: p.description,
        technologies: p.technologies,
        verified: p.verified,
      })),
    );
    setEducationEntries(
      data.education_entries.map((e) => ({
        id: e.id,
        institution: e.institution,
        degree: e.degree,
        field_of_study: e.field_of_study,
        start_date: e.start_date,
        end_date: e.end_date,
        verified: e.verified,
      })),
    );
    setCertifications(
      data.certifications.map((c) => ({
        id: c.id,
        name: c.name,
        issuer: c.issuer,
        issue_date: c.issue_date,
        verified: c.verified,
      })),
    );
  }

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    getResumeProfile(id)
      .then((data) => {
        if (!cancelled) loadIntoForm(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(err instanceof ApiError ? err.message : "Failed to load resume.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  const isVerified = profile?.status === "verified";

  async function handleSave() {
    if (!id) return;
    setActionError(null);
    setStatusMessage(null);
    setIsSaving(true);
    try {
      const updated = await updateResume(id, {
        full_name: fullName,
        email,
        phone,
        location,
        summary,
        skills,
        experiences,
        projects,
        education_entries: educationEntries,
        certifications,
      });
      loadIntoForm(updated);
      setStatusMessage("Changes saved.");
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to save changes.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleVerify() {
    if (!id) return;
    setActionError(null);
    setStatusMessage(null);
    setIsVerifying(true);
    try {
      const updated = await verifyResume(id);
      loadIntoForm(updated);
      setStatusMessage("Resume verified. This profile can now be used for tailoring.");
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to verify resume.");
    } finally {
      setIsVerifying(false);
    }
  }

  if (loadError) {
    return (
      <section>
        <h1 className="text-2xl font-semibold text-slate-900">Resume</h1>
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{loadError}</p>
      </section>
    );
  }

  if (!profile) {
    return (
      <section>
        <p className="text-sm text-slate-500">Loading…</p>
      </section>
    );
  }

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            {profile.full_name || profile.original_filename}
          </h1>
          <p className="text-sm text-slate-500">{profile.original_filename}</p>
        </div>
        <StatusBadge status={profile.status} />
      </div>

      {profile.parse_error && (
        <p className="mt-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {profile.parse_error}
        </p>
      )}

      {isVerified && (
        <p className="mt-4 rounded-md bg-green-50 px-3 py-2 text-sm text-green-800">
          This resume is verified. It's now eligible to be used for job
          matching and tailoring. To make further corrections, upload a new
          resume.
        </p>
      )}

      {actionError && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{actionError}</p>
      )}
      {statusMessage && (
        <p className="mt-4 rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-700">
          {statusMessage}
        </p>
      )}

      <fieldset disabled={isVerified} className="mt-6 space-y-6 disabled:opacity-60">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-slate-900">Contact info</h3>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className={labelClass}>Full name</label>
              <input className={inputClass} value={fullName} onChange={(e) => setFullName(e.target.value)} />
            </div>
            <div>
              <label className={labelClass}>Email</label>
              <input className={inputClass} value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label className={labelClass}>Phone</label>
              <input className={inputClass} value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
            <div>
              <label className={labelClass}>Location</label>
              <input className={inputClass} value={location} onChange={(e) => setLocation(e.target.value)} />
            </div>
          </div>
          <div className="mt-3">
            <label className={labelClass}>Summary</label>
            <textarea className={textareaClass} value={summary} onChange={(e) => setSummary(e.target.value)} />
          </div>
        </div>

        <SkillsEditor skills={skills} onChange={setSkills} />
        <ExperienceEditor experiences={experiences} onChange={setExperiences} />
        <ProjectEditor projects={projects} onChange={setProjects} />
        <EducationEditor educationEntries={educationEntries} onChange={setEducationEntries} />
        <CertificationEditor certifications={certifications} onChange={setCertifications} />
      </fieldset>

      {!isVerified && (
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={isSaving}
            className="rounded-md bg-white px-4 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 disabled:opacity-50"
          >
            {isSaving ? "Saving…" : "Save changes"}
          </button>
          <button
            type="button"
            onClick={() => void handleVerify()}
            disabled={isVerifying}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            {isVerifying ? "Verifying…" : "Mark Resume as Verified"}
          </button>
        </div>
      )}
    </section>
  );
}
