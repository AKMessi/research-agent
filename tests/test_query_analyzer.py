import unittest

from research_agent.core.query_analyzer import OutputFormat, QueryAnalyzer, ResearchDomain


class QueryAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = QueryAnalyzer()

    def test_best_ways_query_prefers_how_to_report(self):
        result = self.analyzer.analyze("best ways to earn money online")
        self.assertEqual(result.domain, ResearchDomain.HOW_TO)
        self.assertEqual(result.output_format, OutputFormat.REPORT)

    def test_top_people_query_stays_profiles(self):
        result = self.analyzer.analyze("top AI researchers 2026")
        self.assertEqual(result.domain, ResearchDomain.PEOPLE)
        self.assertEqual(result.output_format, OutputFormat.PROFILES)


if __name__ == "__main__":
    unittest.main()
