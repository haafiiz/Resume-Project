import type { CertificationDraft } from "../../types/resume";
import {
  addButtonClass,
  cardClass,
  inputClass,
  labelClass,
  removeButtonClass,
} from "./editorStyles";

interface CertificationEditorProps {
  certifications: CertificationDraft[];
  onChange: (certifications: CertificationDraft[]) => void;
}

function emptyCertification(): CertificationDraft {
  return { name: "", issuer: "", issue_date: "", verified: true };
}

export default function CertificationEditor({
  certifications,
  onChange,
}: CertificationEditorProps) {
  function update(index: number, patch: Partial<CertificationDraft>) {
    onChange(certifications.map((cert, i) => (i === index ? { ...cert, ...patch } : cert)));
  }

  function remove(index: number) {
    onChange(certifications.filter((_, i) => i !== index));
  }

  function add() {
    onChange([...certifications, emptyCertification()]);
  }

  return (
    <div className={cardClass}>
      <h3 className="text-sm font-semibold text-slate-900">Certifications</h3>

      {certifications.length === 0 && (
        <p className="mt-2 text-sm text-slate-500">No certifications yet.</p>
      )}

      <div className="mt-3 space-y-3">
        {certifications.map((cert, index) => (
          <div
            key={index}
            className="grid grid-cols-1 items-end gap-3 rounded-md border border-slate-200 p-3 sm:grid-cols-[2fr_2fr_1fr_auto_auto]"
          >
            <div>
              <label className={labelClass}>Name</label>
              <input
                className={inputClass}
                value={cert.name}
                onChange={(e) => update(index, { name: e.target.value })}
              />
            </div>
            <div>
              <label className={labelClass}>Issuer</label>
              <input
                className={inputClass}
                value={cert.issuer ?? ""}
                onChange={(e) => update(index, { issuer: e.target.value })}
              />
            </div>
            <div>
              <label className={labelClass}>Date</label>
              <input
                className={inputClass}
                value={cert.issue_date ?? ""}
                onChange={(e) => update(index, { issue_date: e.target.value })}
              />
            </div>
            <label className="flex items-center gap-1.5 text-xs text-slate-600">
              <input
                type="checkbox"
                checked={cert.verified}
                onChange={(e) => update(index, { verified: e.target.checked })}
              />
              Verified
            </label>
            <button type="button" className={removeButtonClass} onClick={() => remove(index)}>
              Remove
            </button>
          </div>
        ))}
      </div>

      <button type="button" className={addButtonClass} onClick={add}>
        + Add certification
      </button>
    </div>
  );
}
