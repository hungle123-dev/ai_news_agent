import unittest

import requests

from src.tools.github_tool import get_daily_trending_repos, parse_trending_repos_from_html


SAMPLE_TRENDING_HTML = """
<article class="Box-row">
  <h2><a href="/openai/agents-sdk"> openai / agents-sdk </a></h2>
  <p>Framework to build AI agents with tool use.</p>
  <span itemprop="programmingLanguage">Python</span>
  <span>1,234 stars today</span>
</article>
<article class="Box-row">
  <h2><a href="/jqlang/jq"> jqlang / jq </a></h2>
  <p>Lightweight JSON processor.</p>
  <span itemprop="programmingLanguage">C</span>
  <span>321 stars today</span>
</article>
"""


class GithubToolTests(unittest.TestCase):
    def test_parse_trending_repos_from_html_extracts_core_fields(self):
        repos = parse_trending_repos_from_html(SAMPLE_TRENDING_HTML)

        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0].repo_path, "openai/agents-sdk")
        self.assertEqual(repos[0].language, "Python")
        self.assertEqual(repos[0].stars_today, 1234)
        self.assertEqual(repos[1].repo_url, "https://github.com/jqlang/jq")

    def test_get_daily_trending_repos_returns_empty_on_request_error(self):
        class FailingSession:
            def get(self, *args, **kwargs):
                raise requests.RequestException("network down")

        repos = get_daily_trending_repos(session=FailingSession())

        self.assertEqual(repos, [])


if __name__ == "__main__":
    unittest.main()
