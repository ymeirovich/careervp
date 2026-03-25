"use client";

import { useState, KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Topbar } from "@/components/dashboard/Topbar";
import type { UserCV, WorkExperience } from "@/lib/types";

// ─── Types ────────────────────────────────────────────────────────────────────

type FormMode = "view" | "edit" | "saving";

export interface CVFormProps {
  initialCV: UserCV | null;
  isNew: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const EMPTY_CV: UserCV = {
  user_id: "",
  full_name: "",
  language: "en",
  contact_info: { name: "", email: "", phone: "", location: "", linkedin: "" },
  professional_summary: "",
  experience: [],
  education: [],
  skills: [],
  certifications: [],
  top_achievements: ["", "", ""],
  languages: [],
};

const CARD = "rounded-[8px] border border-[#cbd5e1] bg-white p-6 flex flex-col gap-4";
const SECTION_TITLE = "text-base font-bold text-[#1e2229]";
const INPUT =
  "w-full rounded-[4px] border border-[#cbd5e1] px-3 py-2 text-sm text-[#1e2229] " +
  "focus:outline-none focus:border-[#f97316] focus:ring-1 focus:ring-[#f97316]";
const INPUT_DISABLED =
  "w-full rounded-[4px] border border-[#e2e8f0] px-3 py-2 text-sm text-[#9ca3af] " +
  "bg-[rgba(245,245,245,0.8)] cursor-not-allowed";

// ─── Sub-components ───────────────────────────────────────────────────────────

function ImmutableHeader({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="flex items-center gap-2 px-3 py-2 rounded-[4px] bg-[rgba(245,245,245,0.8)] border border-[#e2e8f0]"
      title="Cannot be modified — this field is locked to prevent misrepresentation"
    >
      <span className="text-sm">🔒</span>
      <span className="text-sm font-medium text-[#1e2229]">{children}</span>
    </div>
  );
}

function TagInput({
  tags,
  onChange,
  placeholder,
  maxTags,
}: {
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  maxTags?: number;
}) {
  const [input, setInput] = useState("");

  const addTag = () => {
    const trimmed = input.trim();
    if (!trimmed || tags.includes(trimmed)) return;
    if (maxTags && tags.length >= maxTags) return;
    onChange([...tags, trimmed]);
    setInput("");
  };

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag();
    }
    if (e.key === "Backspace" && !input && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-1.5">
        {tags.map((t) => (
          <span
            key={t}
            className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-[4px] bg-[#f0f2f5] text-[#1e2229]"
          >
            {t}
            <button
              type="button"
              onClick={() => onChange(tags.filter((x) => x !== t))}
              className="ml-0.5 text-[#9ca3af] hover:text-[#ef4444] leading-none"
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          onBlur={addTag}
          placeholder={placeholder ?? "Type and press Enter"}
          className={INPUT + " flex-1"}
        />
        {maxTags && (
          <span className="self-center text-xs text-[#6b7280] shrink-0">
            {tags.length}/{maxTags}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Main Form ────────────────────────────────────────────────────────────────

export function CVForm({ initialCV, isNew }: CVFormProps) {
  const router = useRouter();

  const [mode, setMode] = useState<FormMode>(isNew ? "edit" : "view");
  const [cv, setCv] = useState<UserCV>(initialCV ?? EMPTY_CV);
  const [savedCV, setSavedCV] = useState<UserCV>(initialCV ?? EMPTY_CV);
  const [error, setError] = useState<string | null>(null);

  const isEdit = mode === "edit" || mode === "saving";
  const isSaving = mode === "saving";

  // ── Patch helpers ──────────────────────────────────────────────────────────

  const patch = (updates: Partial<UserCV>) =>
    setCv((prev) => ({ ...prev, ...updates }));

  const patchContact = (updates: Partial<UserCV["contact_info"]>) =>
    setCv((prev) => ({
      ...prev,
      contact_info: { ...prev.contact_info, ...updates },
    }));

  const patchAchievement = (expIndex: number, achIndex: number, value: string) =>
    setCv((prev) => {
      const exp = prev.experience.map((e, i) => {
        if (i !== expIndex) return e;
        const achievements = [...e.achievements];
        achievements[achIndex] = value;
        return { ...e, achievements };
      });
      return { ...prev, experience: exp };
    });

  const addAchievement = (expIndex: number) =>
    setCv((prev) => {
      const exp = prev.experience.map((e, i) =>
        i === expIndex ? { ...e, achievements: [...e.achievements, ""] } : e
      );
      return { ...prev, experience: exp };
    });

  const removeAchievement = (expIndex: number, achIndex: number) =>
    setCv((prev) => {
      const exp = prev.experience.map((e, i) => {
        if (i !== expIndex) return e;
        return {
          ...e,
          achievements: e.achievements.filter((_, j) => j !== achIndex),
        };
      });
      return { ...prev, experience: exp };
    });

  const patchTopAchievement = (index: number, value: string) =>
    setCv((prev) => {
      const top_achievements = [...prev.top_achievements];
      while (top_achievements.length < 3) top_achievements.push("");
      top_achievements[index] = value;
      return { ...prev, top_achievements };
    });

  // ── Actions ────────────────────────────────────────────────────────────────

  const handleEdit = () => {
    setError(null);
    setMode("edit");
  };

  const handleCancel = () => {
    setError(null);
    if (isNew) {
      router.push("/dashboard/cv");
    } else {
      setCv(savedCV);
      setMode("view");
    }
  };

  const handleSave = async () => {
    setMode("saving");
    setError(null);
    try {
      // Clean payload: filter empty achievements
      const payload: Partial<UserCV> = {
        ...cv,
        experience: cv.experience.map((e) => ({
          ...e,
          achievements: e.achievements.filter((a) => a.trim()),
        })),
        top_achievements: cv.top_achievements.filter((a) => a.trim()),
      };
      const saved = await api.saveCV(payload);
      setSavedCV(saved);
      router.push("/dashboard/cv");
    } catch (err) {
      setError("Failed to save CV. Please try again.");
      console.error(err);
      setMode("edit");
    }
  };

  // ── Breadcrumb ────────────────────────────────────────────────────────────

  const breadcrumb = [{ label: "CV Center", href: "/dashboard/cv" }];
  const title = isNew ? "New CV" : "Edit CV";

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <>
      <Topbar title={title} breadcrumb={breadcrumb} />

      {/* Sticky action bar */}
      <div className="sticky top-0 z-10 flex items-center justify-between bg-white border-b border-[#cbd5e1] px-6 py-3">
        <span className="text-sm text-[#f59e0b]">
          {isEdit && !isNew ? "Editing…" : ""}
        </span>
        <div className="flex gap-2">
          {isEdit ? (
            <>
              <button
                onClick={handleCancel}
                disabled={isSaving}
                className="px-4 py-2 text-sm border border-[#cbd5e1] rounded-[8px] text-[#1e2229] hover:bg-[rgba(217,217,217,0.3)] disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-4 py-2 text-sm bg-[#f97316] text-white rounded-[8px] hover:opacity-90 disabled:opacity-50"
              >
                {isSaving ? "Saving…" : "Save"}
              </button>
            </>
          ) : (
            <button
              onClick={handleEdit}
              className="px-4 py-2 text-sm bg-[#f97316] text-white rounded-[8px] hover:opacity-90"
            >
              Edit
            </button>
          )}
        </div>
      </div>

      <main className="flex flex-col gap-6 p-6">
        {/* Error banner */}
        {error && (
          <div className="rounded-[8px] bg-[#fef2f2] border border-[#ef4444] px-4 py-3 text-sm text-[#ef4444]">
            {error}
          </div>
        )}

        {/* Contact Info */}
        <div className={CARD}>
          <h2 className={SECTION_TITLE}>Contact Info</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Full Name" required>
              {isEdit ? (
                <input
                  className={INPUT}
                  value={cv.full_name}
                  onChange={(e) => patch({ full_name: e.target.value })}
                />
              ) : (
                <ViewText value={cv.full_name} />
              )}
            </Field>
            <Field label="Language">
              {isEdit ? (
                <select
                  className={INPUT}
                  value={cv.language}
                  onChange={(e) =>
                    patch({ language: e.target.value as "en" | "he" })
                  }
                >
                  <option value="en">English</option>
                  <option value="he">Hebrew</option>
                </select>
              ) : (
                <ViewText value={cv.language === "he" ? "Hebrew" : "English"} />
              )}
            </Field>
            <Field label="Email">
              {isEdit ? (
                <input
                  className={INPUT}
                  type="email"
                  value={cv.contact_info.email ?? ""}
                  onChange={(e) => patchContact({ email: e.target.value })}
                />
              ) : (
                <ViewText value={cv.contact_info.email} />
              )}
            </Field>
            <Field label="Phone">
              {isEdit ? (
                <input
                  className={INPUT}
                  type="tel"
                  value={cv.contact_info.phone ?? ""}
                  onChange={(e) => patchContact({ phone: e.target.value })}
                />
              ) : (
                <ViewText value={cv.contact_info.phone} />
              )}
            </Field>
            <Field label="Location">
              {isEdit ? (
                <input
                  className={INPUT}
                  value={cv.contact_info.location ?? ""}
                  onChange={(e) => patchContact({ location: e.target.value })}
                />
              ) : (
                <ViewText value={cv.contact_info.location} />
              )}
            </Field>
            <Field label="LinkedIn">
              {isEdit ? (
                <input
                  className={INPUT}
                  value={cv.contact_info.linkedin ?? ""}
                  onChange={(e) => patchContact({ linkedin: e.target.value })}
                />
              ) : (
                <ViewText value={cv.contact_info.linkedin} />
              )}
            </Field>
          </div>
        </div>

        {/* Professional Summary */}
        <div className={CARD}>
          <div className="flex items-start justify-between gap-2">
            <h2 className={SECTION_TITLE}>Professional Summary</h2>
            <span className="text-xs text-[#6b7280]">ⓘ Flexible — tailored per application</span>
          </div>
          {isEdit ? (
            <textarea
              rows={6}
              className={INPUT + " resize-none"}
              value={cv.professional_summary ?? ""}
              onChange={(e) => patch({ professional_summary: e.target.value })}
              placeholder="Write a brief professional summary…"
            />
          ) : (
            <p className="text-sm text-[#1e2229] leading-relaxed whitespace-pre-wrap">
              {cv.professional_summary || (
                <span className="italic text-[#9ca3af]">No summary yet.</span>
              )}
            </p>
          )}
        </div>

        {/* Work Experience */}
        {(cv.experience.length > 0 || isNew) && (
          <div className={CARD}>
            <h2 className={SECTION_TITLE}>Work Experience</h2>
            {cv.experience.length === 0 && (
              <p className="text-sm italic text-[#9ca3af]">No work experience entries.</p>
            )}
            <div className="flex flex-col gap-6">
              {cv.experience.map((exp, ei) => (
                <ExperienceEntry
                  key={ei}
                  exp={exp}
                  index={ei}
                  isEdit={isEdit}
                  onPatchAchievement={(ai, val) => patchAchievement(ei, ai, val)}
                  onAddAchievement={() => addAchievement(ei)}
                  onRemoveAchievement={(ai) => removeAchievement(ei, ai)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Education */}
        {cv.education.length > 0 && (
          <div className={CARD}>
            <h2 className={SECTION_TITLE}>Education</h2>
            <div className="flex flex-col gap-3">
              {cv.education.map((edu, i) => (
                <ImmutableHeader key={i}>
                  {edu.degree}
                  {edu.field_of_study ? ` in ${edu.field_of_study}` : ""} —{" "}
                  {edu.institution}
                  {edu.graduation_date ? ` · ${edu.graduation_date}` : ""}
                </ImmutableHeader>
              ))}
            </div>
          </div>
        )}

        {/* Skills */}
        <div className={CARD}>
          <div className="flex items-center gap-2">
            <h2 className={SECTION_TITLE}>Skills</h2>
            <span className="px-2 py-0.5 text-xs rounded-[4px] bg-[#f0f2f5] text-[#6b7280]">
              {cv.skills.length}
            </span>
          </div>
          {isEdit ? (
            <TagInput
              tags={cv.skills}
              onChange={(tags) => patch({ skills: tags })}
              placeholder="Add skill and press Enter"
              maxTags={50}
            />
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {cv.skills.length === 0 && (
                <span className="text-sm italic text-[#9ca3af]">No skills added.</span>
              )}
              {cv.skills.map((s) => (
                <span
                  key={s}
                  className="px-2 py-0.5 text-xs rounded-[4px] bg-[#f0f2f5] text-[#1e2229]"
                >
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Certifications (read-only display) */}
        {cv.certifications.length > 0 && (
          <div className={CARD}>
            <h2 className={SECTION_TITLE}>Certifications</h2>
            <div className="flex flex-col gap-2">
              {cv.certifications.map((cert, i) => (
                <div key={i} className="flex items-baseline gap-2 text-sm">
                  <span className="font-medium text-[#1e2229]">{cert.name}</span>
                  {cert.issuer && (
                    <span className="text-[#6b7280]">— {cert.issuer}</span>
                  )}
                  {cert.date && (
                    <span className="text-xs text-[#9ca3af]">{cert.date}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top Achievements */}
        <div className={CARD}>
          <div className="flex items-start justify-between gap-2">
            <h2 className={SECTION_TITLE}>Top Achievements</h2>
            <span className="text-xs text-[#6b7280]">ⓘ Max 3 — must be verifiable</span>
          </div>
          {isEdit ? (
            <div className="flex flex-col gap-3">
              {[0, 1, 2].map((i) => (
                <div key={i} className="flex flex-col gap-1">
                  <label className="text-xs text-[#6b7280]">Achievement {i + 1}</label>
                  <textarea
                    rows={2}
                    className={INPUT + " resize-none"}
                    value={cv.top_achievements[i] ?? ""}
                    onChange={(e) => patchTopAchievement(i, e.target.value)}
                    placeholder={`Achievement ${i + 1}…`}
                  />
                </div>
              ))}
            </div>
          ) : (
            <ol className="list-decimal list-inside flex flex-col gap-1">
              {cv.top_achievements.filter((a) => a.trim()).length === 0 && (
                <li className="text-sm italic text-[#9ca3af]">No achievements yet.</li>
              )}
              {cv.top_achievements
                .filter((a) => a.trim())
                .map((a, i) => (
                  <li key={i} className="text-sm text-[#1e2229] leading-relaxed">
                    {a}
                  </li>
                ))}
            </ol>
          )}
        </div>

        {/* Languages */}
        <div className={CARD}>
          <h2 className={SECTION_TITLE}>Languages</h2>
          {isEdit ? (
            <TagInput
              tags={cv.languages}
              onChange={(tags) => patch({ languages: tags })}
              placeholder="Add language and press Enter"
            />
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {cv.languages.length === 0 && (
                <span className="text-sm italic text-[#9ca3af]">No languages added.</span>
              )}
              {cv.languages.map((l) => (
                <span
                  key={l}
                  className="px-2 py-0.5 text-xs rounded-[4px] bg-[#f0f2f5] text-[#1e2229]"
                >
                  {l}
                </span>
              ))}
            </div>
          )}
        </div>
      </main>
    </>
  );
}

// ─── Small helpers ────────────────────────────────────────────────────────────

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-[#1e2229]">
        {label}
        {required && <span className="text-[#ef4444] ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

function ViewText({ value }: { value?: string }) {
  return (
    <span className={`text-sm ${value ? "text-[#1e2229]" : "italic text-[#9ca3af]"}`}>
      {value || "—"}
    </span>
  );
}

function ExperienceEntry({
  exp,
  index,
  isEdit,
  onPatchAchievement,
  onAddAchievement,
  onRemoveAchievement,
}: {
  exp: WorkExperience;
  index: number;
  isEdit: boolean;
  onPatchAchievement: (achIndex: number, value: string) => void;
  onAddAchievement: () => void;
  onRemoveAchievement: (achIndex: number) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      {/* Immutable header */}
      <div
        className="flex items-start justify-between gap-4 px-3 py-2 rounded-[4px] bg-[rgba(245,245,245,0.8)] border border-[#e2e8f0]"
        title="Cannot be modified — this field is locked to prevent misrepresentation"
      >
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-[#1e2229] flex items-center gap-1">
            <span>🔒</span>
            {exp.role} at {exp.company}
            {exp.current && (
              <span className="ml-2 px-1.5 py-0.5 text-xs rounded-[4px] bg-[#dcfce7] text-[#16b44b]">
                Current
              </span>
            )}
          </span>
          <span className="text-xs text-[#6b7280]">{exp.dates}</span>
        </div>
      </div>

      {/* Achievements */}
      <div className="pl-4 flex flex-col gap-2">
        {isEdit ? (
          <>
            {exp.achievements.map((a, ai) => (
              <div key={ai} className="flex gap-2 items-start">
                <textarea
                  rows={2}
                  className="flex-1 rounded-[4px] border border-[#cbd5e1] px-3 py-2 text-sm text-[#1e2229] focus:outline-none focus:border-[#f97316] focus:ring-1 focus:ring-[#f97316] resize-none"
                  value={a}
                  onChange={(e) => onPatchAchievement(ai, e.target.value)}
                  placeholder="Describe achievement with measurable impact…"
                />
                <button
                  type="button"
                  onClick={() => onRemoveAchievement(ai)}
                  className="mt-1 text-xs text-[#9ca3af] hover:text-[#ef4444]"
                >
                  ✕
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={onAddAchievement}
              className="text-xs text-[#f97316] hover:underline w-fit"
            >
              + Add Achievement
            </button>
            <p className="text-xs text-[#f59e0b]">
              ⚠ Achievements must be verifiable — no fabrication
            </p>
          </>
        ) : (
          <ul className="list-disc list-inside flex flex-col gap-1">
            {exp.achievements.length === 0 && (
              <li className="text-sm italic text-[#9ca3af]">No achievements listed.</li>
            )}
            {exp.achievements.map((a, ai) => (
              <li key={ai} className="text-sm text-[#1e2229] leading-relaxed">
                {a}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
