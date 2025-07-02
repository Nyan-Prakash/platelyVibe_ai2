# plately_ai/menu_psychology/analyzer.py

import re

class MenuPsychologyAnalyzer:
    """
    Analyzes a menu based on common psychological principles and suggests improvements.
    This is a basic implementation. Advanced versions would use NLP for descriptions,
    layout analysis (if menu structure is provided), and more sophisticated heuristics.
    """
    def __init__(self, menu_data):
        """
        Initializes the analyzer with menu data.
        :param menu_data: A list of menu item dictionaries.
                          Expected keys: 'id', 'name', 'price', 'description' (optional), 'category' (optional).
                          Example: [{'id': 'item1', 'name': 'Delicious Burger', 'price': 9.99,
                                     'description': 'Our best seller!', 'category': 'Main Courses'}, ...]
        """
        if not isinstance(menu_data, list):
            raise ValueError("menu_data must be a list of item dictionaries.")
        self.menu_items = menu_data
        self.suggestions = []

    def _check_price_formatting(self):
        """
        Principle: Avoid currency symbols and use charming prices (e.g., .99, .95).
        This check looks for prices that are whole numbers or don't end in .99, .95, etc.
        It also checks for explicit currency symbols in string representations if available.
        (Assuming price is float/int for now).
        """
        for item in self.menu_items:
            price_str = str(item.get('price', ''))
            # Check for .00 or whole numbers, suggesting they could be charmed.
            if price_str.endswith(".00") or ('.' not in price_str and price_str.isdigit()):
                self.suggestions.append({
                    "item_id": item.get('id'),
                    "item_name": item.get('name'),
                    "principle": "Price Formatting (Charming Prices)",
                    "suggestion": f"Consider using a 'charming price' for '{item.get('name')}' (e.g., ending in .99 or .95) instead of ${item.get('price')}. This can make the price seem lower."
                })
            # This would be more effective if prices were strings like "$9.99" to detect symbols.
            # For now, we assume 'price' is a number.

    def _check_decoy_effect_opportunity(self, category_field='category'):
        """
        Principle: Decoy Effect. Introduce a slightly inferior or differently priced third option
                   to make one of the other options look more attractive.
        This is a simplified check: looks for categories with exactly two items where one
        could potentially act as a decoy or a decoy could be introduced.
        A true decoy analysis is complex and needs profitability data.
        """
        if not self.menu_items or not category_field:
            return

        items_by_category = {}
        for item in self.menu_items:
            category = item.get(category_field, 'Uncategorized')
            if category not in items_by_category:
                items_by_category[category] = []
            items_by_category[category].append(item)

        for category, items_in_cat in items_by_category.items():
            if len(items_in_cat) == 2:
                # Sort by price to identify high/low
                sorted_items = sorted(items_in_cat, key=lambda x: x.get('price', 0))
                item1_name = sorted_items[0].get('name')
                item2_name = sorted_items[1].get('name')
                self.suggestions.append({
                    "category": category,
                    "principle": "Decoy Effect (Opportunity)",
                    "suggestion": f"In category '{category}', you have two items: '{item1_name}' and '{item2_name}'. Consider if introducing a third, strategically priced item (a decoy) could boost sales of one of them. For example, a slightly more expensive, less appealing option, or a slightly cheaper, much smaller portion."
                })
            if len(items_in_cat) > 2: # Look for a very high priced item that makes others look cheap
                prices = sorted([item.get('price', 0) for item in items_in_cat if item.get('price') is not None])
                if len(prices) > 2:
                    highest_price = prices[-1]
                    second_highest_price = prices[-2]
                    if highest_price > second_highest_price * 1.5: # Arbitrary threshold for "much higher"
                        expensive_item_name = next(i.get('name') for i in items_in_cat if i.get('price') == highest_price)
                        self.suggestions.append({
                            "category": category,
                            "principle": "Price Anchoring (High Anchor)",
                            "suggestion": f"The item '{expensive_item_name}' in '{category}' is priced significantly higher than others. This can act as a price anchor, making other items seem more reasonably priced. Ensure its description justifies the price."
                        })


    def _check_sensory_rich_descriptions(self, description_field='description', min_length=10):
        """
        Principle: Use vivid, appealing language in descriptions.
        This check looks for items with short or missing descriptions.
        NLP could be used here for sentiment, keyword analysis (e.g., "fresh", "crispy").
        """
        for item in self.menu_items:
            desc = item.get(description_field, "")
            if not desc or len(desc.split()) < min_length:
                self.suggestions.append({
                    "item_id": item.get('id'),
                    "item_name": item.get('name'),
                    "principle": "Sensory Rich Descriptions",
                    "suggestion": f"The description for '{item.get('name')}' is short or missing. Consider using more vivid, sensory language to make it more appealing (e.g., adjectives describing taste, texture, origin)."
                })

    def _check_item_placement_indicators(self, common_terms=None):
        """
        Principle: Highlighted items (e.g., "Chef's Special", "Most Popular") draw attention.
        This checks if any items use common highlighting terms in their name or description.
        This is more of an observation than a direct suggestion unless none are found.
        """
        if common_terms is None:
            common_terms = ['special', 'popular', 'favorite', 'signature', "chef's choice"]

        highlighted_item_found = False
        for item in self.menu_items:
            text_to_check = (item.get('name', '') + " " + item.get('description', '')).lower()
            for term in common_terms:
                if term in text_to_check:
                    self.suggestions.append({
                        "item_id": item.get('id'),
                        "item_name": item.get('name'),
                        "principle": "Item Highlighting (Observation)",
                        "suggestion": f"Item '{item.get('name')}' seems to be highlighted (contains '{term}'). This is good for drawing attention. Ensure it's a profitable or strategic item."
                    })
                    highlighted_item_found = True

        if not highlighted_item_found and self.menu_items:
            self.suggestions.append({
                "principle": "Item Highlighting (Opportunity)",
                "suggestion": "Consider highlighting a profitable or signature item as a 'Chef's Special' or 'Most Popular' to guide customer choices."
            })

    def _check_nostalgia_or_branding_in_names(self, description_field='description'):
        """
        Principle: Names that evoke nostalgia or brand identity can be appealing.
        e.g., "Grandma's Apple Pie", "[Restaurant Name]'s Famous Burger".
        This is a very basic check for possessives or common nostalgic terms.
        """
        nostalgic_terms = ['grandma', 'grandpa', 'mom', 'dad', 'traditional', 'classic', 'old-fashioned', 'original']
        for item in self.menu_items:
            name_plus_desc = (item.get('name', '') + " " + item.get(description_field, '')).lower()
            found_nostalgia = False
            for term in nostalgic_terms:
                if term in name_plus_desc:
                    self.suggestions.append({
                        "item_id": item.get('id'),
                        "item_name": item.get('name'),
                        "principle": "Nostalgic Naming/Description",
                        "suggestion": f"Item '{item.get('name')}' uses nostalgic term '{term}'. This can be appealing. Ensure it aligns with the dish and brand."
                    })
                    found_nostalgia = True
                    break
            if "'" in item.get('name', '') and ('s' in item.get('name', '').lower() or '’' in item.get('name', '')): # e.g., "Chef's" or "Grandma's"
                 if not found_nostalgia: # Avoid duplicate suggestion if already caught by specific terms
                    self.suggestions.append({
                        "item_id": item.get('id'),
                        "item_name": item.get('name'),
                        "principle": "Branded/Possessive Naming",
                        "suggestion": f"Item '{item.get('name')}' uses a possessive name. This can build brand or character (e.g., \"[Restaurant]'s Burger\"). Ensure it's used effectively."
                    })


    def analyze(self):
        """
        Runs all implemented analysis checks.
        :return: A list of suggestion dictionaries.
        """
        self.suggestions = [] # Clear previous suggestions
        if not self.menu_items:
            self.suggestions.append({
                "principle": "General",
                "suggestion": "Menu data is empty. Cannot perform analysis."
            })
            return self.suggestions

        self._check_price_formatting()
        self._check_decoy_effect_opportunity()
        self._check_sensory_rich_descriptions()
        self._check_item_placement_indicators()
        self._check_nostalgia_or_branding_in_names()

        if not self.suggestions and self.menu_items:
            self.suggestions.append({
                "principle": "General",
                "suggestion": "No specific issues found with the current checks. The menu might be well-structured or require more advanced analysis."
            })

        return self.suggestions

