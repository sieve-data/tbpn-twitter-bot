# Tbpnify Twitter Bot

Code for creating an AI video influencer twitter bot using Sieve APIs!

### Setup:

Create a new virtual environment with

```bash
python3 -m venv venv
```

Install requirements with

```bash
pip install -r requirements.txt
```

Fill in the `.env` file with your environment variables, you can use `.env_example` as a sample.

```python
TW_BEARER_TOKEN=
TW_API_KEY=
TW_API_SECRET=
TW_ACCESS_TOKEN=
TW_ACCESS_SECRET=
OPENAI_API_KEY=
PERPLEXITY_API_KEY=
ELEVEN_LABS_API_KEY=
```

You will need to get keys for the X api from your X developer portal. Additionally you will need OpenAI, Perplexity, and Elevenlabs
keys for writing scripts and generating audio.

You will also need to download the TBPN overlay, you can get that from this [link](https://storage.googleapis.com/sieve-public-data/overlay.mov).

Deploy the create podcast function to your sieve acount.

- Login to sieve with your sieve API key with `sieve login`
- Deploy with `sieve deploy create_post.py`

Then update the sieve function in check_mentions.py:

`sieve.function.get("sieve-internal/create-tbpn-post")`

And also update the path to the log file: `check_log_path = ""`
Finaly

You can run a test for the calls to the bot with: `python check_mentions.py`

You can setup a cron job on your machine by running `crontab -e` and entering the following line:
This will run the script every 15 minutes to check for new pings.

```bash
*/15 * * * * /path/to/project/venv/bin/python3 /path/to/project/check_mentions.py >> /path/to/project/cron.log 2>&1
```

Additionally you can use some helper files for processing and creating clips in `preprocess_clips/`!
