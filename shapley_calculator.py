import itertools
import numpy as np
from typing import Dict, List, Tuple, Set, Any

class ShapleyCalculator:
    """
    A class to calculate Shapley values for NFT bundle purchases.
    
    The Shapley value provides a fair way to distribute the total value (cost)
    of a bundle among buyers based on their marginal contributions.
    """
    
    def __init__(self, bundle_price: float):
        """
        Initialize the calculator with the total bundle price.
        
        Args:
            bundle_price: The total price of the bundle
        """
        self.bundle_price = bundle_price
        
    def calculate_values(self, 
                         buyers_interests: Dict[str, List[int]], 
                         item_values: Dict[int, float] = None) -> Dict[str, float]:
        """
        Calculate Shapley values for each buyer based on their interests.
        
        Args:
            buyers_interests: Dictionary mapping buyer addresses to lists of item IDs they're interested in
            item_values: Optional dictionary mapping item IDs to their individual values
                        (if not provided, items are assumed to have equal value)
                        
        Returns:
            Dictionary mapping buyer addresses to their Shapley values (amount to pay)
        """
        buyers = list(buyers_interests.keys())
        n = len(buyers)
        
        if n == 0:
            return {}
        
        # If item values are not provided, assume equal distribution
        if item_values is None:
            unique_items = set()
            for items in buyers_interests.values():
                unique_items.update(items)
            
            # Equal value for each item
            item_values = {item_id: self.bundle_price / len(unique_items) for item_id in unique_items}
        
        shapley_values = {buyer: 0.0 for buyer in buyers}
        
        # Calculate all possible permutations of buyers
        permutations = list(itertools.permutations(buyers))
        
        for perm in permutations:
            current_items = set()
            
            for buyer in perm:
                # Calculate marginal contribution
                prev_value = sum(item_values.get(item, 0) for item in current_items)
                
                # Add this buyer's items
                for item in buyers_interests[buyer]:
                    current_items.add(item)
                
                new_value = sum(item_values.get(item, 0) for item in current_items)
                marginal_contribution = new_value - prev_value
                
                # Add to Shapley value
                shapley_values[buyer] += marginal_contribution / len(permutations)
        
        # Normalize to ensure the sum equals the bundle price
        total = sum(shapley_values.values())
        if total > 0:  # Avoid division by zero
            for buyer in shapley_values:
                shapley_values[buyer] = (shapley_values[buyer] / total) * self.bundle_price
        
        return shapley_values
    
    def calculate_values_simplified(self, 
                                   buyers_interests: Dict[str, List[int]]) -> Dict[str, float]:
        """
        A simplified calculation of Shapley values based on the number of items each buyer wants.
        This is a faster approximation for when exact Shapley values are not needed.
        
        Args:
            buyers_interests: Dictionary mapping buyer addresses to lists of item IDs they're interested in
            
        Returns:
            Dictionary mapping buyer addresses to their Shapley values (amount to pay)
        """
        # Count how many buyers are interested in each item
        item_interest_count = {}
        for buyer, items in buyers_interests.items():
            for item in items:
                if item not in item_interest_count:
                    item_interest_count[item] = 0
                item_interest_count[item] += 1
        
        # Calculate value per item based on interest
        item_values = {}
        for item, count in item_interest_count.items():
            item_values[item] = 1.0 / count if count > 0 else 0
            
        # Calculate each buyer's share
        buyer_values = {buyer: 0.0 for buyer in buyers_interests}
        for buyer, items in buyers_interests.items():
            for item in items:
                buyer_values[buyer] += item_values[item]
        
        # Normalize to the bundle price
        total_value = sum(buyer_values.values())
        if total_value > 0:
            for buyer in buyer_values:
                buyer_values[buyer] = (buyer_values[buyer] / total_value) * self.bundle_price
                
        return buyer_values


# Example usage
if __name__ == "__main__":
    # Example with 3 buyers and 3 items
    bundle_price = 100.0
    
    # Buyer interests (which items each buyer wants)
    buyers_interests = {
        "buyer1": [1, 2],      # Buyer 1 wants items 1 and 2
        "buyer2": [2, 3],      # Buyer 2 wants items 2 and 3
        "buyer3": [1, 3]       # Buyer 3 wants items 1 and 3
    }
    
    # Calculate Shapley values
    calculator = ShapleyCalculator(bundle_price)
    shapley_values = calculator.calculate_values(buyers_interests)
    
    print("Shapley Values:")
    for buyer, value in shapley_values.items():
        print(f"{buyer}: ${value:.2f}")
    
    # Simplified calculation
    simplified_values = calculator.calculate_values_simplified(buyers_interests)
    
    print("\nSimplified Values:")
    for buyer, value in simplified_values.items():
        print(f"{buyer}: ${value:.2f}") 