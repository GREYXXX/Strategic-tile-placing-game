# CITS3002 2021 Assignment
# Author: XI RAO
# Student Number: 22435044
# This file implements a basic server that allows a single client to play a
# single game with no other participants, and very little error checking.
#
# Any other clients that connect during this time will need to wait for the
# first client's game to complete.
#
# Your task will be to write a new server that adds all connected clients into
# a pool of players. When enough players are available (two or more), the server
# will create a game with a random sample of those players (no more than
# tiles.PLAYER_LIMIT players will be in any one game). Players will take turns
# in an order determined by the server, continuing until the game is finished
# (there are less than two players remaining). When the game is finished, if
# there are enough players available the server will start a new game with a
# new selection of clients.

import socket
import sys
import tiles
import threading
import random
from time import sleep


#Init all of edge tiles posotion
edge_tiles = [(0, 0), (1, 0), (2,0), (3,0), (4,0), (0,1), (0,2), (0,3), (0,4), (4,1), (4,2), (4,3), (1,4), (2,4), (3,4)]

print_lock = threading.Lock()
count = 0
game_over = 1
game_restart_finsihed = False
client_timer = None
board = tiles.Board()

currentPlayer= 0
idnum = 0
socks = {}
threads = {}
live_idnums = {}
clients_map = {}
valid_tiles = {}
is_turn_broadcast = {}
spec = []
eliminatedPlayer = []
board_moves = []
first_tile_save = {}
remains = {}


"""
Send MessageWelcome(idnum) to every clients
"""
def broadcast_welcome(idnum):
  conn = socks[idnum]
  conn.send(tiles.MessageWelcome(idnum).pack())


"""
Send tiles that made by one of clients to all clients
"""
def broadcast_tiles(msg):
  global valid_tiles, idnum, clients_map
  playerid = clients_map[idnum]
  valid_tiles[playerid] = valid_tiles[playerid] + 1
  for conn in list(socks.values()):
      conn.send(msg)

def broadcast_tokens(msg):
  for conn in list(socks.values()):
    conn.send(msg)

"""
Send MessageGameStart() to all clients when restart a game
"""
def broadcast_gameStart():
  for conn in list(socks.values()):
    conn.send(tiles.MessageGameStart().pack())


"""
Send which player left to all clients
"""
def broadcast_playerleft(idnum):
  for conn in list(socks.values()):
    conn.send(tiles.MessagePlayerLeft(idnum).pack())

"""
Send new client id number to all clients if a new client join in the game
Server send other clients id number to new clients
"""
def broadcast_playerjoined(name, idnum, live_idnums):
  # print("SOCKS is {}".format(socks.keys()))
  try:
    for i in socks.keys():
      if i != idnum:
        conn = socks[i]
        conn.send(tiles.MessagePlayerJoined(name, idnum).pack())

    conn1 = socks[idnum]  
    for i in live_idnums.keys():
      if i!= idnum:
        conn1.send(tiles.MessagePlayerJoined(live_idnums[i], i).pack())
  except:
    pass

"""
Send each client's id number to all cients
Called at re-start a new if a game is finished
"""
def broadcast_playerjoined1(name, idnum):
  # print("name is {}".format(name))
  for i in socks.keys():
    if i != idnum:
      conn = socks[i]
      conn.send(tiles.MessagePlayerJoined(name, idnum).pack())

"""
Send MessagePlayerEliminated(idnum) to all clients in order to let them know which client(s) is eliminated
"""
def broadcast_eliminated(idnum):
  global spec
  for i in socks.keys(): 
    if i not in spec: #Spectator will not recieve eliminated player message due to it has not been broadcast turn
      conn = socks[i]
      conn.send(tiles.MessagePlayerEliminated(idnum).pack())

"""
Send next player's turn to all clients
"""
def broadcast_turn(idnum):
  global is_turn_broadcast
  if idnum not in is_turn_broadcast.keys():
    is_turn_broadcast[idnum] = True
  for conn in list(socks.values()):
    conn.send(tiles.MessagePlayerTurn(idnum).pack())

