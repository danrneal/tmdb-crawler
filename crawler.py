import argparse
import collections
import json
import os
from datetime import datetime

import requests

# http://dev.travisbell.com/play/v4_auth.html
ACCESS_TOKEN = os.environ["TMDB_ACCESS_TOKEN"]
API_KEY = os.environ["TMDB_API_KEY"]
ACCOUNT_ID = os.environ["TMDB_ACCOUNT_ID"]
SORT_BY = 6  # primary_release_date.desc

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["free", "rent", "all"], default="free")
args = parser.parse_args()
headers = {
    "content-type": "application/json;charset=utf-8",
    "authorization": f"Bearer {ACCESS_TOKEN}",
}


def main():
    lists = get_lists(ACCOUNT_ID)
    number_one_ids = get_movie_ids_from_list(
        lists["Box Office Number One Hits"]
    )
    watched_ids = get_movie_ids_from_list(lists["Watched"])
    marvel_ids = get_movie_ids_from_list(lists["Marvel Cinematic Universe"])
    movies = get_movies(number_one_ids, watched_ids, marvel_ids)
    print("Populating Lists....")
    print(f"(1 of {len(movies)}): Populating On Deck")
    populate_list(lists["On Deck"], "On Deck", movies.pop("On Deck"))
    for i, genre in enumerate(sorted(movies, reverse=True)):
        print(f"({i+2} of {len(movies) + 1}): Populating {genre}")
        populate_list(lists[genre], genre, movies[genre])


def get_lists(account_id):
    lists = {}
    page = 1
    while True:
        url = (
            f"https://api.themoviedb.org/4/account/{account_id}/lists"
            f"?page={page}"
        )
        response = requests.get(url, headers=headers).json()
        for result in response["results"]:
            lists[result["name"]] = result["id"]
            if result["sort_by"] != SORT_BY:
                sort_list_by_release_date(result["name"], result["id"])

        page = response["page"]
        total_pages = response["total_pages"]
        if page >= total_pages:
            break

        page += 1

    return lists


def sort_list_by_release_date(list_name, list_id):
    url = f"https://api.themoviedb.org/4/list/{list_id}"
    payload = {"sort_by": SORT_BY}
    payload = json.dumps(payload)
    response = requests.put(url, data=payload, headers=headers).json()
    if not response["success"]:
        print(f"Failed to sort list {list_name} by release date.")


def get_movie_ids_from_list(list_id):
    url = f"https://api.themoviedb.org/4/list/{list_id}"
    response = requests.get(url, headers=headers).json()
    movie_ids = set(
        int(object_id.split(":")[1]) for object_id in response["object_ids"]
    )

    return movie_ids


def get_movies(number_one_ids, watched_ids, marvel_ids):
    movies = collections.defaultdict(set)
    genres = get_genres()
    collection_cache = set()
    for i, movie_id in enumerate(number_one_ids):
        if args.mode != "all" and movie_id in marvel_ids:
            continue

        url = (
            f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}"
        )
        response = requests.get(url).json()
        print(f"({i+1} of {len(number_one_ids)}): " f"{response['title']}")
        if response["belongs_to_collection"]:
            collection_id = response["belongs_to_collection"]["id"]
            if collection_id in collection_cache:
                continue

            collection_cache.add(collection_id)
            collection_movies = get_movies_from_collection(
                collection_id, watched_ids
            )
            for movie in collection_movies:
                movie_id = movie["id"]
                if args.mode == "all" or (
                    get_watch_provider(movie_id) and movie_id not in marvel_ids
                ):
                    movies["On Deck"].add(movie_id)
                    for genre_id in movie["genre_ids"]:
                        genre = genres[genre_id]
                        movies[genre].add(movie_id)

        else:
            movie_id = response["id"]
            if movie_id not in watched_ids and (
                args.mode == "all" or get_watch_provider(movie_id)
            ):
                movies["On Deck"].add(movie_id)
                for genre in response["genres"]:
                    movies[genre["name"]].add(movie_id)

    return movies


def get_genres():
    url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={API_KEY}"
    response = requests.get(url).json()
    genres = {genre["id"]: genre["name"] for genre in response["genres"]}

    return genres


def get_movies_from_collection(collection_id, watched_ids):
    movies = []
    url = (
        f"https://api.themoviedb.org/3/collection/{collection_id}?"
        f"api_key={API_KEY}"
    )
    response = requests.get(url).json()
    parts = sorted(response["parts"], key=lambda part: part["release_date"])
    watched = True
    for i, part in enumerate(parts):
        if part["release_date"] == "":
            continue

        if part["id"] not in watched_ids:
            watched = False

        if watched:
            continue

        if part["release_date"] > datetime.today().strftime("%Y-%m-%d"):
            break

        movies.append(part)

        if args.mode != "all":
            break

    return movies


def get_watch_provider(movie_id):
    url = (
        f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers"
        f"?api_key={API_KEY}"
    )
    response = requests.get(url).json()
    if "US" not in response["results"]:
        return False

    if (
        "free" in response["results"]["US"]
        or "ads" in response["results"]["US"]
        or ("rent" in response["results"]["US"] and args.mode == "rent")
    ):
        return True

    if "flatrate" in response["results"]["US"]:
        for provider in response["results"]["US"]["flatrate"]:
            # PROVIDERS.add(provider["provider_name"])
            if provider["provider_name"] in (
                "Amazon Prime Video",
                "Disney Plus",
                "FXNow",  # Xfinity
                "HBO Max",  # Xfinity
                "Hulu",
                "Netflix",
                "Peacock Premium",  # Xfinity
                "Showtime",  # Xfinity
                "TBS",  # Xfinity
                "TNT",  # Xfinity
                "tru TV",  # Xfinity
            ):
                return True

    return False


def populate_list(list_id, list_name, movie_ids):
    clear_list(list_id, list_name)
    url = f"https://api.themoviedb.org/4/list/{list_id}/items"
    payload = {"items": []}
    for movie_id in movie_ids:
        payload["items"].append(
            {
                "media_type": "movie",
                "media_id": movie_id,
            }
        )

    payload = json.dumps(payload)
    response = requests.post(url, data=payload, headers=headers).json()
    if not response["success"]:
        print(f"Failed to populate list {list_name}.")


def clear_list(list_id, list_name):
    url = f"https://api.themoviedb.org/4/list/{list_id}/clear"
    response = requests.get(url, headers=headers).json()
    if not response["success"]:
        print(f"Failed to clear list {list_name}.")


if __name__ == "__main__":
    main()
