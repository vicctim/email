from app.services.imap_listener import ImapListener, RuleConfig


def test_matching_sender_contains() -> None:
    rule = RuleConfig(
        id=1,
        sender_contains="comuniquese2.com.br",
        sender_name_contains=None,
        subject_regex=None,
    )

    match = ImapListener._matching_rule(
        [rule],
        "ExpoQueijo Brasil <sistemas@comuniquese2.com.br>",
        "Release ExpoQueijo",
    )

    assert match == rule


def test_matching_sender_name_and_subject_regex() -> None:
    rule = RuleConfig(
        id=2,
        sender_contains=None,
        sender_name_contains="ExpoQueijo",
        subject_regex=r"Release\s+Especial",
    )

    match = ImapListener._matching_rule(
        [rule],
        "ExpoQueijo Brasil <release@example.com>",
        "RELEASE ESPECIAL - novidades",
    )

    assert match == rule


def test_matching_rejects_invalid_subject() -> None:
    rule = RuleConfig(
        id=3,
        sender_contains="example.com",
        sender_name_contains=None,
        subject_regex=r"ExpoQueijo",
    )

    match = ImapListener._matching_rule(
        [rule],
        "Contato <release@example.com>",
        "Outro assunto",
    )

    assert match is None

