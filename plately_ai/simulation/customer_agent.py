# plately_ai/simulation/customer_agent.py

import random
import numpy as np

class CustomerAgent:
    """
    Represents a customer agent in the demand simulation.
    Each agent has preferences and a budget, and makes purchasing decisions.
    """
    def __init__(self, agent_id, preferences=None, budget_range=(20, 100), price_sensitivity=None):
        """
        Initializes a CustomerAgent.

        :param agent_id: Unique identifier for the agent.
        :param preferences: A dictionary where keys are item_ids and values are preference scores (e.g., 0 to 1).
                            If None, random preferences will be generated.
        :param budget_range: A tuple (min_budget, max_budget) for generating the agent's budget.
        :param price_sensitivity: A float indicating how sensitive the agent is to price changes (e.g., 0 to 1).
                                 Higher values mean more sensitivity. If None, a random value is chosen.
        """
        self.agent_id = agent_id
        self.budget = random.uniform(budget_range[0], budget_range[1])

        if price_sensitivity is None:
            self.price_sensitivity = random.uniform(0.2, 0.8) # Example range
        else:
            self.price_sensitivity = price_sensitivity

        self.preferences = preferences if preferences is not None else {} # Item_id: preference_score
        self.chosen_items = [] # List of item_ids chosen by the agent in a simulation step

    def generate_random_preferences(self, all_item_ids):
        """
        Generates random preference scores for a given list of item IDs if not provided initially.
        """
        if not self.preferences: # Only generate if preferences are empty
            for item_id in all_item_ids:
                self.preferences[item_id] = random.uniform(0.1, 1.0) # Assign a random preference score

    def _calculate_utility(self, item, menu_items):
        """
        Calculates the utility of an item for the agent.
        Utility is a function of preference, price, and price sensitivity.
        A simple model: utility = preference_score / (price ^ price_sensitivity)

        :param item: The menu item object/dictionary being considered. Must have 'id' and 'price'.
        :param menu_items: The full list of menu items (used here for context, could expand for cross-item effects).
        :return: The calculated utility score for the item.
        """
        item_id = item.get('id')
        price = item.get('price')

        if item_id not in self.preferences:
            # Agent has no preference for this item, or it's a new item.
            # Could assign a default low preference or skip.
            return 0

        if price is None or price <= 0: # Avoid division by zero or negative prices
            return self.preferences.get(item_id, 0) # Utility is just preference if price is invalid

        # Basic utility function: preference scaled by price sensitivity
        # Higher price sensitivity means price has a stronger negative impact on utility.
        # Modified: price_sensitivity's impact is scaled by the preference itself.
        # The idea is that for items an agent likes more, they might be more (or differently) sensitive to price changes.
        # Let's scale the exponent: (price_sensitivity * (0.5 + preference_score))
        # preference_score is typically 0.1 to 1.0. So (0.5 + preference_score) is 0.6 to 1.5.
        # This means for highly preferred items, price_sensitivity has a larger effect.
        # For low preference items, the effective price_sensitivity in the exponent is lower.

        preference_value = self.preferences.get(item_id, 0)
        if preference_value == 0: # If truly no preference, utility is 0
            return 0

        effective_price_sensitivity_exponent = self.price_sensitivity * (0.5 + preference_value)

        # Ensure exponent isn't excessively large or small if preference_value was somehow outside expected range
        # For this example, we'll assume preference_value is within a reasonable positive range (e.g. 0.1 to 1.0)
        # as generated. If it can be 0, the initial check handles it.

        utility = preference_value / (price ** effective_price_sensitivity_exponent)

        # Consider other factors: promotions, item popularity (social influence), dietary restrictions etc.
        # For now, this is a simplified model.
        return utility

    def choose_items(self, menu_items, max_items_to_choose=3):
        """
        The agent decides which item(s) to "purchase" based on utility and budget.

        :param menu_items: A list of available menu item objects/dictionaries. Each item should have 'id' and 'price'.
                           Example: [{'id': 'item1', 'price': 10.00, ...}, {'id': 'item2', 'price': 15.00, ...}]
        :param max_items_to_choose: The maximum number of different items an agent can choose.
        :return: A list of chosen item objects.
        """
        self.chosen_items = []
        remaining_budget = self.budget

        if not menu_items:
            return []

        # Ensure preferences are set for all available items
        current_menu_item_ids = [item['id'] for item in menu_items if 'id' in item]
        for item_id in current_menu_item_ids:
            if item_id not in self.preferences:
                self.preferences[item_id] = random.uniform(0.05, 0.5) # Assign neutral/low preference to new/unseen items

        # Calculate utility for all available and affordable items
        potential_choices = []
        for item in menu_items:
            if item.get('price', float('inf')) <= remaining_budget:
                utility = self._calculate_utility(item, menu_items)
                if utility > 0: # Only consider items with positive utility
                    potential_choices.append({'item': item, 'utility': utility})

        # Sort items by utility in descending order
        potential_choices.sort(key=lambda x: x['utility'], reverse=True)

        # Agent chooses items based on highest utility until budget runs out or max_items is reached
        for choice in potential_choices:
            item_to_buy = choice['item']
            item_price = item_to_buy.get('price')

            if len(self.chosen_items) < max_items_to_choose and item_price <= remaining_budget:
                self.chosen_items.append(item_to_buy)
                remaining_budget -= item_price

            if len(self.chosen_items) >= max_items_to_choose or remaining_budget <= 0:
                break

        return self.chosen_items

    def __repr__(self):
        return f"CustomerAgent(id={self.agent_id}, budget={self.budget:.2f}, sensitivity={self.price_sensitivity:.2f})"

