# SymphCord
Discord bot that turns recent channel chatter into a short melodic clip.
![bADGE](https://hackatime-badge.hackclub.com/U09Q1BWBCR0/SymphCord)
## Features
- Slash command `/compose` grabs the last 100 channel messages
- info commands: `/help`, `/creator`, `/purpose`, `/ping`, `/botinfo`
- Messages become notes: length → pitch, timestamps → rhythm, author → instrument
- Generates a 15–30 second WAV file with simple synth voices (pydub oscillators)
- Optional SoundFont rendering: set `SOUNDFONT_PATH` to a `.sf2` file to get real instruments (piano, pads, choir)

## Quick start
1. Create and invite a Discord application/bot with the `applications.commands` and `bot` scopes. Enable the **Message Content Intent**.
2. Clone the repo and install Python dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` (see below) and fill in your bot token.
4. Run the bot:
   ```bash
   python main.py
   ```

## Run with Docker
1. Build the image:
   ```bash
   docker build -t symphcord .
   ```
2. Copy `.env.example` to `.env`, set your credentials, and optionally add `SOUNDFONT_PATH=/soundfonts/your.sf2`.
3. Run the container (mount the SoundFont directory only if you use one):
   ```bash
   docker run \
     --env-file .env \
     -v "$(pwd)/soundfont:/soundfonts" \
     symphcord
   ```
   Remove the `-v` flag when you do not need an external SoundFont.

## Environment variables (`.env`)
```
DISCORD_TOKEN=your-bot-token
# Optional: set if you already have an application id handy
DISCORD_APPLICATION_ID=123456789012345678
LOG_LEVEL=INFO
# Optional: use a SoundFont for richer instruments
SOUNDFONT_PATH=/path/to/your/soundfont.sf2
```

## Usage
- Drop `/compose` in any text channel the bot can read.
- The bot fetches the latest 100 non-bot messages, blends them into a short track, and replies with an embed plus a downloadable WAV file.
- Each user's messages use a consistent waveform, so group chats form a little ensemble over time.
