# Home Agent Telegram Bot

Welcome to my new project, the **Home Agent project**! This is an open-source Telegram bot designed to help automate tasks,
and learn about bot development.

## Features

- Built with Python and Poetry
- Easily extendable and open for contributions
- Designed for beginners and enthusiasts

## Getting Started

### Prerequisites

- Python 3.11+ (not tested, but expected to run on 3.9+)
- Basic knowledge of Poetry
- [Opencode AI cli](hhttps://opencode.ai/)
- A Telegram bot created (see below)

### Creating a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather).
2. Start a conversation and use `/newbot` to create your bot.
3. Follow the instructions and save your bot token.
4. Paste the token into your `.env` file.

### Set up your and run

1. Install dependencies with Poetry:
   ```bash
   poetry install --no-root
   ```
2. Copy `.env.sample` to `.env` and fill in your Telegram Bot credentials.
3. Start the app:
   ```bash
   poetry run python -m telegram_reader.main
   ```
   [3 lines of post-context]

### Example in Action

Below you can see Home Agent in use:

**Telegram request:**
![Telegram request](docs/request.png)

**App response:**
![App response](docs/app-stdout.png)

## Contributing

This project is open for contributions! Whether you're a beginner or an experienced developer, your input is welcome. Please follow best practices and submit pull requests for review.
