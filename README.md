# Home Agent Telegram Bot

Welcome to the Home Agent project! This is an open-source Telegram bot designed to help you automate tasks, learn about bot development, and showcase your skills. Although this project is at an early stage, it demonstrates best practices in Python development, Poetry dependency management, and open collaboration.

## Features
- Built with Python and Poetry for modern dependency management
- Easily extendable and open for contributions
- Designed for beginners and enthusiasts
- Ready to be showcased on LinkedIn and other platforms

## Getting Started

### Prerequisites
- Basic knowledge of Poetry
- Python 3.8+ installed
- [Opencode](https://opencode.net/) installed (optional, for collaborative development)
- A Telegram bot created (see below)

### Setting up your environment
1. Clone this repository:
   ```bash
   git clone <repo-url>
   cd home-agent
   ```
2. Install dependencies with Poetry:
   ```bash
   poetry install
   ```
3. Copy `.env.sample` to `.env` and fill in your credentials:
   ```bash
   cp .env.sample .env
   # Edit .env with your Telegram bot token
   ```

### Creating a Telegram Bot
1. Open Telegram and search for [@BotFather](https://t.me/botfather).
2. Start a conversation and use `/newbot` to create your bot.
3. Follow the instructions and save your bot token.
4. Paste the token into your `.env` file.

### Running the Bot
To start the bot, run:
```bash
poetry run python -m telegram_reader.main
```

## Contributing
This project is open for contributions! Whether you're a beginner or an experienced developer, your input is welcome. Please follow best practices and submit pull requests for review.

## License
This project is licensed under the MIT License.

---

> **Showcase your skills!** Even as an early-stage project, Home Agent demonstrates your ability to work with modern Python tools, collaborate in open source, and build real-world bots. Add it to your LinkedIn profile and let your network know about your journey!
