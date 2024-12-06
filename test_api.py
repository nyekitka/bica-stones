import requests

HOST = "localhost"
PORT = "5434"
SRC = HOST + ":" + PORT
AGENT_ID = -123456

def get_lobby_ids():
    resp = requests.get(
        url = f"http://{SRC}/get_lobby_ids/"
    )
    print(resp.json())

def enter_lobby():
    agent_id = AGENT_ID
    lobby_id = int(input("Enter lobby id:"))
    params = {"lobby_id": lobby_id, "agent_id": agent_id}
    resp = requests.post(
        url = f"http://{SRC}/enter_lobby/", params=params
    )
    print(resp.json())
    
def leave_lobby():
    agent_id = AGENT_ID
    params = {"agent_id": agent_id}
    resp = requests.post(
        url=f"http://{SRC}/game/leave_lobby/", params=params)
    print(resp.json())
   
    
def pick_stone():
    agent_id = AGENT_ID
    stone = int(input("Enter stone"))
    params = {"agent_id": agent_id, "stone": stone}
    resp = requests.post(
        url = f"http://{SRC}/game/pick_stone/", params = params
    )
    print(resp.json())

def game_info():
    agent_id = AGENT_ID
    params = {"agent_id": agent_id}
    resp = requests.get(
        url = f"http://{SRC}/game/get_game_info/", params = params
    )
    print(resp.json())
  
    
OPTIONS = {
    1: "Get lobby ids",
    2: "Enter lobby",
    3: "leave lobby",
    4: "pick stone",
    5: "get game info"
}
    
def menu():
    
    for option_id, option in OPTIONS.items():
        print(f"{option_id}: {option}")
        
    return int(input())
    
def main():
    while True:
        opt = menu()
        if opt == 1:
            get_lobby_ids()
        elif opt == 2:
            enter_lobby()
        elif opt == 3:
            leave_lobby()
        elif opt == 4:
            pick_stone()
        elif opt == 5:
            game_info()
        else:
            pass
main()