if __name__ == '__main__':
    # Example Usage
    all_items_in_restaurant = [
        {'id': 'burger_classic', 'name': 'Classic Burger', 'price': 12.0},
        {'id': 'pizza_pepperoni', 'name': 'Pepperoni Pizza', 'price': 15.0},
        {'id': 'salad_caesar', 'name': 'Caesar Salad', 'price': 10.0},
        {'id': 'pasta_carbonara', 'name': 'Carbonara Pasta', 'price': 14.0},
        {'id': 'steak_ribeye', 'name': 'Ribeye Steak', 'price': 25.0}
    ]
    item_ids = [item['id'] for item in all_items_in_restaurant]

    # Agent with some predefined preferences
    agent1_prefs = {
        'burger_classic': 0.9,
        'pizza_pepperoni': 0.8,
        'salad_caesar': 0.3,
        'pasta_carbonara': 0.6
        # 'steak_ribeye' will get a random preference if encountered
    }
    agent1 = CustomerAgent(agent_id="agent_001", preferences=agent1_prefs, budget_range=(30, 50), price_sensitivity=0.5)
    # agent1.generate_random_preferences(item_ids) # Not needed if prefs are passed, but good for other agents

    # Agent with fully random preferences
    agent2 = CustomerAgent(agent_id="agent_002", budget_range=(15, 40), price_sensitivity=0.7)
    agent2.generate_random_preferences(item_ids) # Generate random preferences for all known items

    print(agent1)
    print(f"Agent 1 Preferences: {agent1.preferences}")

    print(f"\n{agent2}")
    print(f"Agent 2 Preferences: {agent2.preferences}")

    print("\n--- Agent 1 Making Choices ---")
    chosen_by_agent1 = agent1.choose_items(all_items_in_restaurant, max_items_to_choose=2)
    if chosen_by_agent1:
        print(f"Agent 1 chose: {[item['name'] for item in chosen_by_agent1]}")
        print(f"Total cost: ${sum(item['price'] for item in chosen_by_agent1):.2f}, Budget remaining: ${agent1.budget - sum(item['price'] for item in chosen_by_agent1):.2f}")
    else:
        print("Agent 1 chose nothing.")

    print("\n--- Agent 2 Making Choices ---")
    chosen_by_agent2 = agent2.choose_items(all_items_in_restaurant, max_items_to_choose=1)
    if chosen_by_agent2:
        print(f"Agent 2 chose: {[item['name'] for item in chosen_by_agent2]}")
        print(f"Total cost: ${sum(item['price'] for item in chosen_by_agent2):.2f}, Budget remaining: ${agent2.budget - sum(item['price'] for item in chosen_by_agent2):.2f}")
    else:
        print("Agent 2 chose nothing.")

    # Example of changing prices and observing choices
    print("\n--- Agent 1 Making Choices with Updated Prices (Burger more expensive) ---")
    updated_menu_items = [
        {'id': 'burger_classic', 'name': 'Classic Burger', 'price': 18.0}, # Price increased
        {'id': 'pizza_pepperoni', 'name': 'Pepperoni Pizza', 'price': 15.0},
        {'id': 'salad_caesar', 'name': 'Caesar Salad', 'price': 9.0},    # Price decreased
        {'id': 'pasta_carbonara', 'name': 'Carbonara Pasta', 'price': 14.0},
        {'id': 'steak_ribeye', 'name': 'Ribeye Steak', 'price': 25.0}
    ]
    # Agent 1's budget is reset if we re-run choose_items without creating a new agent or explicitly resetting budget.
    # For this test, let's assume the agent is making a new decision on a different day/context.
    # In a real simulation, agent state (like budget) might persist or be reset based on simulation rules.
    # Re-initializing agent1 for a clean choice demonstration with new prices:
    agent1_for_new_prices = CustomerAgent(agent_id="agent_001_rerun", preferences=agent1_prefs, budget_range=(30, 50), price_sensitivity=0.5)
    chosen_by_agent1_updated = agent1_for_new_prices.choose_items(updated_menu_items, max_items_to_choose=2)
    if chosen_by_agent1_updated:
        print(f"Agent 1 (new prices) chose: {[item['name'] for item in chosen_by_agent1_updated]}")
        total_cost = sum(item['price'] for item in chosen_by_agent1_updated)
        print(f"Total cost: ${total_cost:.2f}")
    else:
        print("Agent 1 (new prices) chose nothing.")
