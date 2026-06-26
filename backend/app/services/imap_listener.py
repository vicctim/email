import asyncio
import base64
import logging
import re
import time
from dataclasses import dataclass
from email import policy
from email.header import decode_header, make_header
from email.parser import BytesParser
from email.utils import parseaddr
from typing import Any

from imapclient import IMAPClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.connection import session_factory
from app.database.models import EmailAccount, MatchRule
from app.security import decrypt_secret


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuleConfig:
    id: int
    sender_contains: str | None
    sender_name_contains: str | None
    subject_regex: str | None


@dataclass(frozen=True)
class AccountConfig:
    id: int
    name: str
    host: str
    port: int
    use_ssl: bool
    username: str
    password: str
    folder: str
    polling_interval_seconds: int
    rules: list[RuleConfig]


class ImapListener:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._stop_event = asyncio.Event()

    async def run_forever(self) -> None:
        logger.info("IMAP listener iniciado")
        while not self._stop_event.is_set():
            try:
                await self.run_once(use_idle=True)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Falha no ciclo do IMAP listener")
                await asyncio.sleep(10)
        logger.info("IMAP listener finalizado")

    def stop(self) -> None:
        self._stop_event.set()

    async def run_once(self, *, use_idle: bool = False) -> int:
        async with session_factory() as session:
            accounts = await self._load_account_configs(session)

        if not accounts:
            await asyncio.sleep(1 if not use_idle else 30)
            return 0

        results = await asyncio.gather(
            *(asyncio.to_thread(self._process_account, account, use_idle) for account in accounts),
            return_exceptions=True,
        )

        processed = 0
        for result in results:
            if isinstance(result, Exception):
                logger.error(
                    "Erro ao processar conta IMAP",
                    exc_info=(type(result), result, result.__traceback__),
                )
            else:
                processed += int(result)
        return processed

    async def _load_account_configs(self, session: AsyncSession) -> list[AccountConfig]:
        account_rows = (
            await session.scalars(select(EmailAccount).where(EmailAccount.is_active.is_(True)))
        ).all()

        configs: list[AccountConfig] = []
        for account in account_rows:
            rules = (
                await session.scalars(
                    select(MatchRule).where(
                        MatchRule.email_account_id == account.id,
                        MatchRule.active.is_(True),
                    )
                )
            ).all()
            rule_configs = [
                RuleConfig(
                    id=rule.id,
                    sender_contains=rule.sender_contains,
                    sender_name_contains=rule.sender_name_contains,
                    subject_regex=rule.subject_regex,
                )
                for rule in rules
            ]
            if not rule_configs:
                continue
            configs.append(
                AccountConfig(
                    id=account.id,
                    name=account.name,
                    host=account.imap_host,
                    port=account.imap_port,
                    use_ssl=account.use_ssl,
                    username=account.username,
                    password=decrypt_secret(account.encrypted_password),
                    folder=account.folder,
                    polling_interval_seconds=account.polling_interval_seconds or 60,
                    rules=rule_configs,
                )
            )
        return configs

    def _process_account(self, account: AccountConfig, use_idle: bool) -> int:
        if not account.password:
            logger.warning("Conta IMAP sem senha configurada: %s", account.username)
            return 0

        with IMAPClient(account.host, port=account.port, ssl=account.use_ssl) as client:
            client.login(account.username, account.password)
            client.select_folder(account.folder)

            processed = self._process_unseen_messages(client, account)
            if use_idle:
                try:
                    client.idle()
                    responses = client.idle_check(timeout=account.polling_interval_seconds)
                    client.idle_done()
                    if responses:
                        processed += self._process_unseen_messages(client, account)
                except Exception:
                    logger.exception("IMAP IDLE indisponível; usando polling para %s", account.username)
                    time.sleep(account.polling_interval_seconds)
            return processed

    async def load_single_rule_config(
        self,
        session: AsyncSession,
        account_id: int,
        rule_id: int,
    ) -> AccountConfig | None:
        """Carrega a conta e apenas a regra solicitada para execução manual."""
        account = await session.get(EmailAccount, account_id)
        if not account or not account.is_active:
            return None

        rule = await session.get(MatchRule, rule_id)
        if not rule or rule.email_account_id != account.id:
            return None

        return AccountConfig(
            id=account.id,
            name=account.name,
            host=account.imap_host,
            port=account.imap_port,
            use_ssl=account.use_ssl,
            username=account.username,
            password=decrypt_secret(account.encrypted_password),
            folder=account.folder,
            polling_interval_seconds=30,
            rules=[
                RuleConfig(
                    id=rule.id,
                    sender_contains=rule.sender_contains,
                    sender_name_contains=rule.sender_name_contains,
                    subject_regex=rule.subject_regex,
                )
            ],
        )

    def run_single_rule_config(self, config: AccountConfig) -> int:
        """Executa IMAP de forma síncrona usando dados já carregados do banco."""
        return self._process_account(config, use_idle=False)

    def _process_unseen_messages(self, client: IMAPClient, account: AccountConfig) -> int:
        uids = client.search(["UNSEEN"])
        if not uids:
            return 0

        processed = 0
        fetched = client.fetch(uids, ["BODY.PEEK[]"])
        for uid, payload in fetched.items():
            try:
                raw_email = self._raw_email_from_payload(payload)
                if not raw_email:
                    continue

                headers = self._headers(raw_email)
                rule = self._matching_rule(account.rules, headers["from"], headers["subject"])
                if not rule:
                    continue

                self._enqueue_email(
                    account_id=account.id,
                    rule_id=rule.id,
                    email_uid=str(uid),
                    raw_email=raw_email,
                )
                processed += 1

                # Marca como lido e aplica label apenas quando enfileirado com sucesso,
                # para que emails fora dos filtros nao sejam alterados.
                client.add_flags([uid], ["\\Seen"])
                self._apply_processed_label(client, uid)
            except Exception:
                # Loga o erro mas nao altera o email na caixa —
                # assim emails problematicos nao sao marcados como lidos
                # e podem ser reavaliados na proxima execucao.
                logger.debug(
                    "Erro ao processar UID %s da conta %s",
                    uid,
                    account.id,
                    exc_info=True,
                )
        return processed

    @staticmethod
    def _raw_email_from_payload(payload: dict[Any, Any]) -> bytes | None:
        # BODY.PEEK[] retorna a chave b"BODY[]"—usar PEEK evita marcar como lido automaticamente
        value = (
            payload.get(b"BODY[]")
            or payload.get("BODY[]")
            or payload.get(b"RFC822")  # fallback para servidores antigos
            or payload.get("RFC822")
        )
        return value if isinstance(value, bytes) else None

    @staticmethod
    def _headers(raw_email: bytes) -> dict[str, str]:
        message = BytesParser(policy=policy.default).parsebytes(raw_email)
        return {
            "from": _decode_header_value(str(message.get("from", "") or "")),
            "subject": _decode_header_value(str(message.get("subject", "") or "")),
        }

    @staticmethod
    def _matching_rule(rules: list[RuleConfig], from_header: str, subject: str) -> RuleConfig | None:
        sender_name, sender_email = parseaddr(from_header)
        sender_blob = f"{sender_name} {sender_email} {from_header}".lower()
        sender_name = sender_name.lower()

        for rule in rules:
            has_filter = bool(rule.sender_contains or rule.sender_name_contains or rule.subject_regex)
            if not has_filter:
                continue
            if rule.sender_contains and rule.sender_contains.lower() not in sender_blob:
                continue
            if rule.sender_name_contains and rule.sender_name_contains.lower() not in sender_name:
                continue
            if rule.subject_regex:
                try:
                    if not re.search(rule.subject_regex, subject or "", flags=re.IGNORECASE):
                        continue
                except re.error:
                    logger.warning("Regex inválida na regra %s: %s", rule.id, rule.subject_regex)
                    continue
            return rule
        return None

    @staticmethod
    def _enqueue_email(*, account_id: int, rule_id: int, email_uid: str, raw_email: bytes) -> None:
        from app.workers.tasks import process_email

        process_email.apply_async(
            kwargs={
                "email_account_id": account_id,
                "match_rule_id": rule_id,
                "email_uid": email_uid,
                "raw_email_b64": base64.b64encode(raw_email).decode("ascii"),
            },
            queue="default",
        )

    @staticmethod
    def _apply_processed_label(client: IMAPClient, uid: int) -> None:
        try:
            add_labels = getattr(client, "add_gmail_labels", None)
            if callable(add_labels):
                add_labels([uid], ["Processed/EmailExtractor"])
        except Exception:
            logger.debug("Não foi possível aplicar label Gmail ao UID %s", uid, exc_info=True)


def _decode_header_value(value: str) -> str:
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


async def run_polling_cycle() -> int:
    return await ImapListener().run_once(use_idle=False)
