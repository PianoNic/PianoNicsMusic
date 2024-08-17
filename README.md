<p align="center">
  <img src="https://github.com/Pianonic/PianoNicsMusic/blob/main/image/Logo.png?raw=true" alt="PianoNic's Music Bot" width="200"/>
</p>

# 🎹 PianoNic's Music Bot

## Description 🎶
PianoNic's Music Bot is a versatile Discord bot designed to elevate the music experience on your Discord server. Not only does it play your favorite tracks on command, but it also features a unique functionality that allows it to play music with a trained AI voice, bringing a novel and engaging musical experience to your community. Additionally, PianoNic's Music Bot can play music from virtually any source, offering a wide range of listening options.

## Features 🌟
- **🎵 Music Playback:** Play music directly in your Discord server's voice channels.
- **🗣️ AI Voice Integration:** Unique feature to play music using a trained AI voice for a distinctive listening experience.
- **🌐 Universal Source Playback:** Play music from any source, including various streaming services, URLs, and local files.
- **📜 Queue System:** Manage music playback with a queue system, allowing users to add, remove, and skip tracks.
- **👌 Easy Commands:** Simple and intuitive commands for controlling music playback and interacting with the AI voice features.

## Installation

1. **Clone the repository**:
    ```sh
    git clone https://github.com/yourusername/PianoNics-Music.git
    cd PianoNics-Music
    ```

2. **Install dependencies**:
    ```sh
    pip install -r requirements.txt
    ```

3. **Set up the database**:
    Ensure you have a database set up and configured in your environment.

## Configuration

1. **Create a `.env` file** in the root directory with the following structure:
    ```properties
    DISCORD_TOKEN=YOUR_DISCORD_TOKEN
    SPOTIFY_CLIENT_ID=YOUR_SPOTIFY_CLIENT_ID
    SPOTIFY_CLIENT_SECRET=YOUR_SPOTIFY_CLIENT_SECRET
    ```

2. **Obtain Spotify Credentials:**
    - To get your `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`, create an application on [Spotify's Developer Dashboard](https://developer.spotify.com/documentation/web-api/concepts/apps). Follow the instructions on the Spotify Developer website to register your app and retrieve your credentials.

3. **Run the bot**:
    ```sh
    python main.py
    ```

5. **Docker Setup 🐳**
   - **Build the Docker Image**
     ```
     docker build -t pianonic-music-bot .
     ```
   - **Run the Docker Container**
     ```
     docker run -d --name pianonic-music-bot pianonic-music-bot
     ```

## Usage 🚀
- **▶️ Playing Music:** Use the play command followed by the song name, URL, or file path to add it to the queue. The bot supports a wide range of sources.
- **🎤 AI Voice Music:** Activate the AI voice feature to experience music in a new way.
- **🔀 Managing the Queue:** Commands for queue management include adding, removing, and skipping tracks.

## Contributing 🤝
We welcome contributions to PianoNic's Music Bot! Feel free to make changes, and submit a pull request.

## License 📄
This project is licensed under the [EUCL License](LICENSE).
