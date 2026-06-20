# categorizer.py
# ---------------------------------------------------------------------------
# This file decides which CATEGORY an event belongs to based on keywords in
# its title and description. The five categories are:
#   Academic / Sports / Social / Career / Other
#
# How it works: we keep a list of keywords for each category. We lowercase the
# event text, then check which keywords appear. The category with the most
# keyword matches wins. If nothing matches, we fall back to "Other".
# ---------------------------------------------------------------------------

# Keyword dictionaries. Add more words here any time to improve accuracy.
CATEGORY_KEYWORDS = {
    "Academic": [
        "lecture", "seminar", "workshop", "research", "symposium", "thesis",
        "exam", "study", "class", "guest speaker", "colloquium", "tutorial",
        "academic", "professor", "library", "science", "math", "physics",
        "history", "literature", "conference", "panel",
    ],
    "Sports": [
        "game", "match", "tournament", "championship", "basketball", "football",
        "soccer", "volleyball", "tennis", "swim", "track", "fitness", "yoga",
        "gym", "intramural", "athletics", "rugby", "baseball", "marathon",
        "sports", "race", "fitness class",
    ],
    "Social": [
        "party", "mixer", "festival", "concert", "music", "dance", "movie",
        "game night", "trivia", "social", "meetup", "club", "celebration",
        "bbq", "barbecue", "picnic", "open mic", "karaoke", "gala", "fair",
        "welcome", "homecoming", "carnival",
    ],
    "Career": [
        "career", "job", "internship", "resume", "networking", "recruiter",
        "hiring", "employer", "interview", "professional", "industry",
        "startup", "entrepreneur", "linkedin", "career fair", "co-op",
        "alumni", "mentorship", "skills",
    ],
}


def categorize(title, description=""):
    """Return one of: Academic, Sports, Social, Career, Other.

    title       -- the event title (string)
    description -- optional extra text to look at (string)
    """
    # Combine title + description into one lowercase string to search through.
    text = f"{title} {description}".lower()

    # Count how many keywords from each category appear in the text.
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in text:
                score += 1
        scores[category] = score

    # Find the best-scoring category.
    best_category = max(scores, key=scores.get)

    # If even the best category found zero keywords, call it "Other".
    if scores[best_category] == 0:
        return "Other"

    return best_category
