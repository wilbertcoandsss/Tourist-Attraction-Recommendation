from flask import Flask, request, render_template, jsonify
import requests
from bs4 import BeautifulSoup
import pandas as pd
from model import get_recommendations
import folium
from folium.plugins import MarkerCluster
from googletrans import Translator

app = Flask(__name__, template_folder="../frontend")

# Load dataset once to optimize performance
df = pd.read_csv("dataset/tourism_with_id.csv")

@app.route("/", methods=["GET", "POST"])
def index():    
    rekomendasi = None
    place_name = None
    return render_template("index.html", rekomendasi=rekomendasi, place_name=place_name)

@app.route("/get_recommendations", methods=["POST"])
def get_recommendations_route():
    rekomendasi = None
    place_name = None

    if request.method == "POST":
        place_name = request.form["place_name"]
        top_n = int(request.form["top_n"])
        max_distance = int(request.form["max_distance"])
        rekomendasi = get_recommendations(place_name, top_n, max_distance)
    
    return render_template("index.html", rekomendasi=rekomendasi, place_name=place_name)

@app.route("/get_filters", methods=["GET"])
def get_filters():
    categories = df["Category"].dropna().unique().tolist()
    cities = df["City"].dropna().unique().tolist()
    return jsonify({"categories": categories, "cities": cities})

@app.route("/peta_wisata")
def peta_wisata():
    indonesia_center = [-2.5, 118.0]
    m = folium.Map(location=indonesia_center, zoom_start=5)
    marker_cluster = MarkerCluster().add_to(m)

    df_indonesia = df[(df["Lat"] >= -11) & (df["Lat"] <= 6) & (df["Long"] >= 95) & (df["Long"] <= 141)]

    for idx, row in df_indonesia.iterrows():
        folium.Marker(
            location=[row["Lat"], row["Long"]],
            popup=f"{row['Place_Name']} ({row['Category']})",
            tooltip=row["Place_Name"],
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(marker_cluster)

    return m._repr_html_()

@app.route("/get_recommendations_by_category_city", methods=["POST"])
def get_recommendations_by_category_city():
    rekomendasi = None

    if request.method == "POST":
        category = request.form.get("category", "").strip()
        city = request.form.get("city", "").strip()
        top_n = int(request.form.get("top_n", 5))

        if category and city:
            # Filter data sesuai kategori dan kota, lalu sort berdasarkan rating tertinggi
            rekomendasi = df[(df["Category"] == category) & (df["City"] == city)].sort_values(by="Rating", ascending=False)

            # Ambil top_n tempat terbaik berdasarkan rating
            rekomendasi = rekomendasi.head(top_n)  # Tetap dalam format DataFrame

    return render_template("index.html", rekomendasi=rekomendasi, category=category, city=city)

def get_wikipedia_info(place_name):
    search_url = "https://id.wikipedia.org/api/rest_v1/page/summary/" + place_name.replace(" ", "_")
    print(f"Fetching Wikipedia for: {place_name}")  # Debug
    response = requests.get(search_url)
    print(f"Status Code: {response.status_code}")  # Debug

    if response.status_code != 200:
        return {"description": "Not found on Wikipedia", "image": ""}

    data = response.json()
    print("Wikipedia Response:", data)  # Debug

    description = ". ".join(data["extract"].split(". ")[:2]) + "."
    image = data.get("thumbnail", {}).get("source", "")

    translator = Translator()
    translated_description = translator.translate(description, src='id', dest='en').text
    return {"description": translated_description, "image": image}

@app.route("/get_wikipedia")
def get_wikipedia():
    place = request.args.get("place")
    data = get_wikipedia_info(place)
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
