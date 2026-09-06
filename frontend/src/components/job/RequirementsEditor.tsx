import {
  IMPORTANCE_LABELS,
  REQUIREMENT_TYPE_LABELS,
  type Importance,
  type JDRequirementDraft,
  type RequirementType,
} from "../../types/jobDescription";
import {
  addButtonClass,
  cardClass,
  inputClass,
  labelClass,
  removeButtonClass,
} from "../resume/editorStyles";

interface RequirementsEditorProps {
  requirements: JDRequirementDraft[];
  onChange: (requirements: JDRequirementDraft[]) => void;
}

const REQUIREMENT_TYPE_ORDER: RequirementType[] = [
  "required_skill",
  "preferred_skill",
  "technology",
  "responsibility",
  "education",
  "experience",
  "domain",
  "keyword",
  "soft_skill",
];

const IMPORTANCE_OPTIONS: Importance[] = ["required", "preferred", "nice_to_have"];

function emptyRequirement(requirementType: RequirementType): JDRequirementDraft {
  return {
    requirement_type: requirementType,
    name: "",
    importance: requirementType === "preferred_skill" ? "preferred" : "required",
    description: "",
    source_text: "",
    verified: true,
  };
}

export default function RequirementsEditor({ requirements, onChange }: RequirementsEditorProps) {
  function update(index: number, patch: Partial<JDRequirementDraft>) {
    onChange(requirements.map((req, i) => (i === index ? { ...req, ...patch } : req)));
  }

  function remove(index: number) {
    onChange(requirements.filter((_, i) => i !== index));
  }

  function add(requirementType: RequirementType) {
    onChange([...requirements, emptyRequirement(requirementType)]);
  }

  return (
    <div className="space-y-4">
      {REQUIREMENT_TYPE_ORDER.map((type) => {
        const itemsWithIndex = requirements
          .map((req, index) => ({ req, index }))
          .filter(({ req }) => req.requirement_type === type);

        return (
          <div key={type} className={cardClass}>
            <h3 className="text-sm font-semibold text-slate-900">
              {REQUIREMENT_TYPE_LABELS[type]}
            </h3>

            {itemsWithIndex.length === 0 && (
              <p className="mt-2 text-sm text-slate-500">None identified.</p>
            )}

            <div className="mt-3 space-y-3">
              {itemsWithIndex.map(({ req, index }) => (
                <div key={index} className="rounded-md border border-slate-200 p-3">
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-[2fr_1fr]">
                    <div>
                      <label className={labelClass}>Name</label>
                      <input
                        className={inputClass}
                        value={req.name}
                        onChange={(e) => update(index, { name: e.target.value })}
                      />
                    </div>
                    <div>
                      <label className={labelClass}>Importance</label>
                      <select
                        className={inputClass}
                        value={req.importance}
                        onChange={(e) =>
                          update(index, { importance: e.target.value as Importance })
                        }
                      >
                        {IMPORTANCE_OPTIONS.map((option) => (
                          <option key={option} value={option}>
                            {IMPORTANCE_LABELS[option]}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="mt-3">
                    <label className={labelClass}>Source text (from the job description)</label>
                    <input
                      className={inputClass}
                      value={req.source_text ?? ""}
                      onChange={(e) => update(index, { source_text: e.target.value })}
                    />
                  </div>

                  <div className="mt-3 flex items-center justify-between">
                    <label className="flex items-center gap-1.5 text-xs text-slate-600">
                      <input
                        type="checkbox"
                        checked={req.verified}
                        onChange={(e) => update(index, { verified: e.target.checked })}
                      />
                      Verified
                    </label>
                    <button
                      type="button"
                      className={removeButtonClass}
                      onClick={() => remove(index)}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <button type="button" className={addButtonClass} onClick={() => add(type)}>
              + Add {REQUIREMENT_TYPE_LABELS[type].toLowerCase()}
            </button>
          </div>
        );
      })}
    </div>
  );
}
