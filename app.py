import random
import re
import streamlit as st
import pandas as pd
from recommender_utils import get_recommendations, movies

st.set_page_config(
    page_title="CineMatch – Movie Recommender",
    page_icon="🎬",
    layout="wide",
)

# ---------- Custom CSS for a more cinematic look ----------
st.markdown(
    """
    <style>
    /* Page background */
    .stApp {
        background: radial-gradient(circle at top, #1f2933 0, #0b1015 45%, #05070a 100%);
        color: #f9fafb;
    }

    /* Main title */
    .main-title {
        font-size: 2.4rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .subtitle {
        font-size: 0.95rem;
        color: #cbd5f5;
        margin-bottom: 1.5rem;
    }

    /* Chat messages */
    .stChatMessage {
        border-radius: 12px;
        padding: 0.25rem 0.5rem;
    }

    /* Assistant bubble */
    .stChatMessage:nth-child(odd) {
        background-color: rgba(31, 41, 55, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.4);
    }

    /* User bubble */
    .stChatMessage:nth-child(even) {
        background-color: rgba(15, 23, 42, 0.9);
        border: 1px solid rgba(75, 85, 99, 0.7);
    }

    /* Command chips */
    .chip {
        display: inline-block;
        padding: 4px 10px;
        margin: 2px 4px 2px 0;
        border-radius: 999px;
        border: 1px solid #64748b;
        font-size: 0.8rem;
        color: #e5e7eb;
        background: rgba(15, 23, 42, 0.9);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Helper functions ----------

def extract_genre_preferences(mood_text: str, genre_text: str) -> set:
    """
    Very simple keyword-based genre extraction from free-text answers.
    """
    text = (mood_text + " " + genre_text).lower()
    genre_map = {
        "action": "Action",
        "adventure": "Adventure",
        "animation": "Animation",
        "cartoon": "Animation",
        "comedy": "Comedy",
        "funny": "Comedy",
        "crime": "Crime",
        "drama": "Drama",
        "emotional": "Drama",
        "fantasy": "Fantasy",
        "horror": "Horror",
        "scary": "Horror",
        "mystery": "Mystery",
        "romance": "Romance",
        "romantic": "Romance",
        "love": "Romance",
        "sci-fi": "Sci-Fi",
        "science fiction": "Sci-Fi",
        "thriller": "Thriller",
        "suspense": "Thriller",
        "family": "Children",
        "kids": "Children",
    }

    target_genres = set()
    for keyword, genre in genre_map.items():
        if keyword in text:
            target_genres.add(genre)

    return target_genres


def extract_pace_preferences(pace_text: str) -> set:
    """
    Infer additional genres based on pace preference.
    """
    t = pace_text.lower()
    target_genres = set()

    if any(word in t for word in ["slow", "calm", "relax", "deep", "thoughtful"]):
        target_genres.update(["Drama", "Romance"])
    elif any(word in t for word in ["fast", "intense", "thrill", "edge", "exciting"]):
        target_genres.update(["Action", "Thriller", "Adventure", "Sci-Fi"])
    else:
        # Balanced / default
        target_genres.update(["Drama", "Comedy"])

    return target_genres


def parse_period(period_text: str):
    """
    Map free-text era preference into a label: 'recent', '2000s', '90s', 'classic', or None.
    """
    t = period_text.lower()
    if any(w in t for w in ["recent", "new", "latest", "modern", "after 2010"]):
        return "recent"
    if any(w in t for w in ["2000", "2000s"]):
        return "2000s"
    if any(w in t for w in ["90s", "1990"]):
        return "90s"
    if any(w in t for w in ["80s", "70s", "60s", "old", "classic", "older"]):
        return "classic"
    return None


def parse_tone(tone_text: str):
    """
    Map free-text tone preference into 'light', 'dark', or None.
    """
    t = tone_text.lower()
    if any(w in t for w in ["light", "family", "kids", "wholesome", "feel good", "happy"]):
        return "light"
    if any(w in t for w in ["dark", "serious", "intense", "violent", "gritty", "heavy"]):
        return "dark"
    return None


def find_liked_movies(liked_text: str):
    """
    Try to match user-typed liked movies to titles in the dataset.
    Returns list of matching titles.
    """
    liked_text = liked_text.strip()
    if not liked_text or liked_text.lower() == "skip":
        return []

    parts = [p.strip().lower() for p in liked_text.split(",") if p.strip()]
    if not parts:
        return []

    titles_lower = movies["title"].str.lower()
    matched_titles = []

    for name in parts:
        # Find titles that contain the given text
        matches = movies[titles_lower.str.contains(re.escape(name))]
        if not matches.empty:
            # Add one or a few unique titles
            for t in matches["title"].tolist():
                if t not in matched_titles:
                    matched_titles.append(t)

    return matched_titles


def pick_seed_movie_from_chat(mood_text: str, genre_text: str, pace_text: str, liked_text: str) -> str:
    """
    Pick a 'seed' movie from the movies DataFrame based on chat answers.
    If the user gave known liked movies, use one of them directly as seed.
    Otherwise, use inferred genres + pace to pick a candidate.
    """
    liked_matches = find_liked_movies(liked_text)
    if liked_matches:
        # Use one of the user's liked movies as the base taste
        return random.choice(liked_matches)

    df = movies.copy()
    df = df[df["genres"].notna()]

    target_genres = set()
    target_genres.update(extract_genre_preferences(mood_text, genre_text))
    target_genres.update(extract_pace_preferences(pace_text))

    if not target_genres:
        candidates = df
    else:
        def match_any(genres_str: str) -> bool:
            return any(g in genres_str for g in target_genres)

        candidates = df[df["genres"].apply(match_any)]
        if candidates.empty:
            candidates = df

    seed_row = candidates.sample(1, random_state=random.randint(0, 999999)).iloc[0]
    return seed_row["title"]


def filter_recommendations_by_period_and_tone(recs, period_text: str, tone_text: str):
    """
    Filter recommended movies by era and tone preferences.
    """
    if recs is None or recs.empty:
        return recs

    recs = recs.copy()

    # Extract year from title (e.g. "Toy Story (1995)")
    years = recs["title"].str.extract(r"\((\d{4})\)", expand=False)
    years = pd.to_numeric(years, errors="coerce")
    recs["year"] = years

    period_label = parse_period(period_text)
    tone_label = parse_tone(tone_text)

    # Filter by period
    if period_label == "recent":
        recs = recs[recs["year"] >= 2010]
    elif period_label == "2000s":
        recs = recs[(recs["year"] >= 2000) & (recs["year"] < 2010)]
    elif period_label == "90s":
        recs = recs[(recs["year"] >= 1990) & (recs["year"] < 2000)]
    elif period_label == "classic":
        recs = recs[recs["year"] < 1990]

    # Filter by tone
    if tone_label == "light":
        # family-friendly / feel-good
        light_genres = ["Animation", "Children", "Comedy", "Family"]
        recs = recs[recs["genres"].apply(lambda g: any(lg in g for lg in light_genres))]
    elif tone_label == "dark":
        dark_genres = ["Drama", "Thriller", "Horror", "Crime"]
        recs = recs[recs["genres"].apply(lambda g: any(dg in g for dg in dark_genres))]

    # If filters removed everything, fall back to original recs (without filters)
    if recs.empty:
        return recs  # caller can decide fallback

    return recs


def add_assistant_message(content: str):
    st.session_state.chat_history.append({"role": "assistant", "content": content})


def add_user_message(content: str):
    st.session_state.chat_history.append({"role": "user", "content": content})


# ---------- Initialize session state ----------

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    # Conversation steps:
    # 1: mood
    # 2: genres
    # 3: pace
    # 4: liked movies
    # 5: era
    # 6: tone -> then recommend
    # 7+: post-recommendation phase
    st.session_state.step = 1
    st.session_state.answers = {
        "mood": "",
        "genre": "",
        "pace": "",
        "liked": "",
        "period": "",
        "tone": "",
    }
    st.session_state.last_recs = None

    # Initial greeting + first question
    add_assistant_message(
        "Hey! 🎬 I'm your movie assistant.\n\n"
        "Let's find something you'd actually want to watch.\n\n"
        "**1️⃣ What kind of mood are you in right now?**"
    )

# ---------- Top layout (header + sidebar) ----------

# Sidebar: instructions & commands
with st.sidebar:
    st.markdown("## 🎥 CineMatch")
    st.markdown("Your AI-powered movie taste assistant.")
    st.markdown("---")
    st.markdown("### How to use")
    st.markdown(
        """
        1. Answer the questions like a chat  
        2. I’ll recommend one movie  
        3. Type **`more`** for more options  
        4. Type **`restart`** to start over  
        """
    )
    st.markdown("---")
    st.markdown("### Quick commands")
    st.markdown(
        """
        <span class="chip">more</span>
        <span class="chip">restart</span>
        """,
        unsafe_allow_html=True,
    )

# Main header
header_col1, header_col2 = st.columns([3, 1])

with header_col1:
    st.markdown('<div class="main-title">🎬 CineMatch – Chat Movie Recommender</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Tell me your mood, taste, vibe & favourite films – '
        'I’ll try to pick something you\'ll actually want to watch.</div>',
        unsafe_allow_html=True,
    )

with header_col2:
    st.metric(label="Movies in catalogue", value=f"{len(movies):,}")

# Show current interpreted taste (optional, but nice)
with st.expander("🎚 Current taste profile (as I understood it)", expanded=False):
    a = st.session_state.answers
    st.markdown(
        f"""
        - **Mood:** `{a.get("mood", "") or "-"}`
        - **Genres you mentioned:** `{a.get("genre", "") or "-"}`
        - **Pace preference:** `{a.get("pace", "") or "-"}`
        - **Movies you liked:** `{a.get("liked", "") or "-"}`
        - **Preferred era:** `{a.get("period", "") or "-"}`
        - **Tone:** `{a.get("tone", "") or "-"}`
        """
    )

# ---------- Display chat history ----------

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------- Chat input ----------

user_input = st.chat_input("Type your reply here...")

if user_input:
    # Store user message
    add_user_message(user_input)
    step = st.session_state.step

    # STEP 1: Mood
    if step == 1:
        st.session_state.answers["mood"] = user_input
        st.session_state.step = 2
        add_assistant_message(
            "Nice, got it. 😊\n\n"
            "**2️⃣ What kind of movies or genres do you generally enjoy?**\n"
            "_(e.g. action, romance, horror, sci-fi, comedy, etc.)_"
        )

    # STEP 2: Genre preference
    elif step == 2:
        st.session_state.answers["genre"] = user_input
        st.session_state.step = 3
        add_assistant_message(
            "Good taste. 🎭\n\n"
            "**3️⃣ Do you prefer slow & deep, balanced, or fast & intense movies?**\n"
            "You can describe it in your own words."
        )

    # STEP 3: Pace
    elif step == 3:
        st.session_state.answers["pace"] = user_input
        st.session_state.step = 4
        add_assistant_message(
            "Gotcha.\n\n"
            "**4️⃣ Name 2–3 movies you liked recently.**\n"
            "_(Comma separated, e.g. `Inception, Interstellar, Shutter Island` — or type `skip` if you want.)_"
        )

    # STEP 4: Liked movies
    elif step == 4:
        st.session_state.answers["liked"] = user_input
        st.session_state.step = 5
        add_assistant_message(
            "Nice picks. 🎞️\n\n"
            "**5️⃣ Do you prefer something recent, 2000s, 90s, or more of a classic?**\n"
            "You can say things like `recent`, `90s`, `older classic`, etc."
        )

    # STEP 5: Era
    elif step == 5:
        st.session_state.answers["period"] = user_input
        st.session_state.step = 6
        add_assistant_message(
            "Cool.\n\n"
            "**6️⃣ Do you want something light/family-friendly, or dark/serious/intense?**\n"
            "Again, feel free to describe it in your own words."
        )

    # STEP 6: Tone, then recommend
    elif step == 6:
        st.session_state.answers["tone"] = user_input
        st.session_state.step = 7  # post-recommendation phase

        mood_text = st.session_state.answers["mood"]
        genre_text = st.session_state.answers["genre"]
        pace_text = st.session_state.answers["pace"]
        liked_text = st.session_state.answers["liked"]
        period_text = st.session_state.answers["period"]
        tone_text = st.session_state.answers["tone"]

        # 1) Pick a seed movie from preferences
        seed_title = pick_seed_movie_from_chat(mood_text, genre_text, pace_text, liked_text)

        # 2) Get a larger pool of recommendations
        raw_recs = get_recommendations(seed_title, n=25)

        # 3) Filter them based on era and tone
        filtered_recs = filter_recommendations_by_period_and_tone(raw_recs, period_text, tone_text)

        # If filters removed everything, fall back to raw recommendations
        if filtered_recs is None or filtered_recs.empty:
            recs = raw_recs.iloc[:6] if raw_recs is not None else raw_recs
        else:
            recs = filtered_recs.iloc[:6]

        st.session_state.last_recs = recs

        if recs is None or len(recs) == 0:
            add_assistant_message(
                "Hmm, I couldn't find anything that matches all of that.\n\n"
                "Try describing your mood and preferences a bit differently, or type **`restart`** to start over."
            )
        else:
            main_movie = recs.iloc[0]
            add_assistant_message(
                "Thanks, that gives me a pretty clear idea of your taste. 🎯\n\n"
                "Based on everything you said, here’s a movie I strongly recommend:\n\n"
                f"### 🎬 **{main_movie['title']}**\n"
                f"*Genres:* {main_movie['genres']}\n\n"
                "If you're **not satisfied**, type **`more`** and I'll suggest a few more options.\n"
                "You can also type **`restart`** to try a completely different vibe."
            )

    # STEP 7+: Already recommended once – handle "more" or "restart"
    else:
        text = user_input.strip().lower()

        if text == "restart":
            # Reset conversation
            st.session_state.chat_history = []
            st.session_state.step = 1
            st.session_state.answers = {
                "mood": "",
                "genre": "",
                "pace": "",
                "liked": "",
                "period": "",
                "tone": "",
            }
            st.session_state.last_recs = None

            add_assistant_message(
                "No problem, let's start over! 🎬\n\n"
                "**1️⃣ What kind of mood are you in right now?**"
            )

        elif text == "more":
            recs = st.session_state.last_recs
            if recs is None or len(recs) <= 1:
                add_assistant_message(
                    "I don't have more options from that set.\n\n"
                    "You can type **`restart`** to answer the questions again and refine your taste."
                )
            else:
                more_recs = recs.iloc[1:6]
                if more_recs.empty:
                    add_assistant_message(
                        "I’ve already given you everything I found for this taste profile.\n\n"
                        "Try **`restart`** for a new search."
                    )
                else:
                    lines = ["Here are some more movies I think you'd enjoy:\n"]
                    for _, row in more_recs.iterrows():
                        lines.append(f"- **{row['title']}**  \n  *Genres:* {row['genres']}")
                    add_assistant_message("\n".join(lines))
        else:
            # Generic response if user types something else at step 7+
            add_assistant_message(
                "If you'd like more options, type **`more`**.\n\n"
                "If you want to start over with new preferences, type **`restart`**."
            )

    # Rerun so new messages appear immediately
    st.rerun()