"""
Adding new tiles after place
"""

def broadcast_addTile(idnum):
  for i in socks.keys():
    if i in socks.keys():
      conn = socks[i]
    else:
      continue
    if i != idnum:
      for _ in range(tiles.HAND_SIZE):
        tileid = tiles.get_random_tileid()
        conn.send(tiles.MessageAddTileToHand(tileid).pack())

"""
Adding new tiles after place, used at re-start a new game
"""
def broadcast_addTile1():
  for i in socks.keys():
    conn = socks[i]
    for _ in range(tiles.HAND_SIZE):
      tileid = tiles.get_random_tileid()
      conn.send(tiles.MessageAddTileToHand(tileid).pack())

"""
Send all moves to spectator
"""
def broad_allMoves(msgs, idnum):
  conn = socks[idnum]
  for msg in msgs:
    conn.send(msg)

"""
Remove the repeated elements in clients_map, and make it in order
"""
def rank_clients_map():
  global clients_map
  func = lambda z:dict([(x, y) for y, x in z.items()])
  values = list(clients_map.values())
  for i in range(len(clients_map)):
    clients_map[i] = values[i]
  clients_map = func(func(clients_map))

"""
Timeout function for starting the first game 
"""
def Timeouts():
  global game_over, clients_map, count, first_tile_save, valid_tiles, board, board_moves, spec

#Reseting lists
  board_moves = []
  count = 0
  idnum = 0
  first_tile_save.clear()
  board.reset()
  for playerid in valid_tiles:
    valid_tiles[playerid] = 0
  
  if len(socks) < 2: #If some clients diconnect the game during countdown
    return
  rank_clients_map()
  broadcast_gameStart()
  broadcast_addTile1()
  broadcast_turn(clients_map[idnum])
  game_over = 0


"""
Timeouts function for re-start a game when a game is finished
"""
def Timeouts1():
  global idnum, clients_map, spec, eliminatedPlayer, live_idnums, game_over, game_restart_finsihed
  global board_moves, count, first_tile_save, valid_tiles

#Resting all variables  
  idnum = 0
  count = 0
  clients_map.clear()
  first_tile_save.clear()
  board_moves = []
  spec = []
  eliminatedPlayer = []
  is_turn_broadcast.clear()
  live_idnums.clear()

  for i in remains.keys():
    live_idnums[i] = remains[i]

  for playerid in valid_tiles:
    valid_tiles[playerid] = 0
  temp_ids = list(remains.keys())
  print("remains {}".format(remains))
  print("live_idnums {}".format(live_idnums))

  if len(remains) > 1 and len(remains) < 5:
    for i in range(len(temp_ids)):
      clients_map[i] = temp_ids[i]             
  elif len(live_idnums) > 4:
    r = random.SystemRandom()
    r.shuffle(temp_ids)
    for i in range(len(temp_ids)):
      if i > 3:
        spec.append(temp_ids[i])
        break
      else:
        clients_map[i] = temp_ids[i]
  elif len(remains) < 2:
    if len(remains) == 0:
      return
    clients_map[0] = temp_ids[0]
    print("less than 2 players remains.... game finished, waiting for other clients connect")
    board.reset()
    #broadcast_eliminated(clients_map[idnum])
    game_over = 1
    game_restart_finsihed = True
    return
  
#Reseting the board, and broadcast player joined, gameStart, and turn......
  try:
    board.reset()
    broadcast_gameStart()
    for i in temp_ids:
      broadcast_welcome(i) 
    for id in live_idnums.keys():
      sock_name = live_idnums[id]
      broadcast_playerjoined1(sock_name, id)  
    broadcast_addTile1()
    broadcast_turn(clients_map[idnum])
    game_over = 0
    game_restart_finsihed = True
  except:
    return


