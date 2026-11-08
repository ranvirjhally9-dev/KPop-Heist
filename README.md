# KPop Heist

A Discord bot starter with moderation, K-pop lookup, trivia, fun commands, a virtual heist economy, and voice music playback.

## Commands

- Moderation: `/kick`, `/ban`, `/timeout`, `/purge`
- Music: `/play`, `/skip`, `/stop`, `/leave`
- K-pop: `/idol`, `/quiz`
- Fun: `/coinflip`, `/roll`, `/8ball`
- Heist economy: `/balance`, `/daily`, `/heist`, `/leaderboard`
- Utility: `/ping`, `/help`

## GitHub setup

1. Create a new **private** GitHub repository.
2. Upload the files in this folder. Do not upload `.env` or your bot token.
3. In your hosting dashboard, connect the repository.
4. Set the start command to `python main.py` (or use the included `Procfile` if your host supports it).
5. Add these environment variables in the host dashboard:
   - `DISCORD_TOKEN`
   - `LAVALINK_URI`
   - `LAVALINK_PASSWORD`
6. Deploy and check the logs.

## Discord developer portal

1. Create an application and add a Bot.
2. Copy its token and put it in the host's `DISCORD_TOKEN` variable. Never share the token or commit it to GitHub.
3. In OAuth2 URL Generator, select `bot` and `applications.commands`.
4. Grant only the permissions needed: View Channels, Send Messages, Embed Links, Read Message History, Connect, Speak, and moderation permissions you intend to use.
5. Invite it to your server.

## Music requirement

Voice music needs a separate **Lavalink v4** server. Put its address and password in `LAVALINK_URI` and `LAVALINK_PASSWORD`. The Lavalink server must have a playable source configured. The bot cannot stream music from GitHub itself. Respect the audio provider's terms and copyright rules.

## Notes

- The heist feature is fictional and uses virtual coins only.
- `/idol` uses Wikipedia page summaries and thumbnails where available.
- `/purge` and the moderation commands require Manage Messages permission. The bot's role must also be high enough in the server role list to moderate the target member.
- Keep the repository private if it contains project details. Never put tokens or passwords in source code.
