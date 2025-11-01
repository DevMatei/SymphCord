# SymphCord
Discord bot that turns recent channel chatter into a short melodic clip.

## Features
- Slash command `/compose` grabs the last 100 channel messages
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

## Environment variables (`.env`)
```
DISCORD_TOKEN=your-bot-token
# Optional: speeds up slash-command sync while you iterate
DISCORD_SYNC_GUILD_ID=your-dev-server-id
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