"""
Helper function for tier 4
"""
def first_turn():
  global board, edge_tiles
  loc = edge_tiles[random.randint(0, len(edge_tiles) - 1)]
  x = loc[0]
  y = loc[1]
  tileid = tiles.get_random_tileid()
  rotation = random.randint(0, 3)
  
  return x, y, tileid, rotation

"""
Helper function for tier 4
"""
def get_pos():
  return random.randint(0, 4)

"""
Helper function for tier 4
"""
def get_tile_rot():
  rotation = random.randint(0, 3)
  tileid = tiles.get_random_tileid()
  return rotation, tileid

"""
Server start a random token for client at second turn
"""
def server_do_action_second(idnum):
  global board, first_tile_save, live_idnums, clients_map
  x = first_tile_save[idnum][0]
  y = first_tile_save[idnum][1]
  for position in range(0, 7):
    if not board.have_player_position(idnum):
      if board.set_player_start_position(idnum, x, y, position):
        for conn in list(socks.values()):
          conn.send(tiles.MessageMoveToken(idnum, x, y, position).pack())
        positionupdates, eliminated = board.do_player_movement(list(live_idnums.keys()))
        for msg in positionupdates:
          broadcast_tiles(msg.pack())        
          board_moves.append(msg.pack())
        if idnum in eliminated:
          eliminatedPlayer.append(idnum)
          broadcast_eliminated(idnum)
          is_turn_broadcast[idnum] = False
          break
      else:
        print("loc is not feasible.............")
        continue
  id = nextTurn()
  broadcast_turn(clients_map[id])

  return

"""
Server makes a random tiles for client at first and any subsequnt turn
"""
def server_do_action(idnum):
  global board, count, live_idnums, clients_map, valid_tiles
  if not board.have_player_position(idnum):
    while True:
      x, y, tileid, rotation= first_turn()
      if not board.set_tile(x, y, rotation, tileid, idnum):
        continue
      else:
        break
  else:
    x, y, _ = board.get_player_position(idnum)
    rotation, tileid = get_tile_rot()
    board.set_tile(x, y, rotation, tileid, idnum)

  for conn in list(socks.values()):
    conn.send(tiles.MessagePlaceTile(idnum, tileid, rotation, x, y).pack())
  valid_tiles[idnum] = valid_tiles[idnum] + 1
  positionupdates, eliminated = board.do_player_movement(list(live_idnums.keys()))
  for msg in positionupdates:
    broadcast_tiles(msg.pack())        
    board_moves.append(msg.pack())
  if idnum in eliminated:
    eliminatedPlayer.append(idnum)
    broadcast_eliminated(idnum)
    is_turn_broadcast[idnum] = False
  if count < 4:
    first_tile_save[idnum] = (x, y)
    count += 1
  id = nextTurn()
  broadcast_turn(clients_map[id])


"""
Make a next turn if a player has finished 
"""
def nextTurn():
  global idnum, clients_map, eliminatedPlayer
  size = len(clients_map)
  if clients_map[(idnum + 1) % size] in eliminatedPlayer and clients_map[(idnum + 2) % size] not in eliminatedPlayer:
    idnum = (idnum + 2) % size
  elif clients_map[(idnum + 1) % size] in eliminatedPlayer and clients_map[(idnum + 2) % size] in eliminatedPlayer:
    idnum = (idnum + 3) % size
  else:
    idnum = (idnum + 1) % size
  return idnum




#Timer will be statred when second client connect the game
#Count down for 8 second, and Timeoues triggered, game is start... 

