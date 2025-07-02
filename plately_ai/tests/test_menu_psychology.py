# plately_ai/tests/test_menu_psychology.py

import unittest
from plately_ai.menu_psychology.analyzer import MenuPsychologyAnalyzer

class TestMenuPsychologyAnalyzer(unittest.TestCase):
    def setUp(self):
        self.sample_menu_alpha = [
            {'id': 'item1', 'name': "Chef's Special Burger", 'price': 12.99,
             'description': "Our signature beef patty with special sauce, lettuce, cheese, pickles, and onions on a sesame seed bun. A true classic!",
             'category': 'Main Courses'},
            {'id': 'item2', 'name': 'Basic Burger', 'price': 10.00, 'description': 'A simple burger.', 'category': 'Main Courses'},
            {'id': 'item3', 'name': 'Deluxe Burger Feast', 'price': 25.00, 'description': 'Double patty, bacon, imported cheese, and truffle fries.', 'category': 'Main Courses'}, # High anchor
            {'id': 'item4', 'name': 'Side Salad', 'price': 5.00, 'description': '', 'category': 'Sides'}, # Short description
            {'id': 'item5', 'name': 'Fries', 'price': 3.95, 'description': 'Crispy golden fries.', 'category': 'Sides'},
            {'id': 'item6', 'name': "Grandma's Apple Pie", 'price': 6.99, 'description': 'Just like grandma used to make, served warm.', 'category': 'Desserts'},
            {'id': 'item7', 'name': 'Chocolate Cake', 'price': 7.00, 'description': 'Rich decadent chocolate cake.', 'category': 'Desserts'},
        ]

    def find_suggestion(self, suggestions, principle, item_name=None, category_name=None):
        """Helper to find a specific suggestion."""
        for sug in suggestions:
            if sug.get('principle') == principle:
                if item_name and sug.get('item_name') != item_name:
                    continue
                if category_name and sug.get('category') != category_name:
                    continue
                return sug
        return None

    def test_empty_menu(self):
        analyzer = MenuPsychologyAnalyzer([])
        suggestions = analyzer.analyze()
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]['suggestion'], "Menu data is empty. Cannot perform analysis.")

    def test_price_formatting_charming_prices(self):
        analyzer = MenuPsychologyAnalyzer(self.sample_menu_alpha)
        suggestions = analyzer.analyze()

        # Basic Burger at 10.00
        sug_item2 = self.find_suggestion(suggestions, "Price Formatting (Charming Prices)", item_name='Basic Burger')
        self.assertIsNotNone(sug_item2)
        self.assertIn("ending in .99 or .95", sug_item2['suggestion'])

        # Side Salad at 5.00
        sug_item4 = self.find_suggestion(suggestions, "Price Formatting (Charming Prices)", item_name='Side Salad')
        self.assertIsNotNone(sug_item4)

        # Chocolate Cake at 7.00
        sug_item7 = self.find_suggestion(suggestions, "Price Formatting (Charming Prices)", item_name='Chocolate Cake')
        self.assertIsNotNone(sug_item7)

        # Prices like 12.99 or 3.95 should not trigger this
        sug_item1 = self.find_suggestion(suggestions, "Price Formatting (Charming Prices)", item_name="Chef's Special Burger")
        self.assertIsNone(sug_item1)
        sug_item5 = self.find_suggestion(suggestions, "Price Formatting (Charming Prices)", item_name="Fries")
        self.assertIsNone(sug_item5)


    def test_decoy_effect_and_anchoring(self):
        menu_for_decoy = [
            {'id': 'd1', 'name': 'Small Popcorn', 'price': 5.00, 'category': 'Snacks'},
            {'id': 'd2', 'name': 'Large Popcorn', 'price': 8.00, 'category': 'Snacks'},
        ]
        analyzer_decoy = MenuPsychologyAnalyzer(menu_for_decoy)
        suggestions_decoy = analyzer_decoy.analyze()
        sug_decoy = self.find_suggestion(suggestions_decoy, "Decoy Effect (Opportunity)", category_name='Snacks')
        self.assertIsNotNone(sug_decoy)
        self.assertIn("Consider if introducing a third, strategically priced item", sug_decoy['suggestion'])

        # Test high anchor from sample_menu_alpha
        analyzer_anchor = MenuPsychologyAnalyzer(self.sample_menu_alpha)
        suggestions_anchor = analyzer_anchor.analyze()
        sug_anchor = self.find_suggestion(suggestions_anchor, "Price Anchoring (High Anchor)", category_name='Main Courses')
        self.assertIsNotNone(sug_anchor)
        self.assertIn("'Deluxe Burger Feast'", sug_anchor['suggestion'])
        self.assertIn("priced significantly higher", sug_anchor['suggestion'])


    def test_sensory_rich_descriptions(self):
        analyzer = MenuPsychologyAnalyzer(self.sample_menu_alpha)
        suggestions = analyzer.analyze()

        # Side Salad has empty description
        sug_item4 = self.find_suggestion(suggestions, "Sensory Rich Descriptions", item_name='Side Salad')
        self.assertIsNotNone(sug_item4)
        self.assertIn("description for 'Side Salad' is short or missing", sug_item4['suggestion'])

        # Basic Burger has short description "A simple burger." (3 words)
        sug_item2 = self.find_suggestion(suggestions, "Sensory Rich Descriptions", item_name='Basic Burger')
        self.assertIsNotNone(sug_item2)
        self.assertIn("description for 'Basic Burger' is short or missing", sug_item2['suggestion'])

        # Chef's Special Burger has a long description, should not be flagged (min_length=10 default)
        sug_item1 = self.find_suggestion(suggestions, "Sensory Rich Descriptions", item_name="Chef's Special Burger")
        self.assertIsNone(sug_item1)

    def test_item_highlighting(self):
        analyzer = MenuPsychologyAnalyzer(self.sample_menu_alpha)
        suggestions = analyzer.analyze()

        # Chef's Special Burger
        sug_highlight = self.find_suggestion(suggestions, "Item Highlighting (Observation)", item_name="Chef's Special Burger")
        self.assertIsNotNone(sug_highlight)
        self.assertIn("seems to be highlighted (contains 'special')", sug_highlight['suggestion'])

        menu_no_highlight = [{'id': 'i1', 'name': 'Plain Dish', 'price': 10.00, 'description': 'A plain dish.'}]
        analyzer_no_highlight = MenuPsychologyAnalyzer(menu_no_highlight)
        suggestions_no_highlight = analyzer_no_highlight.analyze()
        sug_opportunity = self.find_suggestion(suggestions_no_highlight, "Item Highlighting (Opportunity)")
        self.assertIsNotNone(sug_opportunity)
        self.assertIn("Consider highlighting a profitable or signature item", sug_opportunity['suggestion'])


    def test_nostalgia_or_branding_in_names(self):
        analyzer = MenuPsychologyAnalyzer(self.sample_menu_alpha)
        suggestions = analyzer.analyze()

        # Grandma's Apple Pie
        sug_nostalgia = self.find_suggestion(suggestions, "Nostalgic Naming/Description", item_name="Grandma's Apple Pie")
        self.assertIsNotNone(sug_nostalgia)
        self.assertIn("uses nostalgic term 'grandma'", sug_nostalgia['suggestion'])

        # Chef's Special Burger (possessive)
        sug_possessive = self.find_suggestion(suggestions, "Branded/Possessive Naming", item_name="Chef's Special Burger")
        self.assertIsNotNone(sug_possessive)
        self.assertIn("uses a possessive name", sug_possessive['suggestion'])

    def test_valid_menu_no_issues_found_by_basic_checks(self):
        # A menu that might not trigger basic suggestions easily
        perfect_menu = [
            {'id': 'p1', 'name': "Our Famous Chicken Delight", 'price': 14.95,
             'description': "Tender grilled chicken breast marinated in herbs, served with roasted seasonal vegetables and a light lemon sauce. A customer favorite!",
             'category': 'Mains'},
            {'id': 'p2', 'name': "The Ultimate Veggie Wrap", 'price': 11.99,
             'description': "A warm tortilla packed with fresh hummus, avocado, crisp lettuce, tomatoes, cucumbers, and bell peppers. Healthy and satisfying!",
             'category': 'Mains'},
             {'id': 'p3', 'name': "The Extravaganza Platter", 'price': 30.99,
             'description': "A huge platter for sharing, with various meats, cheeses, and breads.",
             'category': 'Starters'}, # Anchor for starters
        ]
        analyzer = MenuPsychologyAnalyzer(perfect_menu)
        suggestions = analyzer.analyze()

        # It might still find "Famous" or "Ultimate" for highlighting, "Our" for branding
        # Let's check if the "no specific issues" suggestion is NOT there if other suggestions exist
        no_issues_sug = self.find_suggestion(suggestions, "General", item_name=None)

        has_other_suggestions = any(sug['principle'] != "General" for sug in suggestions)

        if has_other_suggestions:
            self.assertIsNone(no_issues_sug) # Should not have the "no specific issues" if others are found
        else:
            # This case is unlikely with the current perfect_menu as it has highlighting/branding
            self.assertIsNotNone(no_issues_sug)
            self.assertIn("No specific issues found", no_issues_sug['suggestion'])


if __name__ == '__main__':
    unittest.main()