if __name__ == '__main__':
    sample_menu = [
        {'id': 'item1', 'name': "Chef's Special Burger", 'price': 12.99,
         'description': "Our signature beef patty with special sauce, lettuce, cheese, pickles, and onions on a sesame seed bun. A true classic!",
         'category': 'Main Courses'},
        {'id': 'item2', 'name': 'Basic Burger', 'price': 10.00, 'description': 'A simple burger.', 'category': 'Main Courses'},
        {'id': 'item3', 'name': 'Deluxe Burger', 'price': 15.00, 'description': 'Double patty, bacon, and all the fixings.', 'category': 'Main Courses'},
        {'id': 'item4', 'name': 'Side Salad', 'price': 5.00, 'description': '', 'category': 'Sides'},
        {'id': 'item5', 'name': 'Fries', 'price': 3.95, 'description': 'Crispy golden fries.', 'category': 'Sides'},
        {'id': 'item6', 'name': "Grandma's Apple Pie", 'price': 6.99, 'description': 'Just like grandma used to make, served warm with a scoop of vanilla ice cream.', 'category': 'Desserts'},
        {'id': 'item7', 'name': 'Chocolate Cake', 'price': 7.00, 'description': 'Rich decadent chocolate cake.', 'category': 'Desserts'},
        {'id': 'item8', 'name': 'Water', 'price': 1.00, 'description': 'Bottled water', 'category': 'Drinks'}
    ]

    analyzer = MenuPsychologyAnalyzer(sample_menu)
    suggestions = analyzer.analyze()

    print("Menu Psychology Suggestions:")
    if suggestions:
        for i, suggestion in enumerate(suggestions):
            print(f"\n--- Suggestion {i+1} ---")
            print(f"  Principle: {suggestion.get('principle')}")
            if suggestion.get('item_name'):
                print(f"  Item: {suggestion.get('item_name')}")
            if suggestion.get('category'):
                print(f"  Category: {suggestion.get('category')}")
            print(f"  Suggestion: {suggestion.get('suggestion')}")
    else:
        print("No suggestions generated.")

    print("\n--- Testing with empty menu ---")
    empty_analyzer = MenuPsychologyAnalyzer([])
    empty_suggestions = empty_analyzer.analyze()
    for suggestion in empty_suggestions:
        print(f"  Suggestion: {suggestion.get('suggestion')}")

    print("\n--- Testing with minimal menu for decoy ---")
    minimal_menu = [
        {'id': 'item_a', 'name': "Small Coffee", 'price': 2.00, 'category': 'Coffee'},
        {'id': 'item_b', 'name': "Large Coffee", 'price': 3.00, 'category': 'Coffee'},
    ]
    minimal_analyzer = MenuPsychologyAnalyzer(minimal_menu)
    minimal_suggestions = minimal_analyzer.analyze()
    for suggestion in minimal_suggestions:
         if "Decoy Effect" in suggestion.get("principle", ""):
            print(f"  Principle: {suggestion.get('principle')}, Suggestion: {suggestion.get('suggestion')}")

    print("\n--- Testing price formatting ---")
    price_menu = [
        {'id': 'item_c', 'name': "Soup", 'price': 5.00, 'category': 'Starters'},
        {'id': 'item_d', 'name': "Steak", 'price': 25, 'category': 'Mains'}, # Integer price
    ]
    price_analyzer = MenuPsychologyAnalyzer(price_menu)
    price_suggestions = price_analyzer.analyze()
    for suggestion in price_suggestions:
         if "Price Formatting" in suggestion.get("principle", ""):
            print(f"  Principle: {suggestion.get('principle')}, Suggestion: {suggestion.get('suggestion')}")
