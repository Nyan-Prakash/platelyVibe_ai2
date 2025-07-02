# plately_ai/tests/test_elasticity_calculator.py

import unittest
import math
from plately_ai.simulation.elasticity_calculator import (
    calculate_arc_elasticity,
    calculate_ped_from_simulation_data,
    calculate_xed_from_simulation_data
)

class TestElasticityCalculator(unittest.TestCase):

    def test_calculate_arc_elasticity(self):
        # Standard elastic demand: P up 10->12, Q down 100->60. PED = -2.75
        self.assertAlmostEqual(calculate_arc_elasticity(q1=100, q2=60, p1=10, p2=12), -2.75)
        # Inelastic demand: P up 10->12, Q down 100->90. PED = -0.5789...
        self.assertAlmostEqual(calculate_arc_elasticity(q1=100, q2=90, p1=10, p2=12), -0.5789, places=4)
        # Perfectly inelastic: P up 10->12, Q same 100->100. PED = 0
        self.assertEqual(calculate_arc_elasticity(q1=100, q2=100, p1=10, p2=12), 0.0)
        # Price constant, quantity changes (perfectly elastic)
        self.assertEqual(calculate_arc_elasticity(q1=100, q2=120, p1=10, p2=10), math.inf)
        self.assertEqual(calculate_arc_elasticity(q1=100, q2=80, p1=10, p2=10), -math.inf)
        # Both constant
        self.assertEqual(calculate_arc_elasticity(q1=100, q2=100, p1=10, p2=10), 0.0)
        # Zero average quantity or price
        self.assertIsNone(calculate_arc_elasticity(q1=0, q2=0, p1=10, p2=12)) # Avg Q = 0
        self.assertIsNone(calculate_arc_elasticity(q1=10, q2=20, p1=0, p2=0)) # Avg P = 0
        # XED - Substitutes: P_B up 5->6, Q_A up 20->25. XED = 1.222...
        self.assertAlmostEqual(calculate_arc_elasticity(q1=20, q2=25, p1=5, p2=6), 1.2222, places=4)
        # XED - Complements: P_B up 5->6, Q_A down 20->15. XED = -1.555...
        self.assertAlmostEqual(calculate_arc_elasticity(q1=20, q2=15, p1=5, p2=6), -1.5555, places=4)

    def test_calculate_ped_from_simulation_data(self):
        sample_ped_data_valid = [
            {'price': 10.0, 'demand': 100, 'is_baseline': True, 'percentage_change': 0.0},
            {'price': 12.0, 'demand': 60, 'is_baseline': False, 'percentage_change': 0.2},
            {'price': 8.0, 'demand': 150, 'is_baseline': False, 'percentage_change': -0.2}
        ]
        results = calculate_ped_from_simulation_data(sample_ped_data_valid)
        self.assertEqual(len(results), 2)
        # First scenario: P 10->12, Q 100->60. PED = -2.75
        self.assertAlmostEqual(results[0]['ped_value'], -2.75)
        self.assertEqual(results[0]['percentage_change_price'], 0.2)
        # Second scenario: P 10->8, Q 100->150. PED = ((150-100)/125) / ((8-10)/9) = (0.4 / -0.2222) = -1.8
        self.assertAlmostEqual(results[1]['ped_value'], -1.8)
        self.assertEqual(results[1]['percentage_change_price'], -0.2)

        # Test with inferred baseline (no 'is_baseline' flag, uses percentage_change=0.0)
        sample_ped_data_inferred_baseline = [
            {'price': 10.0, 'demand': 100, 'percentage_change': 0.0}, # Baseline
            {'price': 12.0, 'demand': 60, 'percentage_change': 0.2}
        ]
        results_inferred = calculate_ped_from_simulation_data(sample_ped_data_inferred_baseline)
        self.assertEqual(len(results_inferred), 1)
        self.assertAlmostEqual(results_inferred[0]['ped_value'], -2.75)

        # Test insufficient data
        self.assertEqual(calculate_ped_from_simulation_data([sample_ped_data_valid[0]]), []) # Only baseline
        self.assertEqual(calculate_ped_from_simulation_data([]), []) # Empty

        # Test no baseline found
        sample_ped_data_no_baseline = [
            {'price': 12.0, 'demand': 60, 'is_baseline': False, 'percentage_change': 0.2},
            {'price': 8.0, 'demand': 150, 'is_baseline': False, 'percentage_change': -0.2}
        ]
        self.assertEqual(calculate_ped_from_simulation_data(sample_ped_data_no_baseline), [])


    def test_calculate_xed_from_simulation_data(self):
        sample_xed_data_substitutes = {
            'target_item_name': 'Item A', 'target_item_id': 'A1',
            'affecting_item_name': 'Item B', 'affecting_item_id': 'B1',
            'q_target_base': 20, 'q_target_scenario': 25,
            'p_affecting_base': 5.0, 'p_affecting_scenario': 6.0,
            'percentage_change_p_affecting': 0.2
        }
        result_sub = calculate_xed_from_simulation_data(sample_xed_data_substitutes)
        self.assertIsNotNone(result_sub)
        self.assertAlmostEqual(result_sub['xed_value'], 1.2222, places=4)

        sample_xed_data_complements = {
            'target_item_name': 'Item C', 'target_item_id': 'C1',
            'affecting_item_name': 'Item D', 'affecting_item_id': 'D1',
            'q_target_base': 50, 'q_target_scenario': 40,
            'p_affecting_base': 7.0, 'p_affecting_scenario': 8.0,
            'percentage_change_p_affecting': (8.0-7.0)/7.0
        }
        result_comp = calculate_xed_from_simulation_data(sample_xed_data_complements)
        self.assertIsNotNone(result_comp)
        # Q: (40-50)/45 = -0.2222. P: (8-7)/7.5 = 0.1333. XED = -0.2222 / 0.1333 = -1.666...
        self.assertAlmostEqual(result_comp['xed_value'], -1.6666, places=4)

        # Test invalid data
        self.assertIsNone(calculate_xed_from_simulation_data({}))
        self.assertIsNone(calculate_xed_from_simulation_data({'q_target_base': 10})) # Missing keys

if __name__ == '__main__':
    unittest.main()
