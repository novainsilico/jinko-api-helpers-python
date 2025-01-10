def check_dependencies(dependencies):
    """
    Check if the required dependencies are installed.

    Args:
        dependencies (list of str): A list of module names to check.

    Raises:
        ImportError: If any of the dependencies are missing.
    """
    missing = []
    for dep in dependencies:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)

    if missing:
        raise ImportError(
            f"The following dependencies are required but not installed: {', '.join(missing)}. "
            "Install them with the appropriate Poetry extras, e.g., "
            f"'poetry install --extras jinko-stats-deps' (or include all needed extras)."
        )
