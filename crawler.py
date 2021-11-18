import json
import os
import requests

# http://dev.travisbell.com/play/v4_auth.html
ACCESS_TOKEN = os.environ["TMDB_ACCESS_TOKEN"]
API_KEY = os.environ["TMDB_API_KEY"]
NUMBER_ONES_LIST_ID = os.environ["TMDB_NUMBER_ONES_LIST_ID"]
ON_DECK_LIST_ID = os.environ["TMDB_ON_DECK_LIST_ID"]
WATCHED_LIST_ID = os.environ["TMDB_WATCHED_LIST_ID"]
PROVIDERS = set()

headers = {
    "content-type": "application/json;charset=utf-8",
    "authorization": f"Bearer {ACCESS_TOKEN}",
}


def main():
    number_one_ids = get_movies_ids_from_list(NUMBER_ONES_LIST_ID)
    watched_ids = get_movies_ids_from_list(WATCHED_LIST_ID)
    on_deck_ids = get_on_deck_movie_ids(number_one_ids, watched_ids)
    populate_list(ON_DECK_LIST_ID, on_deck_ids)
    for provider in PROVIDERS:
        print(provider)


def get_movies_ids_from_list(list_id):
    url = f"https://api.themoviedb.org/4/list/{list_id}"
    response = requests.get(url, headers=headers).json()
    movie_ids = set(
        int(object_id.split(":")[1]) for object_id in response["object_ids"]
    )

    return movie_ids


def get_on_deck_movie_ids(number_one_ids, watched_ids):
    movie_ids = set()
    count = 0
    for movie_id in number_one_ids - watched_ids:
        count += 1
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}"
        response = requests.get(url).json()
        print(f"({count} of {len(number_one_ids - watched_ids)}): {response['title']}")
        if response["belongs_to_collection"]:
            collection_id = response["belongs_to_collection"]["id"]
            movie_id = get_movie_id_from_collection(collection_id, watched_ids)

        if movie_id and movie_id not in watched_ids and get_watch_provider(movie_id):
            movie_ids.add(movie_id)

    return movie_ids


def get_movie_id_from_collection(collection_id, watched_ids):
    url = f"https://api.themoviedb.org/3/collection/{collection_id}?api_key={API_KEY}"
    response = requests.get(url).json()
    parts = [part for part in response["parts"] if part.get("release_date")]
    for part in sorted(parts, key=lambda d: d["release_date"]):
        if part["id"] not in watched_ids:
            return part["id"]

    return None


def get_watch_provider(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers?api_key={API_KEY}"
    response = requests.get(url).json()
    if "US" not in response["results"]:
        return False

    if "free" in response["results"]["US"] or "ads" in response["results"]["US"]:
        return True

    if "flatrate" in response["results"]["US"]:
        for provider in response["results"]["US"]["flatrate"]:
            PROVIDERS.add(provider["provider_name"])
            if provider["provider_name"] in (
                "Amazon Prime Video",
                "Disney Plus",
                "Hulu",
                "IMDB TV Amazon Channel",
                "Netflix",
            ):
                return True

    return False


def populate_list(list_id, movie_ids):
    url = f"https://api.themoviedb.org/4/list/{list_id}/clear"
    requests.get(url, headers=headers)
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
    requests.post(url, data=payload, headers=headers)


if __name__ == "__main__":
    main()
