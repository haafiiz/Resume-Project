import type { ExperienceDraft } from "../../types/resume";
import {
  addButtonClass,
  cardClass,
  inputClass,
  labelClass,
  removeButtonClass,
  textareaClass,
} from "./editorStyles";

interface ExperienceEditorProps {
  experiences: ExperienceDraft[];
  onChange: (experiences: ExperienceDraft[]) => void;
}

function emptyExperience(): ExperienceDraft {
  return {
    job_title: "",
    company: "",
    location: "",
    start_date: "",
    end_date: "",
    is_current: false,
    description: "",
    verified: true,
  };
}

export default function ExperienceEditor({ experiences, onChange }: ExperienceEditorProps) {
  function update(index: number, patch: Partial<ExperienceDraft>) {
    onChange(
      experiences.map((experience, i) => (i === index ? { ...experience, ...patch } : experience)),
    );
  }

  function remove(index: number) {
    onChange(experiences.filter((_, i) => i !== index));
  }

  function add() {
    onChange([...experiences, emptyExperience()]);
  }

  return (
    <div className={cardClass}>
      <h3 className="text-sm font-semibold text-slate-900">Experience</h3>

      {experiences.length === 0 && (
        <p className="mt-2 text-sm text-slate-500">No experience entries yet.</p>
      )}

      <div className="mt-3 space-y-4">
        {experiences.map((experience, index) => (
          <div key={index} className="rounded-md border border-slate-200 p-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className={labelClass}>Job title</label>
                <input
                  className={inputClass}
                  value={experience.job_title ?? ""}
                  onChange={(e) => update(index, { job_title: e.target.value })}
                />
              </div>
              <div>
                <label className={labelClass}>Company</label>
                <input
                  className={inputClass}
                  value={experience.company ?? ""}
                  onChange={(e) => update(index, { company: e.target.value })}
                />
              </div>
              <div>
                <label className={labelClass}>Location</label>
                <input
                  className={inputClass}
                  value={experience.location ?? ""}
                  onChange={(e) => update(index, { location: e.target.value })}
                />
              </div>
              <div className="flex items-end gap-3">
                <div className="flex-1">
                  <label className={labelClass}>Start date</label>
                  <input
                    className={inputClass}
                    value={experience.start_date ?? ""}
                    placeholder="e.g. Jan 2020"
                    onChange={(e) => update(index, { start_date: e.target.value })}
                  />
                </div>
                <div className="flex-1">
                  <label className={labelClass}>End date</label>
                  <input
                    className={inputClass}
                    value={experience.end_date ?? ""}
                    placeholder="e.g. Dec 2022"
                    disabled={experience.is_current}
                    onChange={(e) => update(index, { end_date: e.target.value })}
                  />
                </div>
              </div>
            </div>

            <div className="mt-3">
              <label className={labelClass}>Description</label>
              <textarea
                className={textareaClass}
                value={experience.description ?? ""}
                onChange={(e) => update(index, { description: e.target.value })}
              />
            </div>

            <div className="mt-3 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-1.5 text-xs text-slate-600">
                  <input
                    type="checkbox"
                    checked={experience.is_current}
                    onChange={(e) =>
                      update(index, {
                        is_current: e.target.checked,
                        end_date: e.target.checked ? null : experience.end_date,
                      })
                    }
                  />
                  I currently work here
                </label>
                <label className="flex items-center gap-1.5 text-xs text-slate-600">
                  <input
                    type="checkbox"
                    checked={experience.verified}
                    onChange={(e) => update(index, { verified: e.target.checked })}
                  />
                  Verified
                </label>
              </div>
              <button type="button" className={removeButtonClass} onClick={() => remove(index)}>
                Remove entry
              </button>
            </div>
          </div>
        ))}
      </div>

      <button type="button" className={addButtonClass} onClick={add}>
        + Add experience
      </button>
    </div>
  );
}
