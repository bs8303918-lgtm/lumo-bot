from services.page_fetch import html_to_text, is_fetchable_page_url


def test_youthop_url_fetchable():
    assert is_fetchable_page_url("https://www.youthop.com/") is True
    assert is_fetchable_page_url(
        "https://www.youthop.com/scholarships/daad-helmut-schmidt-programme-masters-scholarships-2027"
    )


def test_skip_telegram_and_instagram():
    assert is_fetchable_page_url("https://t.me/somechannel") is False
    assert is_fetchable_page_url("https://www.instagram.com/p/abc") is False
    assert is_fetchable_page_url("https://facebook.com/page") is False


def test_skip_private_and_invalid():
    assert is_fetchable_page_url("not-a-url") is False
    assert is_fetchable_page_url("https://localhost/x") is False
    assert is_fetchable_page_url("https://192.168.1.1/x") is False
    assert is_fetchable_page_url(None) is False


def test_html_to_text_strips_scripts_and_keeps_body():
    html = """
    <html><head><title>T</title><script>evil()</script><style>.x{}</style></head>
    <body>
      <nav>Menu</nav>
      <h1>Youth Opportunities</h1>
      <p>Deadline: 30 June 2026</p>
      <script>more()</script>
    </body></html>
    """
    text = html_to_text(html)
    assert "Youth Opportunities" in text
    assert "Deadline: 30 June 2026" in text
    assert "evil" not in text
    assert "more()" not in text
    assert "Menu" not in text
