from app.services.email_parser import EmailParser


EXPOQUEIJO_HTML = """
<html>
  <body>
    <table><tr><td><img src="https://cdn.expoqueijo.test/destaque.jpg" width="900" height="500"></td></tr></table>
    <h1>ExpoQueijo Brasil anuncia programação oficial</h1>
    <blockquote>Festival reúne produtores, chefs e especialistas em Araxá.</blockquote>
    <p><strong>Programação técnica</strong></p>
    <p>A feira terá degustações, rodadas de negócio e palestras para o setor.</p>
    <p>Veja mais em <a href="https://expoqueijo.test" onclick="alert(1)">ExpoQueijo</a>.</p>
    <p><script>alert("xss")</script><iframe src="https://evil.test"></iframe></p>
    <p><img src="https://cdn.expoqueijo.test/galeria-1.jpg" width="640"></p>
    <p><img src="https://cdn.expoqueijo.test/galeria-2.jpg" width="640" onerror="alert(1)"></p>
    <table>
      <tr><td>Assessoria de Imprensa - telefone (34) 99999-0000 - email imprensa@expoqueijo.test</td></tr>
    </table>
    <p>Todos os direitos reservados © ExpoQueijo Brasil</p>
  </body>
</html>
"""


def test_parser_extracts_expoqueijo_structure() -> None:
    parsed = EmailParser().parse_html(
        EXPOQUEIJO_HTML,
        subject="Fwd: ExpoQueijo Brasil anuncia programação oficial",
    )

    assert parsed.title == "ExpoQueijo Brasil anuncia programação oficial"
    assert parsed.excerpt == "Festival reúne produtores, chefs e especialistas em Araxá."
    assert parsed.featured_image_url == "https://cdn.expoqueijo.test/destaque.jpg"
    assert "<h3>Programação técnica</h3>" in parsed.content_html
    assert "A feira terá degustações" in parsed.content_html
    assert parsed.gallery_image_urls == [
        "https://cdn.expoqueijo.test/galeria-1.jpg",
        "https://cdn.expoqueijo.test/galeria-2.jpg",
    ]


def test_parser_removes_signature_and_sanitizes_html() -> None:
    parsed = EmailParser().parse_html(EXPOQUEIJO_HTML, subject="Release ExpoQueijo")

    assert "Assessoria de Imprensa" not in parsed.content_html
    assert "Todos os direitos reservados" not in parsed.content_html
    assert "<script" not in parsed.content_html
    assert "<iframe" not in parsed.content_html
    assert "onclick" not in parsed.content_html
    assert "onerror" not in parsed.content_html

