# This file makes 'visual_generator' a Python package.
# It can be empty.

# To make it easier to import the main class from this package,
# you can optionally add:
# from .generator import DishImageGenerator
# __all__ = ['DishImageGenerator']
# For now, keeping it simple and empty. Imports will be `from visual_generator.generator import DishImageGenerator`.
# Let's actually add the import for convenience, as done with other packages.
from .generator import DishImageGenerator

__all__ = ['DishImageGenerator']
