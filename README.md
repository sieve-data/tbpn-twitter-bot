# Tbpnify Twitter Bot

Code for creating an AI video influencer twitter bot using Sieve APIs!
You can check out our blog post on this project [here](https://www.sievedata.com/blog/ai-video-influencer-bot)

##### Note On Responsible Use:

It's important to build and represent influencers responsibly. Ideally, you should create content based on yourself or obtain explicit permission from the individual you're featuring. If you choose to use another creator's likeness, limit it to clearly humorous or parody contexts, and always make it transparent that the content was generated using AI. Above all, respect the creator's wishes, if they ask for the content to be removed, honor that decision promptly.

### Setup

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

You will need to get keys for the X API from your [X developer portal](https://developer.x.com). Additionally you will need OpenAI, Perplexity, and Elevenlabs keys for writing scripts and generating audio.

You will also need to download the TBPN overlay, you can get that from this [link](https://storage.googleapis.com/sieve-public-data/overlay.mov). Put this in the folder directory.

Set the voice IDs from Elevenlabs to the voices you want in `podcast_utils.py`:

```python
jordi_voice_id = "Tw6MHQ70AkrkqFDf75BN"
john_voice_id = "qMH3IpwT6hc2977abay7"
```

Deploy the create podcast function to your Sieve account:

- Login to Sieve with your Sieve API key with `sieve login`
- Deploy with `sieve deploy create_post.py`

Then update the Sieve function in `check_mentions.py`:

`sieve.function.get("your-sieve-username/create-tbpn-post")`

And also update the path to the log file: `check_log_path = ""`

Finally, you can run a test for @tbpnify calls to the bot with: `python check_mentions.py`

You can setup a cron job on your machine by running `crontab -e` and entering the following line:
This will run the script every 15 minutes to check for new pings.

```bash
*/15 * * * * /path/to/project/venv/bin/python3 /path/to/project/check_mentions.py >> /path/to/project/cron.log 2>&1
```

Additionally you can use some helper files for processing and creating clips in `preprocess_clips/`!
