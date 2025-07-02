# plately_ai/simulation/simulation_engine.py

import random
import pandas as pd
from .customer_agent import CustomerAgent # Assuming customer_agent.py is in the same directory

class SimulationEngine:
    """
    Manages and runs the demand simulation using CustomerAgents.
    """
    def __init__(self, menu_items, num_agents=100, agent_budget_range=(20, 100), agent_price_sensitivity_range=(0.2, 0.8)):
        """
        Initializes the SimulationEngine.

        :param menu_items: A list of menu item dictionaries.
                           Each item must have 'id', 'name', and 'price'.
                           Example: [{'id': 'item1', 'name': 'Item 1', 'price': 10.00}, ...]
        :param num_agents: The number of customer agents to create for the simulation.
        :param agent_budget_range: Tuple (min, max) for agent budgets.
        :param agent_price_sensitivity_range: Tuple (min, max) for agent price sensitivities.
        """
        self.menu_items_master_list = self._validate_menu_items(menu_items) # Store the original menu
        self.current_menu_items = list(self.menu_items_master_list) # Menu used in current simulation run, can be modified
        self.num_agents = num_agents
        self.agent_budget_range = agent_budget_range
        self.agent_price_sensitivity_range = agent_price_sensitivity_range
        self.agents = []
        self.all_item_ids = [item['id'] for item in self.menu_items_master_list]

        self._create_agents()

    def _validate_menu_items(self, menu_items):
        if not isinstance(menu_items, list):
            raise ValueError("menu_items must be a list.")
        for item in menu_items:
            if not isinstance(item, dict) or not all(k in item for k in ['id', 'name', 'price']):
                raise ValueError("Each menu item must be a dictionary with 'id', 'name', and 'price'.")
            if not isinstance(item['price'], (int, float)) or item['price'] < 0:
                raise ValueError(f"Item '{item['name']}' has an invalid price: {item['price']}.")
        return [dict(item) for item in menu_items] # Return copies

    def _create_agents(self):
        """Creates the population of customer agents."""
        self.agents = []
        for i in range(self.num_agents):
            agent = CustomerAgent(
                agent_id=f"agent_{i:03d}",
                budget_range=self.agent_budget_range,
                price_sensitivity=random.uniform(self.agent_price_sensitivity_range[0], self.agent_price_sensitivity_range[1])
            )
            agent.generate_random_preferences(self.all_item_ids)
            self.agents.append(agent)

    def update_menu_item_price(self, item_id, new_price):
        """
        Updates the price of a specific menu item for the next simulation run.
        This modifies self.current_menu_items.
        """
        if not isinstance(new_price, (int, float)) or new_price < 0:
            # print(f"Warning: Invalid new price {new_price} for item {item_id}. Price not updated.") # Less verbose
            return False

        item_updated = False
        for item in self.current_menu_items:
            if item['id'] == item_id:
                item['price'] = new_price
                item_updated = True
                break
        if not item_updated:
            # print(f"Warning: Item ID {item_id} not found in current menu. Price not updated.") # Less verbose
            return False
        return True

    def reset_menu_to_master(self):
        """Resets self.current_menu_items to copies of the original master list items."""
        self.current_menu_items = [dict(item) for item in self.menu_items_master_list]


    def run_simulation_step(self, max_items_per_agent=3):
        """
        Runs one step of the simulation.
        Each agent makes their choices based on the current menu_items.

        :param max_items_per_agent: Max items an agent can choose.
        :return: A list of all choices made in this step.
                 Each choice is a dictionary like {'agent_id': ..., 'chosen_item_id': ..., 'item_price': ...}.
        """
        all_choices_this_step = []
        for agent in self.agents:
            agent.budget = random.uniform(self.agent_budget_range[0], self.agent_budget_range[1])
            agent.chosen_items = []

            chosen_items_for_agent = agent.choose_items(self.current_menu_items, max_items_per_agent)
            for item in chosen_items_for_agent:
                all_choices_this_step.append({
                    'agent_id': agent.agent_id,
                    'chosen_item_id': item['id'],
                    'chosen_item_name': item['name'],
                    'item_price_at_purchase': item['price']
                })
        return all_choices_this_step

    def analyze_results(self, choices_data):
        """
        Analyzes the results from a simulation step.

        :param choices_data: Data from run_simulation_step.
        :return: A dictionary with aggregated results (e.g., demand per item, total revenue).
        """
        if not choices_data:
            # Ensure all items from current_menu_items are represented in demand/revenue, even if 0
            demand_per_item = {item['name']: 0 for item in self.current_menu_items}
            revenue_per_item = {item['name']: 0 for item in self.current_menu_items}
            return {
                "total_revenue": 0,
                "total_items_sold": 0,
                "demand_per_item": demand_per_item,
                "revenue_per_item": revenue_per_item
            }

        df = pd.DataFrame(choices_data)
        total_revenue = df['item_price_at_purchase'].sum()
        total_items_sold = len(df)

        demand_counts = df.groupby('chosen_item_name').size()
        revenue_counts = df.groupby('chosen_item_name')['item_price_at_purchase'].sum()

        demand_per_item = {item['name']: demand_counts.get(item['name'], 0) for item in self.current_menu_items}
        revenue_per_item = {item['name']: revenue_counts.get(item['name'], 0) for item in self.current_menu_items}

        return {
            "total_revenue": total_revenue,
            "total_items_sold": total_items_sold,
            "demand_per_item": demand_per_item,
            "revenue_per_item": revenue_per_item
        }

    def run_price_scenario(self, item_id_to_change, new_price, max_items_per_agent=3):
        """
        Runs a simulation with a specific price change and returns the analysis.
        Ensures the main simulation menu (self.current_menu_items) is reset afterwards.
        """
        # Store the state of current_menu_items if it's important to restore it to something other than master.
        # For this method, it's designed to be independent, so starting from master is key.
        self.reset_menu_to_master() # Start from a clean slate based on master_list

        price_updated = self.update_menu_item_price(item_id_to_change, new_price)
        if not price_updated:
            # print(f"Could not run scenario: item ID {item_id_to_change} not found or price {new_price} invalid.")
            self.reset_menu_to_master() # Ensure reset even if update fails
            return None

        choices = self.run_simulation_step(max_items_per_agent)
        analysis = self.analyze_results(choices)

        self.reset_menu_to_master() # Reset menu to master list prices for subsequent independent scenarios

        return analysis

    def run_ped_simulation_set(self, item_id_to_vary, price_percentage_changes, max_items_per_agent=3):
        """
        Runs a set of simulations to gather data for Price Elasticity of Demand (PED) calculation.
        It varies the price of a single item (`item_id_to_vary`) by given percentages
        and records the demand for that item at each price point.

        :param item_id_to_vary: The ID of the item whose price will be varied.
        :param price_percentage_changes: A list of percentage changes to apply to the item's base price
                                         (e.g., [-0.2, -0.1, 0.1, 0.2] for -20%, -10%, +10%, +20%).
        :param max_items_per_agent: Max items an agent can choose in each simulation run.
        :return: A list of dictionaries, each containing {'price': P_i, 'demand': Q_i, 'percentage_change': pc}
                 for the varied item, PLUS the baseline data point {'price': P_base, 'demand': Q_base, 'is_baseline': True}.
                 Returns None if item_id_to_vary is not found.
        """
        base_item_info = next((item for item in self.menu_items_master_list if item['id'] == item_id_to_vary), None)
        if not base_item_info:
            print(f"Error: Item ID {item_id_to_vary} not found in master menu list for PED simulation.")
            return None

        base_price = base_item_info['price']
        item_name = base_item_info['name']
        ped_data_points = []

        # 1. Baseline simulation run
        self.reset_menu_to_master()
        baseline_choices = self.run_simulation_step(max_items_per_agent)
        baseline_analysis = self.analyze_results(baseline_choices)
        base_demand = baseline_analysis['demand_per_item'].get(item_name, 0)
        ped_data_points.append({'price': base_price, 'demand': base_demand, 'is_baseline': True, 'percentage_change': 0.0})

        # 2. Simulations for each price variation
        for percentage_change in price_percentage_changes:
            if percentage_change == 0: # Skip if 0% change is passed, baseline already covers it
                continue
            new_price = round(base_price * (1 + percentage_change), 2) # Round to typical currency precision
            if new_price < 0:
                print(f"Warning: Calculated new price for {item_name} is negative ({new_price}). Skipping this change ({percentage_change*100}%).")
                continue

            self.reset_menu_to_master()
            price_updated_successfully = self.update_menu_item_price(item_id_to_vary, new_price)

            if not price_updated_successfully:
                print(f"Warning: Failed to update price for {item_id_to_vary} to {new_price} in PED run. Skipping.")
                continue

            scenario_choices = self.run_simulation_step(max_items_per_agent)
            scenario_analysis = self.analyze_results(scenario_choices)
            scenario_demand = scenario_analysis['demand_per_item'].get(item_name, 0)
            ped_data_points.append({'price': new_price, 'demand': scenario_demand, 'is_baseline': False, 'percentage_change': percentage_change})

        self.reset_menu_to_master()
        return ped_data_points

    def run_xed_simulation_set(self, target_item_id, affecting_item_id, affecting_item_price_percentage_change, max_items_per_agent=3):
        """
        Runs a pair of simulations to gather data for Cross-Price Elasticity of Demand (XED) calculation.
        It changes the price of `affecting_item_id` and observes the change in demand for `target_item_id`.

        :param target_item_id: The ID of the item whose demand change is being observed.
        :param affecting_item_id: The ID of the item whose price is being changed.
        :param affecting_item_price_percentage_change: The percentage change to apply to affecting_item's price (e.g., 0.1 for +10%).
        :param max_items_per_agent: Max items an agent can choose.
        :return: A dictionary containing baseline and scenario data:
                 {'target_item_name': name, 'target_item_id': id,
                  'affecting_item_name': name, 'affecting_item_id': id,
                  'q_target_base': Q_target_base, 'q_target_scenario': Q_target_scenario,
                  'p_affecting_base': P_affecting_base, 'p_affecting_scenario': P_affecting_scenario,
                  'percentage_change_p_affecting': affecting_item_price_percentage_change }
                 Returns None if items are not found, price change is invalid, or items are the same.
        """
        target_item_master = next((item for item in self.menu_items_master_list if item['id'] == target_item_id), None)
        affecting_item_master = next((item for item in self.menu_items_master_list if item['id'] == affecting_item_id), None)

        if not target_item_master:
            print(f"Error: Target Item ID {target_item_id} not found for XED simulation.")
            return None
        if not affecting_item_master:
            print(f"Error: Affecting Item ID {affecting_item_id} not found for XED simulation.")
            return None
        if target_item_id == affecting_item_id:
            print(f"Error: Target item and affecting item cannot be the same for XED ('{target_item_id}').")
            return None # Use PED for own-price elasticity.

        p_affecting_base = affecting_item_master['price']

        # 1. Baseline simulation
        self.reset_menu_to_master()
        baseline_choices = self.run_simulation_step(max_items_per_agent)
        baseline_analysis = self.analyze_results(baseline_choices)
        q_target_base = baseline_analysis['demand_per_item'].get(target_item_master['name'], 0)

        # 2. Scenario simulation (price of affecting_item_id changes)
        p_affecting_scenario = round(p_affecting_base * (1 + affecting_item_price_percentage_change), 2)
        if p_affecting_scenario < 0:
            print(f"Warning: Calculated new price for affecting item {affecting_item_master['name']} is negative. XED not run.")
            return None

        self.reset_menu_to_master()
        price_updated_successfully = self.update_menu_item_price(affecting_item_id, p_affecting_scenario)
        if not price_updated_successfully:
             print(f"Warning: Failed to update price for affecting item {affecting_item_id} in XED run. XED not run.")
             return None

        scenario_choices = self.run_simulation_step(max_items_per_agent)
        scenario_analysis = self.analyze_results(scenario_choices)
        q_target_scenario = scenario_analysis['demand_per_item'].get(target_item_master['name'], 0)

        self.reset_menu_to_master()

        return {
            'target_item_name': target_item_master['name'],
            'target_item_id': target_item_id,
            'affecting_item_name': affecting_item_master['name'],
            'affecting_item_id': affecting_item_id,
            'q_target_base': q_target_base,
            'q_target_scenario': q_target_scenario,
            'p_affecting_base': p_affecting_base,
            'p_affecting_scenario': p_affecting_scenario,
            'percentage_change_p_affecting': affecting_item_price_percentage_change
        }

