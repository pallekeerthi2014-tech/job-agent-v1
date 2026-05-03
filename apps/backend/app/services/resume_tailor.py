"""Resume tailoring service.

Given a candidate's master DOCX resume and a job description, calls OpenAI to
generate targeted edits and applies them using python-docx.  The master file is
NEVER modified — output goes to UPLOAD_DIR/tailored/.

Design principles:
- Employee notes are treated as PRIMARY instructions.  GPT only does what the
  employee explicitly asks — no unsolicited rewrites.
- New paragraphs copy paragraph & run formatting from their insertion point,
  preserving bullet styles, indentation, and fonts.
- Changes are insert_after operations identified by paragraph index so there is
  no ambiguous text-search.
"""
from __future__ import annotations

import copy
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.candidate import Candidate, CandidateSkill
from app.models.tailored_resume import TailoredResume

_RESUME_DIR = Path(os.getenv("RESUME_STORAGE_PATH", "/app/resumes"))
_TAILORED_DIR = _RESUME_DIR / "tailored"


# ── DOCX utilities ────────────────────────────────────────────────────────────

def _extract_docx_text(path: Path) -> str:
    import mammoth  # type: ignore
    result = mammoth.extract_raw_text({"path": str(path)})
    return result.value or ""


def _get_doc_paragraphs(path: Path) -> list[dict[str, Any]]:
    """Return a numbered list of non-empty paragraphs for GPT context."""
    import docx  # python-docx
    doc = docx.Document(str(path))
    paras = []
    for i, p in enumerate(doc.paragraphs):
        text = p.text.strip()
        if text:
            paras.append({
                "index": i,
                "style": p.style.name if p.style else "Normal",
                "text": text[:300],
            })
    return paras


def _make_paragraph_element(doc: Any, text: str, ref_para: Any) -> Any:
    """Build a new <w:p> element that inherits paragraph + run formatting from ref_para."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    new_p = OxmlElement("w:p")

    # Copy paragraph properties (indentation, bullet style, spacing, etc.)
    ref_pPr = ref_para._element.find(qn("w:pPr"))
    if ref_pPr is not None:
        new_p.append(copy.deepcopy(ref_pPr))

    # Build run
    new_r = OxmlElement("w:r")

    # Copy run properties (font, size, bold, etc.) from first run of ref_para
    if ref_para.runs:
        ref_rPr = ref_para.runs[0]._element.find(qn("w:rPr"))
        if ref_rPr is not None:
            new_r.append(copy.deepcopy(ref_rPr))

    new_t = OxmlElement("w:t")
    new_t.text = text
    new_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    new_r.append(new_t)
    new_p.append(new_r)

    return new_p


def _apply_changes_to_docx(source_path: Path, changes: list[dict[str, Any]]) -> bytes:
    """Apply insert_after changes to an in-memory DOCX copy.

    Each change must have:
      action          : "insert_after"
      paragraph_index : int  — insert new para after para at this index
      content         : str  — text for the new paragraph
    """
    import docx  # python-docx

    doc = docx.Document(str(source_path))

    # Snapshot paragraph list BEFORE any mutation so indices stay stable
    para_snapshot = list(doc.paragraphs)

    # Process in REVERSE index order so earlier inserts don't shift later ones
    inserts = sorted(
        [
            c for c in changes
            if c.get("action") == "insert_after"
            and isinstance(c.get("paragraph_index"), int)
            and c.get("content", "").strip()
        ],
        key=lambda x: x["paragraph_index"],
        reverse=True,
    )

    for change in inserts:
        idx = change["paragraph_index"]
        content = change["content"].strip()

        if idx < 0 or idx >= len(para_snapshot):
            continue

        ref_para = para_snapshot[idx]
        new_elem = _make_paragraph_element(doc, content, ref_para)
        ref_para._element.addnext(new_elem)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── OpenAI call ───────────────────────────────────────────────────────────────

def _call_openai(
    doc_paragraphs: list[dict[str, Any]],
    jd_text: str,
    notes: str | None,
) -> list[dict[str, Any]]:
    """Return a list of insert_after change dicts from GPT-4o.

    If employee notes are provided, they are treated as the ONLY instruction.
    GPT is not allowed to make unsolicited changes.
    """
    from openai import OpenAI
    from app.core.config import settings

    client = OpenAI(api_key=settings.openai_api_key)

    # Build the paragraph context string
    para_lines = "\n".join(
        f"[{p['index']}] ({p['style']}) {p['text']}"
        for p in doc_paragraphs
    )

    if notes and notes.strip():
        instructions_block = f"""
═══ EMPLOYEE INSTRUCTIONS (follow EXACTLY and ONLY these) ═══
{notes.strip()}
═══════════════════════════════════════════════════════════════

CRITICAL RULES:
1. ONLY perform the action described in the employee instructions above.
2. Do NOT change, rewrite, or touch anything not explicitly mentioned.
3. Do NOT add a summary, do NOT change skills, do NOT reformat.
4. If the instruction says "last two projects" or "last two jobs": find the
   two most recent job title/company lines (usually highest-indexed job
   entries in the Experience section) and insert new bullet points
   IMMEDIATELY AFTER those lines.
5. Match the bullet style already used in the document (copy from nearby
   bullets — same indentation, same character).
6. Each bullet should be a single, specific, professional responsibility.
7. Keep changes minimal — only what was asked for.
"""
    else:
        instructions_block = """
Make minimal, targeted edits to better align the resume with the job description.
Only change what clearly improves the match. Do not reformat or rewrite whole sections.
"""

    system_prompt = f"""You are a precise resume editor. Your output is ONLY a JSON array of insertions.

