import os
import pickle
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

models_dir = "models"

# Load movies and TF-IDF vectorizer (these are created by train_recommender.py)
with open(os.path.join(models_dir, "movies.pkl"), "rb") as f:
    movies = pickle.load(f)

with open(os.path.join(models_dir, "tfidf.pkl"), "rb") as f:
    tfidf = pickle.load(f)

# Ensure clean index
movies = movies.reset_index(drop=True)

# Build a mapping from lowercase title -> index
indices = pd.Series(movies.index, index=movies["title"].str.lower())

# Build TF-IDF matrix for all movies once
tfidf_matrix = tfidf.transform(movies["combined_features"])

def get_recommendations(movie_title: str, n: int = 10):
    """
    Return a DataFrame with n recommended movies (title + genres)
    similar to movie_title.
    """
    movie_title = movie_title.lower()

    if movie_title not in indices:
        return pd.DataFrame(columns=["title", "genres"])

    idx = indices[movie_title]

    # similarity of this movie to all others
    sim_scores = cosine_similarity(tfidf_matrix[idx], tfidf_matrix)[0]

    # pair (movie_index, score) and sort
    sim_scores = list(enumerate(sim_scores))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # skip itself (first one) and take top n
    sim_scores = sim_scores[1 : n + 1]
    movie_indices = [i[0] for i in sim_scores]

    return movies.iloc[movie_indices][["title", "genres"]]
