import unittest
from capstone.company_qualities import extract_company_qualities

class TestCompanyQualities(unittest.TestCase):
    def test_extract_values_and_style(self):
        text = """
        We are an innovative, customer-obsessed company.
        We value diversity and inclusion and operate in a fast-paced, agile environment.
        This is a hybrid role with some remote flexibility.
        """

        profile = extract_company_qualities(text, company_name="TestCorp")

        self.assertIn("innovation", profile.values)
        self.assertIn("customer_focus", profile.values)
        self.assertIn("diversity", profile.values)
        self.assertIn("fast_paced", profile.work_style)
        self.assertIn("agile", profile.work_style)
        self.assertIn("hybrid", profile.work_style)

    def test_extract_preferred_skills(self):
        text = "We are looking for engineers with strong Python and AWS experience."
        profile = extract_company_qualities(text, company_name="TestCorp")

        self.assertIn("python", profile.preferred_skills)
        self.assertIn("aws", profile.preferred_skills)

if __name__ == "__main__":
    unittest.main()
