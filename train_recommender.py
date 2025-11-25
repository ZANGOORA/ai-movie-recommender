import pandas as pd
import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer

# 1. Load data
movies_path = os.path.join("data", "movies.csv")
movies = pd.read_csv(movies_path)

# 2. Basic cleaning
movies['genres'] = movies['genres'].fillna('')
movies['clean_genres'] = movies['genres'].str.replace('|', ' ', regex=False)

# Remove year from title (optional)
movies['clean_title'] = movies['title'].str.replace(r'\(\d{4}\)', '', regex=True).str.lower()

# Combine title + genres into one text input
movies['combined_features'] = movies['clean_title'] + ' ' + movies['clean_genres']

# 3. Create TF-IDF vectorizer
tfidf = TfidfVectorizer(stop_words='english')

# 4. Fit on movie features
tfidf_matrix = tfidf.fit_transform(movies['combined_features'])

# 5. Save only the movies + the vectorizer
os.makedirs("models", exist_ok=True)
