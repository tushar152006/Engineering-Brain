from app.services.repository_loader import normalize_github_url


def test_normalize_github_url_uses_main_and_master_fallbacks() -> None:
    name, archive_urls = normalize_github_url("https://github.com/example/demo")

    assert name == "example/demo"
    assert archive_urls == [
        "https://codeload.github.com/example/demo/zip/refs/heads/main",
        "https://codeload.github.com/example/demo/zip/refs/heads/master",
    ]


def test_normalize_github_url_supports_tree_branch_urls() -> None:
    name, archive_urls = normalize_github_url("https://github.com/example/demo/tree/dev")

    assert name == "example/demo"
    assert archive_urls == ["https://codeload.github.com/example/demo/zip/refs/heads/dev"]
