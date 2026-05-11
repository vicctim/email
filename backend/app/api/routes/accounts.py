import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from imapclient import IMAPClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.api.schemas import EmailAccountCreate, EmailAccountRead, EmailAccountUpdate
from app.database.models import EmailAccount
from app.security import decrypt_secret, encrypt_secret
from app.services.audit import add_audit_log


router = APIRouter(prefix="/api/accounts", tags=["accounts"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[EmailAccountRead])
async def list_accounts(session: AsyncSession = Depends(get_db)) -> list[EmailAccount]:
    return list((await session.scalars(select(EmailAccount).order_by(EmailAccount.name))).all())


@router.post("", response_model=EmailAccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: EmailAccountCreate,
    session: AsyncSession = Depends(get_db),
) -> EmailAccount:
    account = EmailAccount(
        name=payload.name,
        imap_host=payload.imap_host,
        imap_port=payload.imap_port,
        use_ssl=payload.use_ssl,
        username=payload.username,
        encrypted_password=encrypt_secret(payload.password),
        folder=payload.folder,
        processed_folder=payload.processed_folder,
        polling_interval_seconds=payload.polling_interval_seconds,
        is_active=payload.is_active,
    )
    session.add(account)
    try:
        await session.flush()
        add_audit_log(
            session,
            event="account_created",
            message=f"Conta de email criada: {account.name}",
            payload={"account_id": account.id, "username": account.username},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Conta já cadastrada") from exc
    await session.refresh(account)
    return account


@router.get("/{account_id}", response_model=EmailAccountRead)
async def get_account(account_id: int, session: AsyncSession = Depends(get_db)) -> EmailAccount:
    return await _account_or_404(session, account_id)


@router.put("/{account_id}", response_model=EmailAccountRead)
async def update_account(
    account_id: int,
    payload: EmailAccountUpdate,
    session: AsyncSession = Depends(get_db),
) -> EmailAccount:
    account = await _account_or_404(session, account_id)
    values = payload.model_dump(exclude_unset=True)
    password = values.pop("password", None)
    if password:
        account.encrypted_password = encrypt_secret(password)
    for key, value in values.items():
        setattr(account, key, value)
    add_audit_log(
        session,
        event="account_updated",
        message=f"Conta de email atualizada: {account.name}",
        payload={"account_id": account.id, "fields": sorted(values.keys())},
    )
    await session.commit()
    await session.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: int, session: AsyncSession = Depends(get_db)) -> None:
    account = await _account_or_404(session, account_id)
    add_audit_log(
        session,
        event="account_deleted",
        message=f"Conta de email removida: {account.name}",
        payload={"account_id": account.id, "username": account.username},
    )
    await session.delete(account)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Conta possui registros relacionados") from exc


@router.post("/{account_id}/test")
async def test_account(account_id: int, session: AsyncSession = Depends(get_db)) -> dict[str, object]:
    account = await _account_or_404(session, account_id)
    try:
        await asyncio.to_thread(_test_imap_login, account)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao conectar no IMAP: {exc}") from exc
    return {"ok": True, "status": "connected"}


def _test_imap_login(account: EmailAccount) -> None:
    with IMAPClient(account.imap_host, port=account.imap_port, ssl=account.use_ssl) as client:
        client.login(account.username, decrypt_secret(account.encrypted_password))
        client.select_folder(account.folder)


async def _account_or_404(session: AsyncSession, account_id: int) -> EmailAccount:
    account = await session.get(EmailAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    return account
