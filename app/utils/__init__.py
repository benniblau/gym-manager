"""Utility functions for the Gym Manager app"""


def get_exercem_url(exercise_name):
    """
    Generate exercem.us URL from exercise name.

    Example: "3/4 Sit-Up" -> "https://exercem.us/exercises/3.4_Sit-Up"

    Rules:
    - Replace "/" with "."
    - Replace spaces with "_"
    """
    if not exercise_name:
        return None

    # Replace "/" with "." and spaces with "_"
    url_name = exercise_name.replace("/", ".").replace(" ", "_")

    return f"https://exercem.us/exercises/{url_name}"
