import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.apps import apps

class BingoConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_code = self.scope["url_route"]["kwargs"]["code"]
        self.room_group_name = f"bingo_{self.room_code}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        room = await self.get_room()

        # Initialize rematch votes
        if room.rematch_votes is None:
            room.rematch_votes = []
            await self.save_room(room)

        # -----------------------------------------------------
        # Send current players count to all clients
        # -----------------------------------------------------
        players_count = 0
        if room.player1:
            players_count += 1
        if room.player2:
            players_count += 1

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "players_count_event",
                "count": players_count,
                "current_turn": room.current_turn
            }
        )

        # Start game if both players present
        if room.player1 and room.player2:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "game_start_event",
                    "current_turn": room.current_turn
                }
            )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        room = await self.get_room()

        # Update players count on disconnect
        players_count = 0
        if room.player1:
            players_count += 1
        if room.player2:
            players_count += 1

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "players_count_event",
                "count": players_count,
                "current_turn": room.current_turn
            }
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")
        player = data.get("player")
        number = data.get("number")

        room = await self.get_room()

        # -----------------------------------------------------
        # CHAT
        # -----------------------------------------------------
        if action == "chat":
            message = data.get("message")
            emoji = data.get("emoji", None)

            # Broadcast chat to all players (so sender sees it too)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_event",
                    "player": player,
                    "message": message,
                    "emoji": emoji,
                }
            )

            # Send notification only to opponent
            await self.send_to_opponent(player, {
                "action": "notification",
                "message": f"New message from {player}"
            })
            return

        # -----------------------------------------------------
        # MARK NUMBER
        # -----------------------------------------------------
        if action == "mark_number":
            if room.current_turn != player:
                await self.send(json.dumps({
                    "action": "error",
                    "message": "Not your turn!"
                }))
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "mark_number_event",
                    "number": number,
                    "player": player
                }
            )

            # Switch turn
            room.current_turn = "player2" if player == "player1" else "player1"
            await self.save_room(room)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "turn_change_event",
                    "current_turn": room.current_turn
                }
            )

        # -----------------------------------------------------
        # CALL BINGO
        # -----------------------------------------------------
        elif action == "call_bingo":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "bingo_called_event",
                    "message": f"{player} called Bingo! Game Over!"
                }
            )

        # -----------------------------------------------------
        # PLAY AGAIN
        # -----------------------------------------------------
        elif action == "play_again":
            if player not in room.rematch_votes:
                room.rematch_votes.append(player)
                await self.save_room(room)

            votes = set(room.rematch_votes)

            # FIRST vote → notify opponent
            if votes == {player}:
                await self.send_to_opponent(player, {
                    "action": "play_again_request",
                    "player": player
                })

            # BOTH voted → reset game
            elif votes == {"player1", "player2"}:
                room.rematch_votes = []
                room.current_turn = "player1"
                await self.save_room(room)

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "reset_game_event",
                        "current_turn": room.current_turn
                    }
                )

    # -----------------------------------------------------
    # DIRECT MESSAGE TO OPPONENT ONLY
    # -----------------------------------------------------
    async def send_to_opponent(self, player, message):
        group = self.channel_layer.groups.get(self.room_group_name, [])
        for channel in group:
            if channel != self.channel_name:
                await self.channel_layer.send(channel, {
                    "type": "direct_message",
                    "payload": message
                })

    async def direct_message(self, event):
        await self.send(json.dumps(event["payload"]))

    # -----------------------------------------------------
    # CHAT EVENT HANDLER
    # -----------------------------------------------------
    async def chat_event(self, event):
        await self.send(json.dumps({
            "action": "chat",
            "player": event["player"],
            "message": event["message"],
            "emoji": event["emoji"]
        }))

    # -----------------------------------------------------
    # GAME EVENTS
    # -----------------------------------------------------
    async def mark_number_event(self, event):
        await self.send(json.dumps({
            "action": "mark_number",
            "number": event["number"],
            "player": event["player"]
        }))

    async def turn_change_event(self, event):
        await self.send(json.dumps({
            "action": "turn_change",
            "current_turn": event["current_turn"]
        }))

    async def bingo_called_event(self, event):
        await self.send(json.dumps({
            "action": "bingo_called",
            "message": event["message"]
        }))

    async def game_start_event(self, event):
        await self.send(json.dumps({
            "action": "game_start",
            "current_turn": event["current_turn"]
        }))

    async def reset_game_event(self, event):
        await self.send(json.dumps({
            "action": "reset_game",
            "current_turn": event["current_turn"]
        }))

    async def players_count_event(self, event):
        await self.send(json.dumps({
            "action": "players_count",
            "count": event["count"],
            "current_turn": event["current_turn"]
        }))

    # -----------------------------------------------------
    # DATABASE HELPERS
    # -----------------------------------------------------
    @database_sync_to_async
    def get_room(self):
        Room = apps.get_model("game", "Room")
        return Room.objects.get(code=self.room_code)

    @database_sync_to_async
    def save_room(self, room):
        room.save()
