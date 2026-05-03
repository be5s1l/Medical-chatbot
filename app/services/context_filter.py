from typing import Any, Dict, List

class ContextFilter:
    @staticmethod
    def filter_relevant_context(symptoms: List[str], medical_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filters the raw medical context to reduce noise and improve LLM accuracy.
        Currently implements a lightweight heuristic:
        - Removes empty lists and null fields.
        - Cap long lists to prevent prompt explosion.
        (More advanced semantic filtering could be added here in the future).
        """
        if not medical_context:
            return {}

        filtered = {}
        
        # Keep basic demographic info if present
        if medical_context.get("age"):
            filtered["age"] = medical_context["age"]
        if medical_context.get("gender"):
            filtered["gender"] = medical_context["gender"]

        # Helper to filter and limit lists to reduce noise
        def process_list(field_name: str, max_items: int = 10):
            items = medical_context.get(field_name, [])
            if items and isinstance(items, list):
                # Basic cleaning: remove empty strings and limit length
                clean_items = [str(item).strip() for item in items if str(item).strip()]
                if clean_items:
                    filtered[field_name] = clean_items[:max_items]

        process_list("conditions")
        process_list("surgeries")
        process_list("medications")
        process_list("allergies")
        process_list("lab_results", max_items=5) # Labs can be noisy, keep fewer

        return filtered
