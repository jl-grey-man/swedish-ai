"""Test credibility checking."""
from phases.phase2_5_credibility import deterministic_credibility_check


def test_detects_brand_studio():
    """Should detect Brand Studio sponsored content."""
    html = "Artikeln är producerad av Brand Studio i samarbete med MediaTell"
    url = "https://di.se/brandstudio/test"
    
    result = deterministic_credibility_check(url, html)
    
    assert result["auto_reject"] == True
    assert any("brand" in flag.lower() for flag in result["red_flags"])
    assert any("brandstudio" in flag.lower() for flag in result["red_flags"])


def test_detects_annons():
    """Should detect 'annons' (advertisement) marker."""
    html = "<div class='annons'>Detta är en annons</div>"
    url = "https://breakit.se/article/test"
    
    result = deterministic_credibility_check(url, html)
    
    assert result["auto_reject"] == True
    assert any("annons" in flag.lower() for flag in result["red_flags"])


def test_detects_sponsored_url():
    """Should detect sponsored content in URL."""
    html = "Regular content"
    url = "https://di.se/sponsored/article-123"
    
    result = deterministic_credibility_check(url, html)
    
    assert result["auto_reject"] == True
    assert any("sponsored" in flag.lower() for flag in result["red_flags"])


def test_allows_normal_swedish_content():
    """Should allow normal Swedish business content."""
    html = "Detta är en vanlig artikel om svenska företag och deras problem"
    url = "https://breakit.se/artikel/test-123"
    
    result = deterministic_credibility_check(url, html)
    
    assert result["auto_reject"] == False
    assert result["is_nordic"] == True


def test_detects_non_nordic_geography():
    """Should flag non-Nordic sources."""
    html = "Regular content"
    url = "https://techcrunch.com/article/test"
    
    result = deterministic_credibility_check(url, html)
    
    assert result["auto_reject"] == False  # Not auto-reject, but flagged
    assert result["is_nordic"] == False
    assert any("non_nordic" in flag for flag in result["red_flags"])


def test_accepts_danish_content():
    """Should accept Danish LinkedIn posts."""
    html = "Jeg har længe manglet et effektivt system"
    url = "https://dk.linkedin.com/posts/test-123"
    
    result = deterministic_credibility_check(url, html)
    
    assert result["is_nordic"] == True


def test_accepts_norwegian_content():
    """Should accept Norwegian content."""
    html = "Vi jobber med AI"
    url = "https://dn.no/article/test"
    
    result = deterministic_credibility_check(url, html)
    
    assert result["is_nordic"] == True


def test_accepts_swedish_reddit():
    """Should accept Swedish Reddit posts."""
    html = "Discussion about Swedish businesses"
    url = "https://www.reddit.com/r/sweden/comments/abc123/test"
    
    result = deterministic_credibility_check(url, html)
    
    assert result["is_nordic"] == True


def test_rejects_singapore_reddit():
    """Should flag non-Nordic Reddit posts."""
    html = "SME discussion"
    url = "https://www.reddit.com/r/singapore/comments/abc123/test"
    
    result = deterministic_credibility_check(url, html)
    
    assert result["is_nordic"] == False
