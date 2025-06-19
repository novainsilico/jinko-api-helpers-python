import unittest
from jinko_stats.sample_size import sample_size_continuous_outcome

class TestSampleSize(unittest.TestCase):
    def test_sample_size(self):
        sample_size = sample_size_continuous_outcome(0.05,0.1,10,2)
        self.assertEqual(
            sample_size,
            1
        )

if __name__ == "__main__":
    unittest.main()