def client_handler(connection, address, playerID):
  global currentPlayer, idnum, live_idnums, eliminatedPlayer, clients_map, spec, board_moves, game_over
  global remains, board, game_restart_finsihed, is_turn_broadcast, first_tile_save, count, valid_tiles, client_timer
  print("player ID is {}".format(playerID))
  host, port = address
  name = '{}:{}'.format(host, port)

  valid_tiles[playerID] = 0
  if playerID not in live_idnums.keys():
    live_idnums[playerID] = name
    remains[playerID] = name

  #broadcast playerjoined
  broadcast_playerjoined(name, playerID, live_idnums)
  connection.send(tiles.MessageWelcome(playerID).pack())

  #If a player join during the game, treat as spec
  if playerID not in spec and playerID not in list(clients_map.values()) and game_over == 0:
    broad_allMoves(board_moves, playerID)
    spec.append(playerID)
  
  if len(live_idnums) < 5 and game_over == 1:
    clients_map[playerID] = playerID
  elif len(live_idnums) > 4 and game_over == 1:
    r = random.SystemRandom()
    temp_clients = list(live_idnums.keys())
    r.shuffle(temp_clients)
    for i in range(len(temp_clients)):
      if i > 3:
        spec.append(temp_clients[i])
        break
      else:
        clients_map[i] = temp_clients[i]

  
  if len(socks) == 2:
    timer = threading.Timer(8.0, Timeouts)
    timer.start()
    print("timer start.....")
  
  #sleep(7)
  
  print("game_over iss {}".format(game_over))

  while True:
    """
    Timeouts function for server to make a valid moves after 10 sec if client have not make a move  (tier 4)
    """
    print("Eliminated players {}".format(eliminatedPlayer))
    # try:   
    #   if connection ==  socks[clients_map[idnum]]:
    #    connection.settimeout(10)
    # except:
    #   print("exception")
    try:
      chunk = connection.recv(4096)
    # except socket.timeout as e:
    #   #print(connection)
    #   print("time out" + " " +  str(e))
    #   if valid_tiles[clients_map[idnum]] == 1:
    #     server_do_action_second(clients_map[idnum])
    #   else:
    #     server_do_action(clients_map[idnum])
    #   if len(eliminatedPlayer) == len(live_idnums) -len(spec) - 1:
    #     print("This game is over, starting a new game.....")
    #     timer_turn = threading.Timer(4.0, Timeouts1)
    #     timer_turn.start()
                  
    #     if game_restart_finsihed:
    #       game_restart_finsihed = False
    #       return
    #   continue

    except Exception as e:
      print("recv exception" + "  " + str(e))
      break
    
    if not chunk: 
      del remains[playerID]
      del valid_tiles[playerID]
      print('client {} disconnected'.format(address))

      #If a client that has never been allocate a turn disconnecting, don't broadcast this player is eliminated
      #Else, send eliminate info to all clients 
      if playerID not in eliminatedPlayer and playerID not in spec:
        eliminatedPlayer.append(playerID)
        try:
          if playerID in is_turn_broadcast.keys() and is_turn_broadcast[playerID] == True:
            broadcast_eliminated(playerID)
        except:
          print("broadcast exception")
          pass
      else:
        print("player {} already be eliminated!".format(playerID))  
        del socks[playerID]
        return

      del socks[playerID]
      if playerID in is_turn_broadcast:
        del is_turn_broadcast[playerID]
      
      #Send player left message to all clients
      try:
        broadcast_playerleft(playerID) 
      except:
        pass    
      
      #Exit the game if there are no clients in the game now
      if len(socks) == 0:
        game_over = 1
        return

      #If some clients get out of the game causing the game over, start a new game...
      if len(eliminatedPlayer) == len(live_idnums) -len(spec) - 1 and game_over != 1:
        print("This game is over, starting a new game.....")
        timer_turn = threading.Timer(3.0, Timeouts1)
        timer_turn.start()

        if game_restart_finsihed:
          return
      
      #If it's current turn's player disconnect, switch to next turn
      #If game is over, dont broadcast next turn
      try:
        if playerID == clients_map[idnum] and len(socks) != 0 and game_over != 1:
          idnum = nextTurn()
          broadcast_turn(clients_map[idnum])
      except:
        pass
      return

    print("there are {} players in the game now".format(len(live_idnums) - len(eliminatedPlayer) - len(spec)))

    #If a clients at others turn sends a message, ignore it
    if clients_map[idnum] != playerID:
      print("this is not player {}'s turn, its player {} 's turn".format(playerID,clients_map[idnum])) 
      continue
    
    #If a spectator sends a message to server, ignore it
    if playerID in spec:
      print("player {} is spec".format(playerID))
      continue

    buffer = bytearray()
    buffer.extend(chunk)   


    while True:
      msg, consumed = tiles.read_message_from_bytearray(buffer)
      if not consumed:
        break
    
      buffer = buffer[consumed:]
      print('received message from client : {} {} {} {}'.format(address, msg, consumed, msg.idnum))

      # sent by the player to put a tile onto the board (in all turns except
      # their second)
      if isinstance(msg, tiles.MessagePlaceTile):
        used_tileid = msg.tileid
        if board.set_tile(msg.x, msg.y, msg.tileid, msg.rotation, msg.idnum):
          # notify client that placement was successful
          if count < 4:
            first_tile_save[playerID] = (msg.x, msg.y)
            count += 1
          board_moves.append(msg.pack())
          broadcast_tiles(msg.pack())

          # check for token movement
          positionupdates, eliminated = board.do_player_movement(list(live_idnums.keys()))
          for msg in positionupdates:
            if msg.idnum not in eliminatedPlayer:
              broadcast_tokens(msg.pack())    
              board_moves.append(msg.pack())
          
          #Check all eliminated players
          for id in eliminated:
            if id not in eliminatedPlayer:
              eliminatedPlayer.append(id)
              broadcast_eliminated(id)
              is_turn_broadcast[id] = False
          #Restart a new game if a game is finished
          if len(eliminatedPlayer) == len(live_idnums) -len(spec) - 1:
            print("This game is over, starting a new game.....")
            game_over = 1
            timer_turn = threading.Timer(3.0, Timeouts1)
            timer_turn.start()

            if game_restart_finsihed:
              break
          

          # pickup a new tile
          tileid = used_tileid
          connection.send(tiles.MessageAddTileToHand(tileid).pack())

          # start next turn
          if game_over != 1:
            idnum = nextTurn()
            broadcast_turn(clients_map[idnum])

      # sent by the player in the second turn, to choose their token's
      # starting path
      elif isinstance(msg, tiles.MessageMoveToken):
        if not board.have_player_position(msg.idnum):
          if board.set_player_start_position(msg.idnum, msg.x, msg.y, msg.position):
            # check for token movement
            positionupdates, eliminated = board.do_player_movement(list(live_idnums.keys()))
          
            for msg in positionupdates:
              if msg.idnum not in eliminatedPlayer:
                broadcast_tokens(msg.pack())    
                board_moves.append(msg.pack())

            #Check for all eliminated players
            for id in eliminated:
              if id not in eliminatedPlayer:
                eliminatedPlayer.append(id)
                broadcast_eliminated(id)
                is_turn_broadcast[id] = False
            
            #Restart a new game if a game is finished
            if len(eliminatedPlayer) == len(live_idnums) -len(spec) - 1:
              print("This game is over, starting a new game.....")
              game_over = 1
              timer_turn = threading.Timer(3.0, Timeouts1)
              timer_turn.start()

              if game_restart_finsihed:
                break
          
            # start next turn
            if game_over != 1:
              idnum = nextTurn()
              broadcast_turn(clients_map[idnum])
      
            

# create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# listen on all network interfaces
server_address = ('', 30020)
print(sock.getsockname())

try:  
  sock.bind(server_address)
except socket.error as e:
  str(e)

print('listening on {}'.format(sock.getsockname()))

sock.listen()
print("Waiting for a connection, Server Started......")

while True:
  # handle each new connection independently
  connection, client_address = sock.accept() #Accept any connetions
  socks[currentPlayer] = connection
  thread = threading.Thread(target=client_handler, args= (connection, client_address, currentPlayer), daemon = True)
  thread.start()
  print('received connection from {}'.format(client_address))
  currentPlayer += 1
