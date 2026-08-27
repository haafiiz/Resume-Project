import type { EducationDraft } from "../../types/resume";
import {
  addButtonClass,
  cardClass,
  inputClass,
  labelClass,
  removeButtonClass,
} from "./editorStyles";

interface EducationEditorProps {
  educationEntries: EducationDraft[];
  onChange: (entries: EducationDraft[]) => void;
}

function emptyEducation(): EducationDraft {
  return {
    institution: "",
    degree: "",
    field_of_study: "",
    start_date: "",
    end_date: "",
    verified: true,
  };
}

export default function EducationEditor({ educationEntries, onChange }: EducationEditorProps) {
  function update(index: number, patch: Partial<EducationDraft>) {
    onChange(
      educationEntries.map((entry, i) => (i === index ? { ...entry, ...patch } : entry)),
    );
  }

  function remove(index: number) {
    onChange(educationEntries.filter((_, i) => i !== index));
  }

  function add() {
    onChange([...educationEntries, emptyEducation()]);
  }

  return (
    <div className={cardClass}>
      <h3 className="text-sm font-semibold text-slate-900">Education</h3>

      {educationEntries.length === 0 && (
        <p className="mt-2 text-sm text-slate-500">No education entries yet.</p>
      )}

      <div className="mt-3 space-y-4">
        {educationEntries.map((entry, index) => (
          <div key={index} className="rounded-md border border-slate-200 p-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className={labelClass}>Institution</label>
                <input
                  className={inputClass}
                  value={entry.institution ?? ""}
                  onChange={(e) => update(index, { institution: e.target.value })}
                />
              </div>
              <div>
                <label className={labelClass}>Degree</label>
                <input
                  className={inputClass}
                  value={entry.degree ?? ""}
                  onChange={(e) => update(index, { degree: e.target.value })}
                />
              </div>
              <div>
                <label className={labelClass}>Field of study</label>
                <input
                  className={inputClass}
                  value={entry.field_of_study ?? ""}
                  onChange={(e) => update(index, { field_of_study: e.target.value })}
                />
              </div>
              <div className="flex items-end gap-3">
                <div className="flex-1">
                  <label className={labelClass}>Start date</label>
                  <input
                    className={inputClass}
                    value={entry.start_date ?? ""}
                    onChange={(e) => update(index, { start_date: e.target.value })}
                  />
                </div>
                <div className="flex-1">
                  <label className={labelClass}>End date</label>
                  <input
                    className={inputClass}
                    value={entry.end_date ?? ""}
                    onChange={(e) => update(index, { end_date: e.target.value })}
                  />
                </div>
              </div>
            </div>

            <div className="mt-3 flex items-center justify-between">
              <label className="flex items-center gap-1.5 text-xs text-slate-600">
                <input
                  type="checkbox"
                  checked={entry.verified}
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
        + Add education
      </button>
    </div>
  );
}
