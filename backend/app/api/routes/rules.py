from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.api.schemas import MatchRuleCreate, MatchRuleRead, MatchRuleUpdate
from app.database.models import MatchRule
from app.services.audit import add_audit_log


router = APIRouter(prefix="/api/rules", tags=["rules"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[MatchRuleRead])
async def list_rules(session: AsyncSession = Depends(get_db)) -> list[MatchRule]:
    return list((await session.scalars(select(MatchRule).order_by(MatchRule.name))).all())


@router.post("", response_model=MatchRuleRead, status_code=status.HTTP_201_CREATED)
async def create_rule(payload: MatchRuleCreate, session: AsyncSession = Depends(get_db)) -> MatchRule:
    rule = MatchRule(**payload.model_dump())
    session.add(rule)
    await session.flush()
    add_audit_log(
        session,
        event="rule_created",
        message=f"Regra de matching criada: {rule.name}",
        payload={"rule_id": rule.id, "email_account_id": rule.email_account_id, "wordpress_site_id": rule.wordpress_site_id},
    )
    await session.commit()
    await session.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=MatchRuleRead)
async def get_rule(rule_id: int, session: AsyncSession = Depends(get_db)) -> MatchRule:
    return await _rule_or_404(session, rule_id)


@router.put("/{rule_id}", response_model=MatchRuleRead)
async def update_rule(
    rule_id: int,
    payload: MatchRuleUpdate,
    session: AsyncSession = Depends(get_db),
) -> MatchRule:
    rule = await _rule_or_404(session, rule_id)
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(rule, key, value)
    add_audit_log(
        session,
        event="rule_updated",
        message=f"Regra de matching atualizada: {rule.name}",
        payload={"rule_id": rule.id, "fields": sorted(values.keys())},
    )
    await session.commit()
    await session.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: int, session: AsyncSession = Depends(get_db)) -> None:
    rule = await _rule_or_404(session, rule_id)
    add_audit_log(
        session,
        event="rule_deleted",
        message=f"Regra de matching removida: {rule.name}",
        payload={"rule_id": rule.id},
    )
    await session.delete(rule)
    await session.commit()


@router.patch("/{rule_id}/toggle", response_model=MatchRuleRead)
async def toggle_rule(rule_id: int, session: AsyncSession = Depends(get_db)) -> MatchRule:
    rule = await _rule_or_404(session, rule_id)
    rule.active = not rule.active
    add_audit_log(
        session,
        event="rule_toggled",
        message=f"Regra de matching {'ativada' if rule.active else 'desativada'}: {rule.name}",
        payload={"rule_id": rule.id, "active": rule.active},
    )
    await session.commit()
    await session.refresh(rule)
    return rule


async def _rule_or_404(session: AsyncSession, rule_id: int) -> MatchRule:
    rule = await session.get(MatchRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    return rule
