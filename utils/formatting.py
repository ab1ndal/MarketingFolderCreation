def format_number(num_str):
    if num_str is None:
        return None

    cleaned = str(num_str).replace(",", "").strip()

    try:
        return f"{float(cleaned):,.2f}"
    except ValueError:
        return ""