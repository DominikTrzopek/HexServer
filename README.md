# Hex

This project aims to design and implement a multiplayer strategy-economic game with a 3D view for Windows PCs, along with a server application that allows multiple users to participate in the game. The server enables players to create or join games and establish connections with other users.

Inspired by games like Sid Meier's "Civilization," the gameplay is turn-based, with only one player allowed to make moves per turn. During their turn, a player can move units, attack other players' units based on specific factors like available movement points, and upgrade their fortifications. The objective is to earn as many points as possible within a set number of turns by building new structures.

The project implements user communication through network sockets, where each user connects to a central server application. The server handles connections and manages data transmission between connected players.

## Server Side

![test](https://github.com/user-attachments/assets/cee58d3c-f11e-4b67-8e15-7011f61734cf)

The project utilizes both UDP and TCP network sockets for communication between users. The communication process is illustrated in the diagram (Figure 19). Users exchange information through a server application that acts as an intermediary. All messages are standardized in JSON format and include an integer code that indicates the type of information being transmitted. Both the server and client share a list of message codes to ensure proper response handling.

The server is a separate application, allowing users to connect from remote locations via WAN, provided the server is hosted on a public IP address. To connect via UDP, users need the server's IP address and port number, which are pre-configured in the client application.

Using the client application, users can send one of three requests to the UDP server: create a new game (Create), retrieve a list of available games (Get), or delete a created game (Delete). Game data is stored in a server_list database collection for easy access. Upon receiving a Create request, the UDP server launches a new TCP server process to manage communication during the game. Each game session is handled by its dedicated TCP server.

Users connect directly to the TCP server to join a game. The UDP server adds the TCP server's PID, IP address, and port numbers to the Create request and stores them in the database. This allows the UDP server to send the client a list of available TCP servers when responding to a Get request.

A TCP server can be terminated either by receiving a Delete request from the user who created it or by a daemon process detecting inactivity. The Delete request triggers the server to close its network sockets and release resources before shutting down. User identities consist of public and private IDs; private IDs are used for server creation and deletion, hashed by the server, and stored securely in the database. Public IDs are used for player interactions and ownership identification within the game.

## Client Side
https://github.com/DominikTrzopek/Hex

The application is a multiplayer, turn-based, 3D strategy-economic game designed for at least two players. The game features an isometric perspective and takes place on a procedurally generated hexagonal grid. Each player starts with a base in one corner of the map, and the goal is to accumulate the most points by building structures and managing resources.

### Key Features

- **Multiplayer:** Supports at least two players.
- **Turn-Based:** Only one player can make a move at a time.
- **3D Isometric View:** The game is played in a three-dimensional space with an isometric perspective.
- **Procedural Map Generation:** The map is procedurally generated to ensure balanced starting positions for each player.

### Gameplay Mechanics

- **Hexagonal Grid:** The map consists of hexagonal tiles, each with specific tags that determine the objects and interactions possible on that tile.
- **Resource Management:** Players manage resources to perform actions like creating units or building structures. Resources are gained each turn based on control of resource deposits.
- **Structure Building:** Structures claim surrounding tiles and earn points for the player. Destroyed structures result in the loss of associated points, and structures must be connected to the player's base.
- **Unit Actions:** Units can move, attack, or upgrade stats (health, attack power, attack range, movement range). Actions are executed using a Command pattern, enabling flexibility and reusability in unit operations.
- **Combat:** Units can either move and attack in a turn or just attack. An attack ends the unit's actions for the turn.
- **Player Identification:** Each player is represented by a unique color, distinguishing ownership of units and structures on the map.

### Game Objective
The game ends when the maximum number of moves is reached, and the player with the most points wins. If a player's base is destroyed, they lose the game immediately.

## Game presentation

![obraz](https://github.com/user-attachments/assets/e66ae457-160e-4891-ac64-fc0dabeb1db3)

Main Menu

![obraz](https://github.com/user-attachments/assets/4889e785-d377-4d73-938e-94740896a9ea)

Connecting to server

![obraz](https://github.com/user-attachments/assets/771ae5b4-b396-4bc6-a9a2-0284d5f3d932)

Start of the game

![obraz](https://github.com/user-attachments/assets/71e4a44a-f8b4-4628-b5cd-756af09043a9)

Attacking enemy units

![obraz](https://github.com/user-attachments/assets/8f08915a-3fc3-472b-bdff-e4361fb59498)
![obraz](https://github.com/user-attachments/assets/5a7c83e7-2936-4663-974c-aa855bbd7a54)

Examples of map generation








