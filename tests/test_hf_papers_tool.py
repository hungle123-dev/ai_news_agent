import unittest

from src.tools.hf_papers_tool import _candidate_dates, normalize_daily_paper


class HFPapersToolTests(unittest.TestCase):
    def test_normalize_daily_paper_supports_nested_payload(self):
        payload = {
            "paper": {
                "id": "2604.08377",
                "title": "SkillClaw",
                "summary": "A framework for evolving agent skills.",
                "ai_keywords": ["agents", "skills", "evolution"],
                "upvotes": 171,
            }
        }

        normalized = normalize_daily_paper(payload)

        self.assertEqual(normalized["title"], "SkillClaw")
        self.assertEqual(normalized["upvotes"], 171)
        self.assertEqual(normalized["url"], "https://arxiv.org/abs/2604.08377")
        self.assertEqual(normalized["keywords"], ["agents", "skills", "evolution"])

    def test_candidate_dates_falls_back_when_input_date_invalid(self):
        dates = _candidate_dates("2026-99-99")

        self.assertEqual(len(dates), 2)
        self.assertRegex(dates[0], r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(dates[1], r"^\d{4}-\d{2}-\d{2}$")


if __name__ == "__main__":
    unittest.main()
