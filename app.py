import random
import streamlit as st
from recommender_utils import get_recommendations, movies

st.set_page_config(page_title="Movie Recommender Chat", page_icon="🎬")

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


def pick_seed_movie_from_chat(mood_text: str, genre_text: str, pace_text: str) -> str:
    """
    Pick a 'seed' movie from the movies DataFrame based on free-text chat answers.
    """
    df = movies.copy()
    df = df[df["genres"].notna()]

    target_genres = set()
    target_genres.update(extract_genre_preferences(mood_text, genre_text))
    target_genres.update(extract_pace_preferences(pace_text))

    # If we found no clear genres, allow any
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


def add_assistant_message(content: str):
    st.session_state.chat_history.append({"role": "assistant", "content": content})


def add_user_message(content: str):
    st.session_state.chat_history.append({"role": "user", "content": content})


# ---------- Initialize session state ----------

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.step = 1  # which question we are on
    st.session_state.answers = {"mood": "", "genre": "", "pace": ""}
    st.session_state.last_recs = None

    # Initial greeting + first question
    add_assistant_message(
        "Hey! 🎬 I'm your movie assistant.\n\n"
        "Let's find something to watch. First, tell me:\n\n"
        "**What kind of mood are you in?**"
    )

st.title("🎬 Chat-based Movie Recommender")

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
            "Got it. Now tell me:\n\n"
            "**What kind of movies or genres do you generally enjoy?**\n"
            "_(For example: action, romance, horror, sci-fi, comedy, etc.)_"
        )

    # STEP 2: Genre preference
    elif step == 2:
        st.session_state.answers["genre"] = user_input
        st.session_state.step = 3
        add_assistant_message(
            "Nice taste 😄\n\n"
            "**Do you prefer slow & deep, balanced, or fast & intense movies?**\n"
            "You can describe it in your own words."
        )

    # STEP 3: Pace, then recommend
    elif step == 3:
        st.session_state.answers["pace"] = user_input
        st.session_state.step = 4  # conversation moves to recommendation phase

        mood_text = st.session_state.answers["mood"]
        genre_text = st.session_state.answers["genre"]
        pace_text = st.session_state.answers["pace"]

        # Pick seed movie and get recommendations
        seed_title = pick_seed_movie_from_chat(mood_text, genre_text, pace_text)
        recs = get_recommendations(seed_title, n=6)
        st.session_state.last_recs = recs

        if recs is None or len(recs) == 0:
            add_assistant_message(
                "Hmm, I couldn't find anything that matches.\n\n"
                "Try describing your mood and preferences a bit differently."
            )
        else:
            main_movie = recs.iloc[0]
            add_assistant_message(
                "Thanks! Based on everything you said, here's a movie I think you'll like:\n\n"
                f"### 🎯 **{main_movie['title']}**\n"
                f"*Genres:* {main_movie['genres']}\n\n"
                "If you're **not satisfied**, type **`more`** and I'll suggest a few more options.\n"
                "You can also type **`restart`** to start over."
            )

    # STEP 4: Already recommended once – handle "more" or "restart"
    else:
        text = user_input.strip().lower()

        if text == "restart":
            # Reset conversation
            st.session_state.chat_history = []
            st.session_state.step = 1
            st.session_state.answers = {"mood": "", "genre": "", "pace": ""}
            st.session_state.last_recs = None

            add_assistant_message(
                "No problem, let's start over! 🎬\n\n"
                "**What kind of mood are you in right now?**"
            )

        elif text == "more":
            recs = st.session_state.last_recs
            if recs is None or len(recs) <= 1:
                add_assistant_message(
                    "I don't have more options from that set.\n\n"
                    "You can type **`restart`** to answer the questions again."
                )
            else:
                more_recs = recs.iloc[1:6]
                if more_recs.empty:
                    add_assistant_message(
                        "I’ve already given you everything I found.\n\n"
                        "Try **`restart`** for a new search."
                    )
                else:
                    lines = ["Here are some more movies you might like:\n"]
                    for _, row in more_recs.iterrows():
                        lines.append(f"- **{row['title']}**  \n  *Genres:* {row['genres']}")
                    add_assistant_message("\n".join(lines))
        else:
            # Generic response if user types something else at step 4
            add_assistant_message(
                "If you'd like more options, type **`more`**.\n\n"
                "If you want to start over, type **`restart`**."
            )

    # Force rerun so new messages appear immediately
    st.rerun()
