from .recommender import RecommendationEngine

# Global singleton instance
_recommender_instance = None

def get_recommender() -> RecommendationEngine:
    """
    Get the singleton RecommendationEngine instance.
    
    This ensures all requests share the same instance,
    so Thompson Sampling state (including similarity-based initialization)
    is preserved across requests.
    """
    global _recommender_instance
    if _recommender_instance is None:
        _recommender_instance = RecommendationEngine()
    return _recommender_instance