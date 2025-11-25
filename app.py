import streamlit as st
from recommender_utils import get_recommendations, movies

st.set_page_config(page_title="Movie Recommender", page_icon="🎬")

st.title("🎬 Movie Recommendation System")
st.write("Select a movie and get similar recommendations")

movie_list = movies['title'].tolist()

selected_movie = st.selectbox("Choose a movie:", movie_list)

num_rec = st.slider("Number of recommendations:", 5, 20, 10)

if st.button("Recommend"):
    results = get_recommendations(selected_movie, num_rec)

    if len(results) == 0:
        st.write("No results found.")
    else:
        st.subheader("Recommended Movies:")
        for _, row in results.iterrows():
            st.write(f"- **{row['title']}** ({row['genres']})")
