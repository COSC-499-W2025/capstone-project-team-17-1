import unittest

from capstone.company_qualities import extract_company_qualities


class TestCompanyQualities(unittest.TestCase):
    def test_extract_values_and_style_and_keywords(self):
        text = """
        We are an innovative, customer-obsessed company.
        We value diversity and inclusion and operate in a fast-paced, agile environment.
        This is a hybrid role with some remote flexibility.
        """

        profile = extract_company_qualities(text, company_name="TestCorp")
        data = profile.to_json()

        # values
        self.assertIn("innovation", data["values"])
        self.assertIn("customer_focus", data["values"])
        self.assertIn("diversity", data["values"])

        # work style
        self.assertIn("fast_paced", data["work_style"])
        self.assertIn("agile", data["work_style"])
        self.assertIn("hybrid", data["work_style"])

        # keywords should include at least one value + one work_style
        self.assertIn("innovation", data["keywords"])
        self.assertIn("fast_paced", data["keywords"])

    def test_extract_preferred_skills_and_keywords(self):
        text = "We are looking for engineers with strong Python and AWS experience."
        profile = extract_company_qualities(text, company_name="TestCorp")
        data = profile.to_json()

        # preferred skills from JOB_SKILL_KEYWORDS
        self.assertIn("python", data["preferred_skills"])
        self.assertIn("aws", data["preferred_skills"])

        # keywords should include skills too
        self.assertIn("python", data["keywords"])
        self.assertIn("aws", data["keywords"])


if __name__ == "__main__":
    unittest.main()
