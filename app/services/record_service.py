from datetime import date, datetime

from sqlalchemy import or_
from sqlmodel import Session, col, select

from app.exceptions import AppError
from app.models import FinancialRecord, RecordType, User, UserRole


def _scope_user_ids_for_list(actor: User, filter_user_id: int | None) -> list[int] | None:
    """
    Return None = no extra user filter (all users).
    Return [id] = restrict to that user.
    """
    if actor.role == UserRole.viewer:
        return [actor.id]
    if actor.role == UserRole.analyst:
        if filter_user_id is not None:
            return [filter_user_id]
        return None
    # admin
    if filter_user_id is not None:
        return [filter_user_id]
    return None


def create_record(session: Session, actor: User, *, amount: float, type_: RecordType, category: str, d: date, notes: str | None) -> FinancialRecord:
    rec = FinancialRecord(
        user_id=actor.id,
        amount=amount,
        type=type_,
        category=category,
        date=d,
        notes=notes,
        is_deleted=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec


def list_records(
    session: Session,
    actor: User,
    *,
    date_from: date | None,
    date_to: date | None,
    type_: RecordType | None,
    category: str | None,
    user_id: int | None,
    q: str | None,
    offset: int,
    limit: int,
    include_deleted: bool,
) -> tuple[list[FinancialRecord], int]:
    scope = _scope_user_ids_for_list(actor, user_id)
    stmt = select(FinancialRecord)
    if not include_deleted:
        stmt = stmt.where(FinancialRecord.is_deleted == False)  # noqa: E712
    if scope is not None:
        stmt = stmt.where(col(FinancialRecord.user_id).in_(scope))
    if date_from is not None:
        stmt = stmt.where(FinancialRecord.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(FinancialRecord.date <= date_to)
    if type_ is not None:
        stmt = stmt.where(FinancialRecord.type == type_)
    if category:
        stmt = stmt.where(FinancialRecord.category == category)
    if q:
        pat = f"%{q}%"
        stmt = stmt.where(
            or_(
                col(FinancialRecord.category).ilike(pat),
                col(FinancialRecord.notes).ilike(pat),
            )
        )
    count_stmt = select(FinancialRecord)
    if not include_deleted:
        count_stmt = count_stmt.where(FinancialRecord.is_deleted == False)  # noqa: E712
    if scope is not None:
        count_stmt = count_stmt.where(col(FinancialRecord.user_id).in_(scope))
    if date_from is not None:
        count_stmt = count_stmt.where(FinancialRecord.date >= date_from)
    if date_to is not None:
        count_stmt = count_stmt.where(FinancialRecord.date <= date_to)
    if type_ is not None:
        count_stmt = count_stmt.where(FinancialRecord.type == type_)
    if category:
        count_stmt = count_stmt.where(FinancialRecord.category == category)
    if q:
        pat = f"%{q}%"
        count_stmt = count_stmt.where(
            or_(
                col(FinancialRecord.category).ilike(pat),
                col(FinancialRecord.notes).ilike(pat),
            )
        )
    total = len(session.exec(count_stmt).all())
    stmt = stmt.order_by(FinancialRecord.date.desc(), FinancialRecord.id.desc()).offset(offset).limit(limit)
    rows = list(session.exec(stmt).all())
    return rows, total


def get_record(session: Session, actor: User, record_id: int) -> FinancialRecord:
    rec = session.get(FinancialRecord, record_id)
    if rec is None or rec.is_deleted:
        raise AppError("not_found", "Record not found.", 404)
    if actor.role == UserRole.viewer and rec.user_id != actor.id:
        raise AppError("forbidden", "You cannot access this record.", 403)
    if actor.role == UserRole.analyst:
        pass  # can read any non-deleted
    if actor.role == UserRole.admin:
        pass
    return rec


def _can_mutate_record(actor: User, rec: FinancialRecord) -> bool:
    if actor.role == UserRole.admin:
        return True
    if actor.role == UserRole.analyst and rec.user_id == actor.id:
        return True
    return False


def update_record(
    session: Session,
    actor: User,
    record_id: int,
    *,
    amount: float | None,
    type_: RecordType | None,
    category: str | None,
    d: date | None,
    notes: str | None,
) -> FinancialRecord:
    rec = session.get(FinancialRecord, record_id)
    if rec is None or rec.is_deleted:
        raise AppError("not_found", "Record not found.", 404)
    if not _can_mutate_record(actor, rec):
        raise AppError("forbidden", "You cannot update this record.", 403)
    if amount is not None:
        rec.amount = amount
    if type_ is not None:
        rec.type = type_
    if category is not None:
        rec.category = category
    if d is not None:
        rec.date = d
    if notes is not None:
        rec.notes = notes
    rec.updated_at = datetime.utcnow()
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec


def delete_record(session: Session, actor: User, record_id: int, hard: bool = False) -> None:
    rec = session.get(FinancialRecord, record_id)
    if rec is None:
        raise AppError("not_found", "Record not found.", 404)
    if rec.is_deleted and not hard:
        raise AppError("not_found", "Record not found.", 404)
    if not _can_mutate_record(actor, rec):
        raise AppError("forbidden", "You cannot delete this record.", 403)
    if hard:
        if actor.role != UserRole.admin:
            raise AppError("forbidden", "Hard delete requires admin.", 403)
        session.delete(rec)
        session.commit()
        return
    rec.is_deleted = True
    rec.updated_at = datetime.utcnow()
    session.add(rec)
    session.commit()
