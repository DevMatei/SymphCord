import logging
import os

from dotenv import load_dotenv

from bot import SymphCordBot


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="[%(asctime)s] %(levelname)s:%(name)s: %(message)s",
    )


def main() -> None:
    load_dotenv()
    configure_logging()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Set DISCORD_TOKEN in your environment or .env file.")

    bot = SymphCordBot()
    try:
        bot.run(token)
    except KeyboardInterrupt:
        logging.getLogger("symphcord").info("Shutting down SymphCord.")


if __name__ == "__main__":
    main()
