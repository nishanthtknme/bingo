import random
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Room

def generate_room_code():
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_grid():
    numbers = list(range(1, 26))
    random.shuffle(numbers)
    # Convert to 2D list (5x5)
    return [numbers[i:i+5] for i in range(0, 25, 5)]

def bingo(request):
    if request.method == "POST":
        action = request.POST.get("action")
        room_code = request.POST.get("room_code", "").strip().upper()

        if action == "create":
            room_code = generate_room_code()
            room = Room.objects.create(code=room_code, player1="Player 1", current_turn=None)
            room.player1_grid = generate_grid()
            room.save()
            return redirect(reverse("game_room", kwargs={"code": room.code}) + "?player=Player+1")

        elif action == "join":
            if not room_code:
                return render(request, "bingo.html", {"error": "Please enter a room code."})
            try:
                room = Room.objects.get(code=room_code)
                if room.player2:
                    return render(request, "bingo.html", {"error": "Room is full!"})

                room.player2 = "Player 2"
                room.player2_grid = generate_grid()
                if not room.current_turn:
                    room.current_turn = random.choice(["player1", "player2"])
                room.save()
                return redirect(reverse("game_room", kwargs={"code": room.code}) + "?player=Player+2")
            except Room.DoesNotExist:
                return render(request, "bingo.html", {"error": "Invalid room code!"})

    return render(request, "bingo.html")


def game_room(request, code):
    player_name = request.GET.get("player", "Guest")
    try:
        room = Room.objects.get(code=code)
    except Room.DoesNotExist:
        return render(request, "bingo_room.html", {"error": "Room not found!"})

    # Select the correct grid for the player
    player_grid = room.player1_grid if "1" in player_name else room.player2_grid

    context = {
        "room": room,
        "player": player_name,
        "grid": player_grid  # 2D list
    }
    return render(request, "bingo_room.html", context)






def index(request):
    return render(request, "index.html")

