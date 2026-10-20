import unittest
import numpy as np
from phase_analysis import analyze_two_channels, wrap_degrees

class TestPhaseAnalysis(unittest.TestCase):
    def test_phase_difference(self):
        frequency = 10e6
        sample_rate = 100e6
        t = np.arange(
            0,
            5e-6,
            1 / sample_rate,
        )
        phase_ref = 0.4
        phase_rf = 1.2
        reference = (
            1.5 * np.sin(2 * np.pi * frequency * t + phase_ref)
            + 0.05
        )
        rf = (
            0.8 * np.sin(2 * np.pi * frequency * t + phase_rf)
            - 0.02
        )
        result = analyze_two_channels(
            t,
            reference,
            rf,
            frequency,
        )
        expected = np.degrees(phase_rf - phase_ref)
        self.assertAlmostEqual(
            result["phase_difference_deg"],
            expected,
            places=6,
        )
        self.assertGreater(
            result["reference"].r_squared,
            0.999999,
        )
        self.assertGreater(
            result["rf"].r_squared,
            0.999999,
        )

    def test_angle_wrapping(self):
        self.assertAlmostEqual(wrap_degrees(190), -170)
        self.assertAlmostEqual(wrap_degrees(-190), 170)

if __name__ == "__main__":
    unittest.main()
