import nltk
import pandas as pd
import numpy as np
import re
import string
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from geopy.distance import geodesic

nltk.download("stopwords")
nltk.download("punkt")
nltk.download("wordnet")

# Load dataset + replace Pelabuhan Marina to the real location on Ancol
df = pd.read_csv("dataset/tourism_with_id.csv")
df = df[["Place_Name", "Description", "Category", "Rating", "Lat", "Long"]].dropna()
df.loc[df["Place_Name"] == "Pelabuhan Marina", ["Lat", "Long"]] = [-6.11881631002271, 106.82940420928773]

# Fungsi Preprocessing Deskripsi
def preprocess_text(description):
    description = description.lower()
    description = re.sub(r"\d+", "", description)
    description = re.sub(r"[^\w]", " ", description)
    description = re.sub(r"\s+", " ", description).strip()

    tokens = word_tokenize(description)
    tokens = [word for word in tokens if word not in stopwords.words("indonesian")]

    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(word) for word in tokens]

    return " ".join(tokens)

# Fungsi untuk membangun model TF-IDF dan Cosine Similarity
def build_tfid_cosine():
    df["Combined_Features"] = df["Category"].astype(str) + " " + df["Description"]
    df["Combined_Features"] = df["Combined_Features"].apply(preprocess_text)
    tfidf = TfidfVectorizer()
    tfidf_matrix = tfidf.fit_transform(df["Combined_Features"])
    cosine_sim = cosine_similarity(tfidf_matrix)
    return cosine_sim

# Fungsi untuk mendapatkan rekomendasi wisata
def get_recommendations(place_name, top_n=10, max_distance_km=50):
    if place_name not in df["Place_Name"].values:
        return "Tempat tidak ditemukan dalam dataset."

    idx = df[df["Place_Name"] == place_name].index[0]
    place_coord = (df.loc[idx, "Lat"], df.loc[idx, "Long"])

    cosine_similarities = build_tfid_cosine()
    
    sim_scores = list(enumerate(cosine_similarities[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    recommendations = []
    for i, score in sim_scores:
        if i == idx:
            continue

        dest_coord = (df.loc[i, "Lat"], df.loc[i, "Long"])
        distance = geodesic(place_coord, dest_coord).kilometers

        if distance <= max_distance_km:
            weighted_score = score * (df.loc[i, "Rating"] / 5.0)
            recommendations.append((df.loc[i, "Place_Name"], df.loc[i, "Category"], score, weighted_score, df.loc[i, "Rating"], distance))

        if len(recommendations) >= top_n:
            break

    rec_df = pd.DataFrame(recommendations, columns=["Place_Name", "Category", "Score", "Weighted_Score", "Rating", "Distance(KM)"])
    rec_df = rec_df.sort_values(by="Weighted_Score", ascending=False)
    return rec_df