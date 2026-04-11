import unittest

from src.models import CuratedNewsletter, NewsletterEntry
from src.services.telegram_service import (
    TELEGRAM_MESSAGE_LIMIT,
    render_curated_newsletter_html,
    sanitize_telegram_html,
    split_telegram_html_message,
)


class TelegramServiceTests(unittest.TestCase):
    def test_split_telegram_html_message_respects_limit(self):
        long_message = "<b>Title</b>\n\n" + ("A" * (TELEGRAM_MESSAGE_LIMIT + 200))

        chunks = split_telegram_html_message(long_message, limit=400)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 400 for chunk in chunks))

    def test_split_telegram_html_message_keeps_tags_balanced(self):
        long_message = "<a href=\"https://example.com\">" + ("A" * 450) + "</a>"

        chunks = split_telegram_html_message(long_message, limit=100)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 100 for chunk in chunks))
        self.assertTrue(all(chunk.count("<a ") == chunk.count("</a>") for chunk in chunks))

    def test_render_curated_newsletter_html_contains_sections_and_links(self):
        curated = CuratedNewsletter(
            headline="Ban tin AI",
            lead="4 muc dang chu y hom nay.",
            repos=[
                NewsletterEntry(
                    kind="repo",
                    title="Agents SDK",
                    url="https://github.com/openai/agents-sdk",
                    tldr="SDK de build AI agents.",
                    why_it_matters="Giup build workflow agent nhanh hon.",
                    highlights=["Tool calling", "Tracing"],
                    source_signal="1,234 stars today",
                )
            ],
            papers=[
                NewsletterEntry(
                    kind="paper",
                    title="SkillClaw",
                    url="https://arxiv.org/abs/2604.08377",
                    tldr="Paper ve skill evolution.",
                    why_it_matters="Mo rong cach quan ly ky nang agent.",
                    highlights=["Multi-user", "Continuous improvement"],
                    source_signal="171 upvotes",
                )
            ],
        )

        html = render_curated_newsletter_html(curated)

        self.assertIn("<b>GitHub nổi bật</b>", html)
        self.assertIn("https://github.com/openai/agents-sdk", html)
        self.assertIn("<b>Paper nổi bật</b>", html)
        self.assertIn("171 upvotes", html)

    def test_render_curated_newsletter_html_escapes_url_attribute(self):
        curated = CuratedNewsletter(
            headline="Ban tin AI",
            lead="Lead",
            repos=[
                NewsletterEntry(
                    kind="repo",
                    title="Repo X",
                    url='https://example.com/?a="b"&c=1',
                    tldr="TLDR",
                    why_it_matters="Impact",
                )
            ],
        )

        html = render_curated_newsletter_html(curated)

        self.assertIn("&quot;b&quot;", html)
        self.assertIn("&amp;c=1", html)

    def test_sanitize_telegram_html_converts_unsupported_list_tags(self):
        raw_html = "<b>Title</b><br><ul><li>One</li><li>Two</li></ul>"

        sanitized = sanitize_telegram_html(raw_html)

        self.assertNotIn("<ul>", sanitized)
        self.assertNotIn("<li>", sanitized)
        self.assertIn("• One", sanitized)
        self.assertIn("• Two", sanitized)


if __name__ == "__main__":
    unittest.main()