if __name__ == '__main__':
    sample_menu = [
        {'id': 'burger_classic', 'name': 'Classic Burger', 'price': 12.0},
        {'id': 'pizza_pepperoni', 'name': 'Pepperoni Pizza', 'price': 15.0},
        {'id': 'salad_caesar', 'name': 'Caesar Salad', 'price': 10.0},
        {'id': 'pasta_carbonara', 'name': 'Carbonara Pasta', 'price': 14.0},
    ]

    print("Initializing Simulation Engine...")
    engine = SimulationEngine(menu_items=sample_menu, num_agents=200)
    print(f"Engine initialized with {len(engine.agents)} agents.")
    print(f"Master Menu (for reference): {engine.menu_items_master_list}")

    print("\n--- Running Baseline Simulation (prices from master list) ---")
    engine.reset_menu_to_master() # Ensure current_menu_items is from master_list
    baseline_choices = engine.run_simulation_step(max_items_per_agent=2)
    baseline_analysis = engine.analyze_results(baseline_choices)
    print("Baseline Analysis:")
    for key, value in baseline_analysis.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")

    print("\n--- Running Price Scenario: Classic Burger price increased to $15 ---")
    burger_price_scenario_analysis = engine.run_price_scenario(
        item_id_to_change='burger_classic',
        new_price=15.0,
        max_items_per_agent=2
    )
    if burger_price_scenario_analysis:
        print("Burger Price Increase Scenario Analysis:")
        for key, value in burger_price_scenario_analysis.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")

    print(f"\nMaster menu prices after scenario (should be unchanged): {[(item['name'], item['price']) for item in engine.menu_items_master_list]}")
    engine.reset_menu_to_master() # Explicitly reset to be sure
    print(f"Current menu prices in engine after scenario (should be reset to master): {[(item['name'], item['price']) for item in engine.current_menu_items]}")


    print("\n--- Running Price Scenario: Caesar Salad price decreased to $8 ---")
    salad_price_scenario_analysis = engine.run_price_scenario(
        item_id_to_change='salad_caesar',
        new_price=8.0,
        max_items_per_agent=2
    )
    if salad_price_scenario_analysis:
        print("Salad Price Decrease Scenario Analysis:")
        for key, value in salad_price_scenario_analysis.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")

    print("\n--- Testing invalid item ID for price update ---")
    invalid_scenario = engine.run_price_scenario("non_existent_id", 10.0)
    if invalid_scenario is None:
        print("Scenario with invalid item ID handled correctly (returned None).")

    print("\n--- Testing invalid price for price update ---")
    invalid_price_scenario = engine.run_price_scenario("burger_classic", -5.0)
    if invalid_price_scenario is None:
         print("Scenario with invalid price handled correctly (returned None).")
    else: # Should be None because update_menu_item_price returns False
        print(f"Scenario with invalid price returned data (unexpected): {invalid_price_scenario}")

    print("\n--- Verifying menu is reset after scenarios ---")
    engine.reset_menu_to_master() # Ensure it's reset
    are_menus_same_after_scenarios = all(
        master_item['price'] == current_item['price']
        for master_item, current_item in zip(engine.menu_items_master_list, engine.current_menu_items)
    )
    print(f"Is current_menu_items reset to master_menu_items after scenarios? {are_menus_same_after_scenarios}")
    assert are_menus_same_after_scenarios, "Menu was not properly reset after running scenarios!"
