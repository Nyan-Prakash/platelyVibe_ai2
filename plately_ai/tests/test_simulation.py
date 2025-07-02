# plately_ai/tests/test_simulation.py

import unittest
import random
from plately_ai.simulation.customer_agent import CustomerAgent
from plately_ai.simulation.simulation_engine import SimulationEngine

class TestCustomerAgent(unittest.TestCase):
    def setUp(self):
        self.sample_menu_items = [
            {'id': 'item1', 'name': 'Burger A', 'price': 10.0},
            {'id': 'item2', 'name': 'Pizza B', 'price': 12.0},
            {'id': 'item3', 'name': 'Salad C', 'price': 8.0}
        ]
        self.item_ids = [item['id'] for item in self.sample_menu_items]
        random.seed(42) # for reproducible tests

    def test_agent_initialization(self):
        agent = CustomerAgent(agent_id="test_agent_01", budget_range=(50, 50), price_sensitivity=0.5)
        self.assertEqual(agent.agent_id, "test_agent_01")
        self.assertEqual(agent.budget, 50)
        self.assertEqual(agent.price_sensitivity, 0.5)
        self.assertEqual(agent.preferences, {})

    def test_generate_random_preferences(self):
        agent = CustomerAgent(agent_id="test_agent_02")
        agent.generate_random_preferences(self.item_ids)
        self.assertEqual(len(agent.preferences), len(self.item_ids))
        for item_id in self.item_ids:
            self.assertTrue(0.1 <= agent.preferences[item_id] <= 1.0)

    def test_calculate_utility(self):
        agent = CustomerAgent(agent_id="test_agent_03", price_sensitivity=1) # Utility = pref / price
        agent.preferences = {'item1': 0.8, 'item2': 0.9}

        utility1 = agent._calculate_utility(self.sample_menu_items[0], self.sample_menu_items) # Burger A, price 10
        self.assertAlmostEqual(utility1, 0.8 / 10.0)

        utility2 = agent._calculate_utility(self.sample_menu_items[1], self.sample_menu_items) # Pizza B, price 12
        self.assertAlmostEqual(utility2, 0.9 / 12.0)

        utility_unknown = agent._calculate_utility(self.sample_menu_items[2], self.sample_menu_items) # Salad C, no pref
        self.assertEqual(utility_unknown, 0) # No preference, so utility is 0

    def test_choose_items_budget_and_preference(self):
        agent = CustomerAgent(agent_id="test_agent_04", budget_range=(15, 15), price_sensitivity=0.5)
        agent.preferences = {'item1': 0.9, 'item2': 0.7, 'item3': 0.8} # Prefers Burger, then Salad, then Pizza
        # Prices: item1:10, item2:12, item3:8
        # Utilities (approx, sensitivity 0.5):
        # item1: 0.9 / sqrt(10) ~ 0.28
        # item2: 0.7 / sqrt(12) ~ 0.20
        # item3: 0.8 / sqrt(8)  ~ 0.28 (similar to item1, slightly higher due to lower price impact)
        # Expected choice order: item3 (Salad), then item1 (Burger) if budget allows

        chosen = agent.choose_items(self.sample_menu_items, max_items_to_choose=2)
        chosen_ids = [item['id'] for item in chosen]

        # Based on utility (Salad C then Burger A), budget $15.
        # Salad C ($8) chosen first. Remaining budget $7. Burger A ($10) cannot be afforded.
        self.assertEqual(len(chosen_ids), 1)
        self.assertIn('item3', chosen_ids) # Salad C

    def test_choose_items_max_items(self):
        agent = CustomerAgent(agent_id="test_agent_05", budget_range=(100, 100), price_sensitivity=0.1) # Low sensitivity
        agent.generate_random_preferences(self.item_ids) # Random but consistent due to seed

        chosen = agent.choose_items(self.sample_menu_items, max_items_to_choose=1)
        self.assertEqual(len(chosen), 1)

        chosen_two = agent.choose_items(self.sample_menu_items, max_items_to_choose=2)
        self.assertEqual(len(chosen_two), 2)


