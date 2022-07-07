import collections
import json
import os
import requests

# http://dev.travisbell.com/play/v4_auth.html
ACCESS_TOKEN = os.environ["TMDB_ACCESS_TOKEN"]
API_KEY = os.environ["TMDB_API_KEY"]
ACCOUNT_ID = os.environ["TMDB_ACCOUNT_ID"]
GENRES = collections.defaultdict(list)
# PROVIDERS = set()

headers = {
    "content-type": "application/json;charset=utf-8",
    "authorization": f"Bearer {ACCESS_TOKEN}",
}


def main():
    lists = get_lists(ACCOUNT_ID)
    number_one_ids = get_movies_ids_from_list(
        lists["Box Office Number One Hits"]
    )
    watched_ids = get_movies_ids_from_list(lists["Watched"])
    on_deck_ids = get_on_deck_movie_ids(number_one_ids, watched_ids)
    print("Populating Lists....")
    print(f"(1 of {len(GENRES) + 1}): Populating On Deck")
    populate_list(lists["On deck"], on_deck_ids)
    create_genre_lists(lists, GENRES)
    for i, genre in enumerate(sorted(GENRES, reverse=True)):
        print(f"({i+2} of {len(GENRES) + 1}): Populating {genre}")
        populate_list(lists[genre], GENRES[genre])
    # for provider in PROVIDERS:
    #     print(provider)


def get_lists(account_id):
    lists = {}
    page = 1
    total_pages = 2
    while page <= total_pages:
        url = (
            f"https://api.themoviedb.org/4/account/{account_id}/lists"
            f"?page={page}"
        )
        response = requests.get(url, headers=headers).json()
        page = response["page"] + 1
        total_pages = response["total_pages"]
        for result in response["results"]:
            lists[result["name"]] = result["id"]
            if result["sort_by"] != 6:
                url = f"https://api.themoviedb.org/4/list/{result['id']}"
                payload = {"sort_by": 6}
                payload = json.dumps(payload)
                response = requests.put(
                    url, data=payload, headers=headers
                ).json()
                if not response["success"]:
                    print(
                        f"Failed to sort list {result['name']} by release date."
                    )

    return lists


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
    for movie_id in number_one_ids:
        count += 1
        url = (
            f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}"
        )
        response = requests.get(url).json()
        print(
            f"({count} of {len(number_one_ids)}): "
            f"{response['title']}"
        )
        if response["belongs_to_collection"]:
            collection_id = response["belongs_to_collection"]["id"]
            movie_id = get_movie_id_from_collection(collection_id, watched_ids)

        if (
            movie_id
            and movie_id not in watched_ids | movie_ids
            and get_watch_provider(movie_id)
        ):
            movie_ids.add(movie_id)
            url = (
                f"https://api.themoviedb.org/3/movie/{movie_id}?"
                f"api_key={API_KEY}"
            )
            response = requests.get(url).json()
            for genre in response["genres"]:
                GENRES[genre["name"]].append(response["id"])

    return movie_ids


def get_movie_id_from_collection(collection_id, watched_ids):
    url = (
        f"https://api.themoviedb.org/3/collection/{collection_id}?"
        f"api_key={API_KEY}"
    )
    response = requests.get(url).json()
    parts = [part for part in response["parts"] if part.get("release_date")]
    for part in sorted(parts, key=lambda d: d["release_date"]):
        if part["id"] not in watched_ids:
            return part["id"]

    return None


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


def populate_list(list_id, movie_ids):
    url = f"https://api.themoviedb.org/4/list/{list_id}/clear"
    response = requests.get(url, headers=headers).json()
    if not response["success"]:
        print(f"Failed to clear list.")

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
        print(f"Failed to populate list.")


def create_genre_lists(lists, genres):
    for genre in genres:
        if genre not in lists:
            url = f"https://api.themoviedb.org/4/list"
            payload = {"name": genre, "iso_639_1": "en"}
            payload = json.dumps(payload)
            response = requests.post(url, data=payload, headers=headers).json()
            lists[genre] = response["id"]
            url = f"https://api.themoviedb.org/4/list/{response['id']}"
            payload = {"sort_by": 6}
            payload = json.dumps(payload)
            response = requests.put(url, data=payload, headers=headers).json()
            if not response["success"]:
                print(f"Failed to sort list {genre} by release date.")


if __name__ == "__main__":
    main()
