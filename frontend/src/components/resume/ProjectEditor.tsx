import type { ProjectDraft } from "../../types/resume";
import {
  addButtonClass,
  cardClass,
  inputClass,
  labelClass,
  removeButtonClass,
  textareaClass,
} from "./editorStyles";

interface ProjectEditorProps {
  projects: ProjectDraft[];
  onChange: (projects: ProjectDraft[]) => void;
}

function emptyProject(): ProjectDraft {
  return { name: "", description: "", technologies: "", verified: true };
}

export default function ProjectEditor({ projects, onChange }: ProjectEditorProps) {
  function update(index: number, patch: Partial<ProjectDraft>) {
    onChange(projects.map((project, i) => (i === index ? { ...project, ...patch } : project)));
  }

  function remove(index: number) {
    onChange(projects.filter((_, i) => i !== index));
  }

  function add() {
    onChange([...projects, emptyProject()]);
  }

  return (
    <div className={cardClass}>
      <h3 className="text-sm font-semibold text-slate-900">Projects</h3>

      {projects.length === 0 && (
        <p className="mt-2 text-sm text-slate-500">No projects yet.</p>
      )}

      <div className="mt-3 space-y-4">
        {projects.map((project, index) => (
          <div key={index} className="rounded-md border border-slate-200 p-3">
            <label className={labelClass}>Project name</label>
            <input
              className={inputClass}
              value={project.name ?? ""}
              onChange={(e) => update(index, { name: e.target.value })}
            />

            <label className={`${labelClass} mt-3`}>Technologies</label>
            <input
              className={inputClass}
              value={project.technologies ?? ""}
              placeholder="e.g. Python, React"
              onChange={(e) => update(index, { technologies: e.target.value })}
            />

            <label className={`${labelClass} mt-3`}>Description</label>
            <textarea
              className={textareaClass}
              value={project.description ?? ""}
              onChange={(e) => update(index, { description: e.target.value })}
            />

            <div className="mt-3 flex items-center justify-between">
              <label className="flex items-center gap-1.5 text-xs text-slate-600">
                <input
                  type="checkbox"
                  checked={project.verified}
                  onChange={(e) => update(index, { verified: e.target.checked })}
                />
                Verified
              </label>
              <button type="button" className={removeButtonClass} onClick={() => remove(index)}>
                Remove entry
              </button>
            </div>
          </div>
        ))}
      </div>

      <button type="button" className={addButtonClass} onClick={add}>
        + Add project
      </button>
    </div>
  );
}
