import type { SkillDraft } from "../../types/resume";
import {
  addButtonClass,
  cardClass,
  inputClass,
  removeButtonClass,
} from "./editorStyles";

interface SkillsEditorProps {
  skills: SkillDraft[];
  onChange: (skills: SkillDraft[]) => void;
}

export default function SkillsEditor({ skills, onChange }: SkillsEditorProps) {
  function update(index: number, patch: Partial<SkillDraft>) {
    onChange(skills.map((skill, i) => (i === index ? { ...skill, ...patch } : skill)));
  }

  function remove(index: number) {
    onChange(skills.filter((_, i) => i !== index));
  }

  function add() {
    onChange([...skills, { name: "", verified: true }]);
  }

  return (
    <div className={cardClass}>
      <h3 className="text-sm font-semibold text-slate-900">Skills</h3>

      {skills.length === 0 && (
        <p className="mt-2 text-sm text-slate-500">No skills yet. Add one below.</p>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {skills.map((skill, index) => (
          <div
            key={index}
            className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-2 py-1"
          >
            <input
              className={`${inputClass} w-40 border-none bg-transparent px-0 py-0`}
              value={skill.name}
              placeholder="Skill name"
              onChange={(e) => update(index, { name: e.target.value })}
            />
            <label className="flex items-center gap-1 text-xs text-slate-500">
              <input
                type="checkbox"
                checked={skill.verified}
                onChange={(e) => update(index, { verified: e.target.checked })}
              />
              Verified
            </label>
            <button
              type="button"
              className={removeButtonClass}
              onClick={() => remove(index)}
              aria-label={`Remove ${skill.name || "skill"}`}
            >
              Remove
            </button>
          </div>
        ))}
      </div>

      <button type="button" className={addButtonClass} onClick={add}>
        + Add skill
      </button>
    </div>
  );
}
