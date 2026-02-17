"""CV summarization helpers for prompt cost optimization."""

from __future__ import annotations

import json
import math
from typing import Any

from careervp.models.cv import Education, Skill, UserCV, WorkExperience


class CVSummarizer:
    """Extract compact CV context while preserving the most important signals."""

    SUMMARY_CHAR_LIMIT = 200
    EXPERIENCE_CHAR_LIMIT = 500
    EXPERIENCE_JOB_LIMIT = 3
    SKILLS_LIMIT = 50
    EDUCATION_CHAR_LIMIT = 300

    _SKILL_LEVEL_PRIORITY = {
        'EXPERT': 4,
        'ADVANCED': 3,
        'INTERMEDIATE': 2,
        'BEGINNER': 1,
    }

    def summarize(self, cv: UserCV, max_tokens: int = 2000) -> dict[str, Any]:
        """Build a token-efficient CV payload for LLM prompts."""
        summary_text = self._build_summary(cv)
        summary, summary_truncated = self._truncate_text(summary_text, self.SUMMARY_CHAR_LIMIT)

        experience, experience_truncated = self._summarize_experience(cv.work_experience)
        skills, skills_truncated = self._summarize_skills(cv.skills)
        education, education_truncated = self._summarize_education(cv.education)

        was_truncated = summary_truncated or experience_truncated or skills_truncated or education_truncated

        token_count = self._estimate_payload_tokens(
            summary=summary,
            experience=experience,
            skills=skills,
            education=education,
        )

        if token_count > max_tokens:
            summary, experience, skills, education, budget_truncated, token_count = self._enforce_token_budget(
                summary=summary,
                experience=experience,
                skills=skills,
                education=education,
                max_tokens=max_tokens,
            )
            was_truncated = was_truncated or budget_truncated

        return {
            'summary': summary,
            'experience': experience,
            'skills_extracted': skills,
            'education': education,
            'token_count': token_count,
            'was_truncated': was_truncated,
        }

    def _build_summary(self, cv: UserCV) -> str:
        summary_parts: list[str] = []

        name = cv.full_name.strip()
        if name:
            summary_parts.append(name)

        if cv.professional_summary:
            professional_summary = cv.professional_summary.strip()
            if professional_summary:
                summary_parts.append(professional_summary)

        return ' | '.join(summary_parts)

    def _summarize_experience(self, experiences: list[WorkExperience]) -> tuple[list[str], bool]:
        selected_jobs = experiences[: self.EXPERIENCE_JOB_LIMIT]
        was_truncated = len(experiences) > self.EXPERIENCE_JOB_LIMIT

        summarized_jobs: list[str] = []
        for job in selected_jobs:
            compact_text = self._format_experience_entry(job)
            trimmed_text, item_truncated = self._truncate_text(compact_text, self.EXPERIENCE_CHAR_LIMIT)
            summarized_jobs.append(trimmed_text)
            was_truncated = was_truncated or item_truncated

        return summarized_jobs, was_truncated

    def _summarize_skills(self, skills: list[Skill | str]) -> tuple[list[str], bool]:
        ranked: dict[str, tuple[str, int, int]] = {}

        for index, skill in enumerate(skills):
            name, score = self._score_skill(skill)
            normalized = name.strip().lower()
            if not normalized:
                continue

            previous = ranked.get(normalized)
            candidate = (name.strip(), score, index)
            if previous is None or candidate[1] > previous[1]:
                ranked[normalized] = candidate

        ordered = sorted(ranked.values(), key=lambda item: (-item[1], item[2]))
        skill_names = [item[0] for item in ordered]

        was_truncated = len(skill_names) > self.SKILLS_LIMIT
        return skill_names[: self.SKILLS_LIMIT], was_truncated

    def _summarize_education(self, education_entries: list[Education]) -> tuple[str, bool]:
        compact_entries = [self._format_education_entry(entry) for entry in education_entries]
        compact_text = '; '.join(part for part in compact_entries if part)
        return self._truncate_text(compact_text, self.EDUCATION_CHAR_LIMIT)

    def _enforce_token_budget(  # noqa: C901
        self,
        summary: str,
        experience: list[str],
        skills: list[str],
        education: str,
        max_tokens: int,
    ) -> tuple[str, list[str], list[str], str, bool, int]:
        current_summary = summary
        current_experience = list(experience)
        current_skills = list(skills)
        current_education = education
        budget_truncated = False

        for _ in range(24):
            token_count = self._estimate_payload_tokens(
                summary=current_summary,
                experience=current_experience,
                skills=current_skills,
                education=current_education,
            )
            if token_count <= max_tokens:
                return (
                    current_summary,
                    current_experience,
                    current_skills,
                    current_education,
                    budget_truncated,
                    token_count,
                )

            changed = False

            # Drop older jobs first to preserve the most recent role.
            if len(current_experience) > 1:
                current_experience = current_experience[:-1]
                changed = True
            elif len(current_skills) > 20:
                # Keep top-ranked skills and remove lower-priority tail entries.
                current_skills = current_skills[:-5]
                changed = True
            elif len(current_education) > 150:
                current_education, did_truncate = self._truncate_text(
                    current_education,
                    max(150, len(current_education) - 60),
                )
                changed = changed or did_truncate
            elif len(current_summary) > 120:
                current_summary, did_truncate = self._truncate_text(
                    current_summary,
                    max(120, len(current_summary) - 40),
                )
                changed = changed or did_truncate
            elif current_experience:
                shorter_entries: list[str] = []
                did_shorten = False
                for job in current_experience:
                    shortened_job, did_truncate = self._truncate_text(job, max(180, len(job) - 60))
                    shorter_entries.append(shortened_job)
                    did_shorten = did_shorten or did_truncate
                if did_shorten:
                    current_experience = shorter_entries
                    changed = True

            if not changed:
                break
            budget_truncated = True

        final_token_count = self._estimate_payload_tokens(
            summary=current_summary,
            experience=current_experience,
            skills=current_skills,
            education=current_education,
        )
        return (
            current_summary,
            current_experience,
            current_skills,
            current_education,
            budget_truncated,
            final_token_count,
        )

    def _score_skill(self, skill: Skill | str) -> tuple[str, int]:
        if isinstance(skill, Skill):
            level_value = skill.level.value if skill.level else ''
            level_score = self._SKILL_LEVEL_PRIORITY.get(level_value, 0)
            years_score = max(skill.years_of_experience or 0, 0) * 10
            return skill.name, years_score + level_score
        return str(skill), 0

    def _format_experience_entry(self, experience: WorkExperience) -> str:
        dates = experience.dates or ''
        headline = f'{experience.company} | {experience.role}'
        if dates:
            headline = f'{headline} | {dates}'

        parts = [headline]
        if experience.description:
            parts.append(experience.description.strip())
        if experience.achievements:
            parts.append('Achievements: ' + '; '.join(achievement.strip() for achievement in experience.achievements if achievement.strip()))

        return ' '.join(part for part in parts if part).strip()

    def _format_education_entry(self, education: Education) -> str:
        parts = [education.institution, education.degree]
        if education.field_of_study:
            parts.append(education.field_of_study)
        if education.dates:
            parts.append(education.dates)
        elif education.graduation_date:
            parts.append(education.graduation_date)
        return ' | '.join(part.strip() for part in parts if part and part.strip())

    def _estimate_payload_tokens(self, summary: str, experience: list[str], skills: list[str], education: str) -> int:
        payload = {
            'summary': summary,
            'experience': experience,
            'skills_extracted': skills,
            'education': education,
        }
        return self._estimate_tokens(json.dumps(payload, ensure_ascii=False))

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, math.ceil(len(text) / 4))

    @staticmethod
    def _truncate_text(text: str, max_chars: int) -> tuple[str, bool]:
        clean_text = text.strip()
        if max_chars <= 0:
            return '', bool(clean_text)
        if len(clean_text) <= max_chars:
            return clean_text, False
        if max_chars <= 3:
            return clean_text[:max_chars], True
        return clean_text[: max_chars - 3].rstrip() + '...', True
