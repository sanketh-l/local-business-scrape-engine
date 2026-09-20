from leadgen.normalize import normalize_domain, normalize_phone


def test_normalize_domain():
    assert normalize_domain("https://www.example.com/path?utm_source=x") == "example.com"


def test_normalize_phone_fallback():
    assert normalize_phone("(555) 123-4567") == "5551234567"
