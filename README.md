# TMDB Crawler

A script that uses the TMDB API to get all number one box office hits and find any that are currently steaming that I haven't watched yet.

## Set-up

Set-up a virtual environment and activate it:

```bash
python3 -m venv env
source env/bin/activate
```

You should see (env) before your command prompt now. (You can type `deactivate` to exit the virtual environment any time.)

Install the requirements:

```bash
pip install -U pip
pip install -r requirements.txt
```

Obtain a TMDB API key [here](https://www.themoviedb.org/settings/api).
Obtain a TMDB Access token [here](http://dev.travisbell.com/play/v4_auth.html)
Obtain your TMDB Account ID (gravatar hash) [here](http://dev.travisbell.com/play/v3_account_details.html)

Set up your environment variables:

```bash
touch .env
echo export TMDB_API_KEY="XXX" >> .env
echo export TMDB_ACCESS_TOKEN="XXX" >> .env
echo export TMDB_ACCOUNT_ID="XXX" >> .env
```

## Usage

Make sure you are in the virtual environment (you should see (env) before your command prompt). If not `source /env/bin/activate` to enter it.

Make sure .env variables are set:

```bash
set -a; source .env; set +a
```

Then run the script:

```bash
Usage: crawler.py
```

## License

TMDB Crawler is licensed under the [MIT license](https://github.com/danrneal/route-planner/blob/master/LICENSE).
