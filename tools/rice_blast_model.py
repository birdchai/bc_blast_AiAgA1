def rice_blast_risk(
    temp: float,
    humidity: float,
    rainfall: float
) -> dict:

    score = 0

    if 24 <= temp <= 28:
        score += 2
    elif 20 <= temp <= 32:
        score += 1

    if humidity > 90:
        score += 2
    elif humidity > 80:
        score += 1

    if rainfall > 10:
        score += 1

    if score >= 4:
        level = "High"
    elif score >= 2:
        level = "Moderate"
    else:
        level = "Low"

    return {
        "temperature": temp,
        "humidity": humidity,
        "rainfall": rainfall,
        "risk_score": score,
        "risk_level": level
    }