Each insertion is:
{{
  "action": "insert_after",
  "paragraph_index": <int>,   // insert new paragraph after this paragraph index
  "content": "<text>"         // the exact text for the new bullet/line
}}

{instructions_block}

RULES:
- Return ONLY a valid JSON array. No markdown fences. No prose. No explanation.
- Empty array [] if no changes are needed.
- paragraph_index must be an integer from the paragraph list provided.
- Do NOT invent companies, degrees, or certifications that aren't implied by the existing resume.
"""

    user_msg = (
        f"RESUME PARAGRAPHS (index → style → text):\n{para_lines[:5000]}\n\n"
        f"JOB DESCRIPTION:\n{jd_text[:2000]}"
    )

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.2,
        max_tokens=1500,
    )

    raw = (resp.choices[0].message.content or "").strip()

    # Strip markdown code fences if GPT wraps the JSON
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
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


# ── Skill flagging ─────────────────────────────────────────────────────────────

def _get_candidate_skill_names(db: Session, candidate_id: int) -> set[str]:
    rows = db.query(CandidateSkill).filter(CandidateSkill.candidate_id == candidate_id).all()
    return {r.skill_name.lower() for r in rows}


def _flag_unknown_skills(
    changes: list[dict[str, Any]],
    known_skills: set[str],
) -> list[str]:
    """Return skill names in inserted content that aren't in the candidate's profile."""
    flagged: list[str] = []
    skill_keywords = {
        w.strip(",.;()").lower()
        for c in changes
        for w in c.get("content", "").split()
        if len(w.strip(",.;()")) > 2
    }
    flagged = [w for w in skill_keywords if w not in known_skills]
    return list(dict.fromkeys(flagged))  # de-duplicate, preserve order


# ── Main entry point ──────────────────────────────────────────────────────────

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
    """Tailor a candidate's master DOCX resume for a specific job.

    Returns (TailoredResume record, flagged_skills list).
    If flagged_skills is non-empty and confirm_flagged_skills is None, the
    record stays at status='pending' for the employee to confirm before proceeding.
    """
    path = Path(master_resume_path)

    # Create the DB record first — gives us an ID to return in all error paths
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

    # ── Validate master resume ───────────────────────────────────────────────
    if path.suffix.lower() != ".docx":
        record.status = "error"
        record.error_message = (
            "Master resume must be a .docx file. "
            "Please re-upload the resume as a Word document (.docx) and try again."
        )
        db.commit()
        return record, []

    # If the disk file is missing (e.g. after a Railway redeploy), restore it
    # from the database bytes which are always present after any upload.
    if not path.exists():
        candidate = db.get(Candidate, candidate_id)
        if candidate and candidate.resume_bytes:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(candidate.resume_bytes)
            except Exception as exc:
                record.status = "error"
                record.error_message = f"Could not restore resume from database: {exc}"
                db.commit()
                return record, []
        else:
            record.status = "error"
            record.error_message = (
                "Resume file not found. Please re-upload the candidate's .docx resume."
            )
            db.commit()
            return record, []

    # ── Extract paragraph structure ──────────────────────────────────────────
    try:
        doc_paragraphs = _get_doc_paragraphs(path)
    except Exception as exc:
        record.status = "error"
        record.error_message = f"Could not read the DOCX file: {exc}"
        db.commit()
        return record, []

    if not doc_paragraphs:
        record.status = "error"
        record.error_message = "The resume appears to be empty or unreadable."
        db.commit()
        return record, []

    # ── Call OpenAI ──────────────────────────────────────────────────────────
    record.status = "processing"
    db.commit()

    try:
        changes = _call_openai(doc_paragraphs, jd_text, notes)
    except Exception as exc:
        record.status = "error"
        record.error_message = f"AI service error: {exc}"
        db.commit()
        return record, []

    if not changes:
        # GPT found nothing to change — still mark ready with original
        # (copy master to tailored dir unchanged)
        _TAILORED_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_filename = f"tailored_{candidate_id}_{job_id}_{ts}.docx"
        out_path = _TAILORED_DIR / out_filename
        import shutil
        shutil.copy2(path, out_path)
        record.status = "ready"
        record.filename = out_filename
        record.error_message = "No changes were needed — the resume already aligns well."
        db.commit()
        db.refresh(record)
        return record, []

    # ── Skill flagging ───────────────────────────────────────────────────────
    known_skills = _get_candidate_skill_names(db, candidate_id)
    flagged_skills: list[str] = []
    if known_skills:
        flagged_skills = _flag_unknown_skills(changes, known_skills)

    if flagged_skills and confirm_flagged_skills is None:
        record.status = "pending"
        db.commit()
        return record, flagged_skills

    # Filter out unconfirmed flagged skills
    confirmed_set = {s.lower() for s in (confirm_flagged_skills or [])}
    if flagged_skills:
        def _is_confirmed(change: dict[str, Any]) -> bool:
            words = {w.strip(",.;()").lower() for w in change.get("content", "").split()}
            unconfirmed = [s for s in flagged_skills if s not in confirmed_set and s in words]
            return len(unconfirmed) == 0
        changes = [c for c in changes if _is_confirmed(c)]

    # ── Apply changes to DOCX ────────────────────────────────────────────────
    try:
        docx_bytes = _apply_changes_to_docx(path, changes)
    except Exception as exc:
        record.status = "error"
        record.error_message = f"Failed to apply changes to document: {exc}"
        db.commit()
        return record, []

    # ── Save tailored DOCX ───────────────────────────────────────────────────
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