class TestSimulationEngine(unittest.TestCase):
    def setUp(self):
        self.sample_menu = [
            {'id': 'burger', 'name': 'Classic Burger', 'price': 10.0},
            {'id': 'pizza', 'name': 'Pepperoni Pizza', 'price': 12.0},
            {'id': 'salad', 'name': 'Caesar Salad', 'price': 8.0}
        ]
        random.seed(123) # for reproducible tests
        self.engine = SimulationEngine(menu_items=list(self.sample_menu), num_agents=10)

    def test_engine_initialization(self):
        self.assertEqual(len(self.engine.agents), 10)
        self.assertEqual(len(self.engine.menu_items_master_list), 3)
        self.assertEqual(self.engine.current_menu_items[0]['price'], 10.0)

    def test_update_menu_item_price(self):
        self.engine.update_menu_item_price('burger', 11.0)
        self.assertEqual(self.engine.current_menu_items[0]['price'], 11.0)
        # Test invalid item
        self.assertFalse(self.engine.update_menu_item_price('nonexistent', 15.0))
        # Test invalid price
        self.assertFalse(self.engine.update_menu_item_price('burger', -5.0))


    def test_run_simulation_step_and_analyze(self):
        # With fixed seed, agent preferences & choices should be somewhat predictable for a small N
        # This is more of an integration test for the simulation loop
        choices = self.engine.run_simulation_step(max_items_per_agent=1)
        self.assertIsInstance(choices, list)
        # Each agent should make at most 1 choice. Some might choose nothing if budget is too low or no utility.
        self.assertTrue(len(choices) <= self.engine.num_agents)

        analysis = self.engine.analyze_results(choices)
        self.assertIn('total_revenue', analysis)
        self.assertIn('demand_per_item', analysis)
        self.assertEqual(len(analysis['demand_per_item']), len(self.sample_menu))

        # Check if total items sold matches the length of choices
        self.assertEqual(analysis['total_items_sold'], len(choices))

        # Check if total revenue is sum of prices of chosen items
        calculated_revenue = sum(c['item_price_at_purchase'] for c in choices)
        self.assertAlmostEqual(analysis['total_revenue'], calculated_revenue)


    def test_run_price_scenario(self):
        baseline_analysis = self.engine.run_price_scenario('burger', 10.0) # Baseline price

        # Increase burger price
        scenario_analysis = self.engine.run_price_scenario('burger', 15.0)

        self.assertIsNotNone(baseline_analysis)
        self.assertIsNotNone(scenario_analysis)

        # Expect total revenue to change, and demand for burger to potentially decrease
        # Exact values depend on the random agent generation, but should be different
        # self.assertNotEqual(baseline_analysis['total_revenue'], scenario_analysis['total_revenue'])
        # This is not guaranteed, could be same by chance, but less likely with more agents

        burger_demand_baseline = baseline_analysis['demand_per_item'].get('Classic Burger', 0)
        burger_demand_scenario = scenario_analysis['demand_per_item'].get('Classic Burger', 0)

        # With price increase, demand for burger is expected to be less or equal (can't be more unless very specific cross-effects not modeled here)
        self.assertTrue(burger_demand_scenario <= burger_demand_baseline)

        # Ensure menu is reset after scenario
        self.assertEqual(self.engine.current_menu_items[0]['price'], self.sample_menu[0]['price'])

    def test_run_ped_simulation_set(self):
        item_id_to_vary = 'burger'
        price_changes = [-0.1, 0.1] # -10% and +10%

        ped_data = self.engine.run_ped_simulation_set(item_id_to_vary, price_changes)
        self.assertIsNotNone(ped_data)
        self.assertEqual(len(ped_data), len(price_changes) + 1) # Baseline + number of changes

        baseline_point = next(p for p in ped_data if p.get('is_baseline'))
        self.assertIsNotNone(baseline_point)
        self.assertEqual(baseline_point['price'], self.sample_menu[0]['price']) # Burger price is 10.0

        # Check one of the scenario points
        scenario_point_plus_10 = next(p for p in ped_data if p.get('percentage_change') == 0.1)
        self.assertIsNotNone(scenario_point_plus_10)
        self.assertAlmostEqual(scenario_point_plus_10['price'], 10.0 * 1.1)
        self.assertIn('demand', scenario_point_plus_10)

        # Test with invalid item ID
        invalid_ped_data = self.engine.run_ped_simulation_set('nonexistent_item', price_changes)
        self.assertIsNone(invalid_ped_data)

        # Test with price change that makes price negative (should be skipped)
        # Base price of salad is 8.0. -110% would make it negative.
        salad_id = 'salad'
        extreme_price_changes = [-1.1] # -110%
        # We need to ensure the engine handles this gracefully by skipping the negative price scenario
        # The run_ped_simulation_set prints a warning and skips.
        # So, the returned data should only contain the baseline.
        ped_data_negative_price = self.engine.run_ped_simulation_set(salad_id, extreme_price_changes)
        self.assertIsNotNone(ped_data_negative_price)
        # It should contain baseline + any valid scenarios. Here, only baseline.
        self.assertEqual(len(ped_data_negative_price), 1)
        self.assertTrue(ped_data_negative_price[0].get('is_baseline'))


    def test_run_xed_simulation_set(self):
        target_item_id = 'pizza'    # Demand of Pizza
        affecting_item_id = 'burger' # Price of Burger changes
        price_change_percentage = 0.2 # Burger price +20%

        xed_data = self.engine.run_xed_simulation_set(target_item_id, affecting_item_id, price_change_percentage)
        self.assertIsNotNone(xed_data)
        self.assertEqual(xed_data['target_item_id'], target_item_id)
        self.assertEqual(xed_data['affecting_item_id'], affecting_item_id)
        self.assertAlmostEqual(xed_data['p_affecting_base'], self.sample_menu[0]['price']) # Burger base price 10.0
        self.assertAlmostEqual(xed_data['p_affecting_scenario'], 10.0 * (1 + price_change_percentage))
        self.assertIn('q_target_base', xed_data)
        self.assertIn('q_target_scenario', xed_data)

        # Test with invalid target item ID
        invalid_xed_target = self.engine.run_xed_simulation_set('nonexistent', affecting_item_id, price_change_percentage)
        self.assertIsNone(invalid_xed_target)

        # Test with invalid affecting item ID
        invalid_xed_affecting = self.engine.run_xed_simulation_set(target_item_id, 'nonexistent', price_change_percentage)
        self.assertIsNone(invalid_xed_affecting)

        # Test with same target and affecting item ID
        same_item_xed = self.engine.run_xed_simulation_set(target_item_id, target_item_id, price_change_percentage)
        self.assertIsNone(same_item_xed) # Should return None as per implementation

        # Test with price change that makes affecting item price negative
        # Burger base price 10.0. -110% change.
        xed_negative_price = self.engine.run_xed_simulation_set(target_item_id, affecting_item_id, -1.1)
        self.assertIsNone(xed_negative_price) # Should be skipped and return None


if __name__ == '__main__':
    unittest.main()
