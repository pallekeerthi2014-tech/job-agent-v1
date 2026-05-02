"""Resume tailoring service.

Given a candidate's master DOCX resume and a job description, calls OpenAI to
generate targeted edits and applies them using python-docx.  The master file is
NEVER modified — output goes to UPLOAD_DIR/tailored/.
"""
from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.candidate import CandidateSkill
from app.models.tailored_resume import TailoredResume

_RESUME_DIR = Path(os.getenv("RESUME_STORAGE_PATH", "/app/resumes"))
_TAILORED_DIR = _RESUME_DIR / "tailored"


def _extract_docx_text(path: Path) -> str:
    """Extract plain text from a DOCX file using mammoth."""
    import mammoth  # type: ignore
    result = mammoth.extract_raw_text({"path": str(path)})
    return result.value or ""


def _get_candidate_skill_names(db: Session, candidate_id: int) -> set[str]:
    rows = db.query(CandidateSkill).filter(CandidateSkill.candidate_id == candidate_id).all()
    return {r.skill_name.lower() for r in rows}


def _call_openai(master_text: str, jd_text: str, notes: str | None) -> list[dict[str, Any]]:
    """Ask GPT-4o for a list of suggested resume changes."""
    from openai import OpenAI
    from app.core.config import settings

    client = OpenAI(api_key=settings.openai_api_key)

    system_prompt = (
        "You are an expert resume writer. Given a candidate's resume and a job description, "
        "output a JSON array of targeted edits. Each edit is an object with:\n"
        "  section: one of 'Summary', 'Experience', 'Skills'\n"
        "  action: one of 'replace', 'add', 'remove'\n"
        "  content: the new text to use (for replace/add) or text to remove (for remove)\n"
        "  original: (only for replace/remove) the exact existing text to find in the resume\n\n"
        "Rules:\n"
        "- Keep edits targeted and professional.\n"
        "- Only suggest changes that are supported by the candidate's existing experience.\n"
        "- Do NOT invent credentials, companies, or degrees.\n"
        "- Return ONLY valid JSON — no markdown, no prose.\n"
        "- If no changes are needed, return an empty array [].\n"
    )

    notes_block = f"\n\nEmployee notes / instructions:\n{notes}" if notes else ""

    user_prompt = (
        f"RESUME:\n{master_text[:6000]}\n\n"
        f"JOB DESCRIPTION:\n{jd_text[:4000]}"
        f"{notes_block}"
    )

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
    )

    raw = (resp.choices[0].message.content or "").strip()
    # Strip markdown code fences if GPT wraps the JSON
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        changes = json.loads(raw)
        if not isinstance(changes, list):
            changes = []
    except (json.JSONDecodeError, ValueError):
        changes = []
    return changes


def _apply_changes_to_docx(source_path: Path, changes: list[dict[str, Any]]) -> bytes:
    """Apply a list of change dicts to an in-memory copy of the DOCX.

    Strategy: for replace/remove, find the paragraph containing `original`
    and either replace its text or clear it.  For add, append a new paragraph
    at the end of the document (or after the relevant section heading).
    """
    import docx  # python-docx

    doc = docx.Document(str(source_path))

    for change in changes:
        action = change.get("action", "")
        content = change.get("content", "")
        original = change.get("original", "")

        if action == "replace" and original:
            for para in doc.paragraphs:
                if original in para.text:
                    # Preserve first run's formatting, replace full text
                    for run in para.runs:
                        run.text = ""
                    if para.runs:
                        para.runs[0].text = content
                    else:
                        para.add_run(content)
                    break

        elif action == "remove" and original:
            for para in doc.paragraphs:
                if original in para.text:
                    for run in para.runs:
                        run.text = ""
                    break

        elif action == "add" and content:
            doc.add_paragraph(content)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def tailor_resume(
    candidate_id: int,
    job_id: int,
    master_resume_path: str,
    jd_text: str,
    notes: str | None,
    db: Session,
    created_by_employee_id: int | None = None,
    match_id: int | None = None,
    confirm_flagged_skills: list[str] | None = None,
) -> tuple[TailoredResume, list[str]]:
    """Main entry-point called by the API route.

    Returns (TailoredResume record, flagged_skills list).
    If flagged_skills is non-empty and confirm_flagged_skills is None,
    the record stays at status='pending' and the caller should surface the
    flagged_skills to the employee for confirmation before proceeding.
    """
    path = Path(master_resume_path)

    # Create the DB record first so we always have an ID to return
    record = TailoredResume(
        candidate_id=candidate_id,
        job_id=job_id,
        match_id=match_id,
        created_by_employee_id=created_by_employee_id,
        status="pending",
        notes=notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Only DOCX is supported for editing
    if path.suffix.lower() != ".docx":
        record.status = "error"
        record.error_message = "Master resume must be DOCX format for tailoring"
        db.commit()
        return record, []

    if not path.exists():
        record.status = "error"
        record.error_message = "Master resume file not found on disk"
        db.commit()
        return record, []

    # Extract resume text
    try:
        master_text = _extract_docx_text(path)
    except Exception as exc:
        record.status = "error"
        record.error_message = f"Failed to read master resume: {exc}"
        db.commit()
        return record, []

    # Get known skills for this candidate
    known_skills = _get_candidate_skill_names(db, candidate_id)

    # Call OpenAI for suggested changes
    record.status = "processing"
    db.commit()

    try:
        changes = _call_openai(master_text, jd_text, notes)
    except Exception as exc:
        record.status = "error"
        record.error_message = f"OpenAI error: {exc}"
        db.commit()
        return record, []

    # Detect flagged skills — skills in 'add' actions not in candidate's profile
    flagged_skills: list[str] = []
    if known_skills:
        for change in changes:
            if change.get("action") == "add" and change.get("section") == "Skills":
                content = change.get("content", "")
                # Rough check: if any word in the new content isn't in known skills
                words = [w.strip(",.;()").lower() for w in content.split() if len(w) > 2]
                new_skills = [w for w in words if w not in known_skills]
                flagged_skills.extend(new_skills)

    # De-duplicate
    flagged_skills = list(dict.fromkeys(flagged_skills))

    # If there are flagged skills the employee hasn't confirmed, pause here
    if flagged_skills and confirm_flagged_skills is None:
        record.status = "pending"
        db.commit()
        return record, flagged_skills

    # If employee confirmed (or there are none), filter out unconfirmed flagged skills
    confirmed_set = set(s.lower() for s in (confirm_flagged_skills or []))
    if flagged_skills:
        filtered_changes = []
        for change in changes:
            if change.get("action") == "add" and change.get("section") == "Skills":
                content = change.get("content", "")
                words = [w.strip(",.;()").lower() for w in content.split() if len(w) > 2]
                new_skills = [w for w in words if w not in known_skills]
                unconfirmed = [s for s in new_skills if s not in confirmed_set]
                if unconfirmed:
                    continue  # skip this add — not confirmed
            filtered_changes.append(change)
        changes = filtered_changes

    # Apply changes to in-memory DOCX
    try:
        docx_bytes = _apply_changes_to_docx(path, changes)
    except Exception as exc:
        record.status = "error"
        record.error_message = f"Failed to apply changes to DOCX: {exc}"
        db.commit()
        return record, []

    # Save tailored DOCX
    _TAILORED_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_filename = f"tailored_{candidate_id}_{job_id}_{ts}.docx"
    out_path = _TAILORED_DIR / out_filename
    out_path.write_bytes(docx_bytes)

    record.status = "ready"
    record.filename = out_filename
    db.commit()
    db.refresh(record)
    return record, []
