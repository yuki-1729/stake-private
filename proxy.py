# LICENSE: GNU AGPL v3.0

import sys
sys.dont_write_bytecode = True

import os
import json
import yaml
import time
import uuid
import locale
import random
import secrets
import logging
import datetime

from utils.roll import Roller
from utils.mines import MinesCalc
from mitmproxy import http, ctx
from utils.generate import generate_value

# Disable Error
logging.getLogger("passlib").setLevel(logging.ERROR)

# Set Title
os.system("title StakePrivate")

# Config
with open("config.yml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# Websocket
wss = []
ws_bet_id = None
ws_bal_id = None
ws_vault_id = None

# Seed Pair
nonce = 0
current_server_seed = secrets.token_hex(32)
current_server_seed_id = str(uuid.uuid4())
current_client_seed = secrets.token_urlsafe(8)
current_client_seed_id = str(uuid.uuid4())
print("[INIT] Generated SeedPair")

# Next Seed Pair
next_server_seed = secrets.token_hex(32)
next_server_seed_id = str(uuid.uuid4())
next_client_seed_id = str(uuid.uuid4())
print("[INIT] Generated Next-SeedPair")

# Mines Data
mines_data = {}

# Init balance_available
balance_available = config["init"]
balance_vault = 0

locale.setlocale(locale.LC_TIME, "en_US.UTF-8")

def request(flow):
    # Global Data
    global nonce
    global balance_available
    global balance_vault

    # Seed Pair Data
    global current_server_seed
    global current_server_seed_id
    global current_client_seed
    global current_client_seed_id

    # Next Seed Pair Data
    global next_server_seed
    global next_server_seed_id
    global next_client_seed_id

    # Mines Data
    global mines_data

    if flow.request.pretty_url != "https://stake.com/_api/graphql":
        return
    
    query_param = flow.request.json().get("query")
    if query_param == None:
        return
    
    # Dice
    if query_param.startswith("mutation DiceRoll"):
        var_param = flow.request.json()["variables"]
        target = var_param["target"]
        condition = var_param["condition"]
        amount = var_param["amount"]
        identifier = var_param["identifier"]

        balance_available -= amount

        is_clear, result, multiplier, payout = Roller.roll({
            "server": current_server_seed,
            "client": current_client_seed,
            "nonce": nonce
        }, target, condition, amount)

        balance_available += payout

        nonce += 1

        bet_id = str(uuid.uuid4())
        bet_time = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

        response_payload = {
            "data": {
                "diceRoll": {
                    "id": bet_id,
                    "active": False,
                    "payoutMultiplier": multiplier,
                    "amountMultiplier": 1,
                    "amount": amount,
                    "payout": payout,
                    "updatedAt": bet_time,
                    "currency": "ltc",
                    "game": "dice",
                    "user": {
                        "id": config["id"],
                        "name": config["name"]
                    },
                    "state": {
                        "result": result,
                        "target": target,
                        "condition": condition
                    }
                }
            }
        }
        response = http.Response.make(
            200,
            json.dumps(response_payload),
            {"Content-Type": "application/json"}
        )
        
        time.sleep(config["time"])
        flow.response = response

        house_id = "".join([random.choice("0123456789") for i in range(12)])

        ws_bet_payload = {
            "id": ws_bet_id,
            "type": "next",
            "payload": {
                "data": {
                    "houseBets": {
                        "id": bet_id,
                        "iid": f"house:{house_id}",
                        "game": {
                            "name": "dice",
                            "icon": "stake-game-dice",
                            "__typename": "GameKuratorGame"
                        },
                        "bet": {
                            "__typename": "CasinoBet",
                            "id": bet_id,
                            "active": False,
                            "payoutMultiplier": multiplier,
                            "amountMultiplier": 1,
                            "amount": amount,
                            "payout": payout,
                            "updatedAt": bet_time,
                            "currency": "ltc",
                            "user": {
                                "id": config["id"],
                                "name": config["name"],
                                "preferenceHideBets": False,
                                "__typename": "User"
                            }
                        },
                        "__typename": "Bet"
                    }
                }
            }
        }

        ws_bal_payload = {
            "id": ws_bal_id,
            "type": "next",
            "payload": {
                "data": {
                    "availableBalances": {
                        "amount": amount if is_clear else amount*-1,
                        "identifier": identifier,
                        "balance": {
                            "amount": balance_available,
                            "currency": "ltc"
                        }
                    }
                }
            }
        }

        for ws in wss:
            ctx.master.commands.call("inject.websocket", ws, True, json.dumps(ws_bet_payload).encode())
            if amount > 0:
                ctx.master.commands.call("inject.websocket", ws, True, json.dumps(ws_bal_payload).encode())

    # Limbo
    elif query_param.startswith("mutation LimboBet"):
        var_param = flow.request.json()["variables"]
        target = var_param["multiplierTarget"]
        amount = var_param["amount"]
        identifier = var_param["identifier"]

        balance_available -= amount

        result = generate_value(current_server_seed, current_client_seed, nonce, "limbo")
        if result > target:
            is_clear = True
            multiplier = target
            payout = amount*multiplier
        else:
            is_clear = False
            multiplier = 0
            payout = 0

        balance_available += payout

        nonce += 1

        bet_id = str(uuid.uuid4())
        bet_time = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

        response_payload = {
            "data": {
                "limboBet": {
                    "id": bet_id,
                    "active": False,
                    "payoutMultiplier": multiplier,
                    "amountMultiplier": 2,
                    "amount": amount,
                    "payout": payout,
                    "updatedAt": bet_time,
                    "currency": "ltc",
                    "game": "limbo",
                    "user": {
                        "id": config["id"],
                        "name": config["name"]
                    },
                    "state": {
                        "result": result,
                        "multiplierTarget": target
                    }
                }
            }
        }
        response = http.Response.make(
            200,
            json.dumps(response_payload),
            {"Content-Type": "application/json"}
        )
        
        time.sleep(config["time"])
        flow.response = response

        house_id = "".join([random.choice("0123456789") for i in range(12)])

        ws_bet_payload = {
            "id": ws_bet_id,
            "type": "next",
            "payload": {
                "data": {
                    "houseBets": {
                        "id": bet_id,
                        "iid": f"house:{house_id}",
                        "game": {
                            "name": "limbo",
                            "icon": "stake-game-limbo",
                            "__typename": "GameKuratorGame"
                        },
                        "bet": {
                            "__typename": "CasinoBet",
                            "id": bet_id,
                            "active": False,
                            "payoutMultiplier": multiplier,
                            "amountMultiplier": 1,
                            "amount": amount,
                            "payout": payout,
                            "updatedAt": bet_time,
                            "currency": "ltc",
                            "user": {
                                "id": config["id"],
                                "name": config["name"],
                                "preferenceHideBets": False,
                                "__typename": "User"
                            }
                        },
                        "__typename": "Bet"
                    }
                }
            }
        }

        ws_bal_payload = {
            "id": ws_bal_id,
            "type": "next",
            "payload": {
                "data": {
                    "availableBalances": {
                        "amount": amount if is_clear else amount*-1,
                        "identifier": identifier,
                        "balance": {
                            "amount": balance_available,
                            "currency": "ltc"
                        }
                    }
                }
            }
        }

        for ws in wss:
            ctx.master.commands.call("inject.websocket", ws, True, json.dumps(ws_bet_payload).encode())
            if amount > 0:
                ctx.master.commands.call("inject.websocket", ws, True, json.dumps(ws_bal_payload).encode())

    # Mines
    elif query_param.startswith("mutation MinesBet") or query_param.startswith("mutation MinesNext") or query_param.startswith("mutation MinesCashout") or query_param.startswith("query MinesActiveBet"):
        if query_param.startswith("mutation MinesBet"):
            var_param = flow.request.json()["variables"]
            amount = var_param["amount"]
            bomb = var_param["minesCount"]

            balance_available -= amount

            mines_data["amount"] = amount

            mines_data["mines"] = []
            mines_data["rounds"] = []

            fields = []
            for i in range(25):
                fields.append(i)

            random.seed(f"{current_server_seed}:{current_client_seed}:{nonce}")
            for i in range(bomb):
                bomb_field = random.choice(fields)
                mines_data["mines"].append(bomb_field)
                fields.remove(bomb_field)

            nonce += 1

            mines_data["id"] = str(uuid.uuid4())

            response_payload = {
                "data": {
                    "minesBet": {
                        "id": mines_data["id"],
                        "active": True,
                        "payoutMultiplier": 0,
                        "amountMultiplier": 1,
                        "amount": amount,
                        "payout": 0,
                        "updatedAt": datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                        "currency": "ltc",
                        "game": "mines",
                        "user": {
                            "id": config["id"],
                            "name": config["name"]
                        },
                        "state": {
                            "mines": None,
                            "minesCount": bomb,
                            "rounds": []
                        }
                    }
                }
            }
            response = http.Response.make(
                200,
                json.dumps(response_payload),
                {"Content-Type": "application/json"}
            )

            time.sleep(config["time"])
            flow.response = response

            ws_bal_payload = {
                "id": ws_bal_id,
                "type": "next",
                "payload": {
                    "data": {
                        "availableBalances": {
                            "amount": amount*-1,
                            "identifier": "",
                            "balance": {
                                "amount": balance_available,
                                "currency": "ltc"
                            }
                        }
                    }
                }
            }

            for ws in wss:
                if amount > 0:
                    ctx.master.commands.call("inject.websocket", ws, True, json.dumps(ws_bal_payload).encode())
        elif query_param.startswith("mutation MinesNext"):
            var_param = flow.request.json()["variables"]
            selected_fields = var_param["fields"]

            for field in selected_fields:
                multiplier = MinesCalc.calc_multiplier(len(mines_data["mines"]), len(mines_data["rounds"]) + 1)
                if field in mines_data["mines"]:
                    multiplier = 0

                try:
                    if mines_data["rounds"][-1]["payoutMultiplier"] == 0:
                        multiplier = 0
                except:
                    pass

                mines_data["rounds"].append({
                    "field": field,
                    "payoutMultiplier": multiplier
                })

            response_payload = {
                "data": {
                    "minesNext": {
                        "id": mines_data["id"],
                        "active": False if mines_data["rounds"][-1]["payoutMultiplier"] == 0 else True,
                        "payoutMultiplier": multiplier,
                        "amountMultiplier": 1,
                        "amount": mines_data["amount"],
                        "payout": mines_data["amount"]*multiplier,
                        "updatedAt": datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                        "currency": "ltc",
                        "game": "mines",
                        "user": {
                            "id": config["id"],
                            "name": config["name"]
                        },
                        "state": {
                            "mines": mines_data["mines"] if mines_data["rounds"][-1]["payoutMultiplier"] == 0 else None,
                            "minesCount": len(mines_data["mines"]),
                            "rounds": mines_data["rounds"]
                        }
                    }
                }
            }
            response = http.Response.make(
                200,
                json.dumps(response_payload),
                {"Content-Type": "application/json"}
            )

            time.sleep(config["time"])
            flow.response = response
        elif query_param.startswith("mutation MinesCashout"):
            var_param = flow.request.json()["variables"]
            identifier = var_param["identifier"]

            multiplier = MinesCalc.calc_multiplier(len(mines_data["mines"]), len(mines_data["rounds"]))

            balance_available += mines_data["amount"]*multiplier

            response_payload = {
                "data": {
                    "minesCashout": {
                        "id": mines_data["id"],
                        "active": False,
                        "payoutMultiplier": multiplier,
                        "amountMultiplier": 1,
                        "amount": mines_data["amount"],
                        "payout": mines_data["amount"]*multiplier,
                        "updatedAt": datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                        "currency": "ltc",
                        "game": "mines",
                        "user": {
                            "id": config["id"],
                            "name": config["name"]
                        },
                        "state": {
                            "mines": mines_data["mines"],
                            "minesCount": len(mines_data["mines"]),
                            "rounds": mines_data["rounds"]
                        }
                    }
                }
            }
            response = http.Response.make(
                200,
                json.dumps(response_payload),
                {"Content-Type": "application/json"}
            )

            time.sleep(config["time"])
            flow.response = response

            house_id = "".join([random.choice("0123456789") for i in range(12)])

            ws_bet_payload = {
                "id": ws_bet_id,
                "type": "next",
                "payload": {
                    "data": {
                        "houseBets": {
                            "id": mines_data["id"],
                            "iid": f"house:{house_id}",
                            "game": {
                                "name": "mines",
                                "icon": "stake-game-mines",
                                "__typename": "GameKuratorGame"
                            },
                            "bet": {
                                "__typename": "CasinoBet",
                                "id": mines_data["id"],
                                "active": False,
                                "payoutMultiplier": multiplier,
                                "amountMultiplier": 1,
                                "amount": mines_data["amount"],
                                "payout": mines_data["amount"]*multiplier,
                                "updatedAt": datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                                "currency": "ltc",
                                "user": {
                                    "id": config["id"],
                                    "name": config["name"],
                                    "preferenceHideBets": False,
                                    "__typename": "User"
                                }
                            },
                            "__typename": "Bet"
                        }
                    }
                }
            }

            ws_bal_payload = {
                "id": ws_bal_id,
                "type": "next",
                "payload": {
                    "data": {
                        "availableBalances": {
                            "amount": mines_data["amount"]*multiplier if mines_data["rounds"][-1]["payoutMultiplier"] else mines_data["amount"]*-1,
                            "identifier": identifier,
                            "balance": {
                                "amount": balance_available,
                                "currency": "ltc"
                            }
                        }
                    }
                }
            }

            for ws in wss:
                ctx.master.commands.call("inject.websocket", ws, True, json.dumps(ws_bet_payload).encode())
                if mines_data["amount"] > 0:
                    ctx.master.commands.call("inject.websocket", ws, True, json.dumps(ws_bal_payload).encode())

            mines_data = {}
        elif query_param.startswith("query MinesActiveBet"):
            if mines_data.get("id") == None:
                response_payload = {
                    "data": {
                        "user": {
                            "id": config["id"],
                            "activeCasinoBet": None
                        }
                    }
                }

                response = http.Response.make(
                    200,
                    json.dumps(response_payload),
                    {"Content-Type": "application/json"}
                )

                time.sleep(config["time"])
                flow.response = response
            else:
                multiplier = MinesCalc.calc_multiplier(len(mines_data["mines"]), len(mines_data["rounds"]))

                response_payload = {
                    "data": {
                        "user": {
                            "id": config["id"],
                            "activeCasinoBet": {
                                "id": mines_data["id"],
                                "active": True,
                                "payoutMultiplier": multiplier,
                                "amountMultiplier": 0,
                                "amount": mines_data["amount"],
                                "payout": mines_data["amount"]*multiplier,
                                "updatedAt": datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                                "currency": "ltc",
                                "game": "mines",
                                "user": {
                                    "id": config["id"],
                                    "name": config["name"]
                                },
                                "state": {
                                    "mines": None,
                                    "minesCount": len(mines_data["mines"]),
                                    "rounds": mines_data["rounds"]
                                }
                            }
                        }
                    }
                }

                response = http.Response.make(
                    200,
                    json.dumps(response_payload),
                    {"Content-Type": "application/json"}
                )

                time.sleep(config["time"])
                flow.response = response

    # Misc
    elif query_param.startswith("query UserSeedPair"):
        response_payload = {
            "data": {
                "user": {
                    "id": config["id"],
                    "activeClientSeed": {
                        "id": current_client_seed_id,
                        "seed": current_client_seed,
                        "__typename": "CasinoClientSeed"
                    },
                    "activeServerSeed": {
                        "id": current_server_seed_id,
                        "nonce": nonce,
                        "seedHash": current_server_seed,
                        "nextSeedHash": next_server_seed,
                        "__typename": "CasinoServerSeed"
                    },
                    "activeCasinoBets": [],
                    "__typename": "User"
                }
            }
        }
        response = http.Response.make(
            200,
            json.dumps(response_payload),
            {"Content-Type": "application/json"}
        )

        time.sleep(config["time"])
        flow.response = response
    elif query_param.startswith("mutation RotateSeedPair"):
        var_param = flow.request.json()["variables"]
        new_client_seed = var_param["seed"]

        current_server_seed = next_server_seed
        current_server_seed_id = next_server_seed_id

        current_client_seed = new_client_seed
        current_server_seed_id = next_client_seed_id

        nonce = 0
        next_server_seed = secrets.token_hex(32)
        next_server_seed_id = str(uuid.uuid4())
        next_client_seed_id = str(uuid.uuid4())

        response_payload = {
            "data": {
                "rotateSeedPair": {
                    "clientSeed": {
                        "user": {
                            "id": config["id"],
                            "activeClientSeed": {
                                "id": current_client_seed_id,
                                "seed": current_client_seed,
                                "__typename": "CasinoClientSeed"
                            },
                            "activeServerSeed": {
                                "id": current_server_seed_id,
                                "nonce": nonce,
                                "seedHash": current_server_seed,
                                "nextSeedHash": next_server_seed,
                                "__typename": "CasinoServerSeed"
                            },
                            "__typename": "User"
                        },
                        "__typename": "CasinoClientSeed"
                    },
                    "__typename": "CasinoSeedPair"
                }
            }
        }

        response = http.Response.make(
            200,
            json.dumps(response_payload),
            {"Content-Type": "application/json"}
        )

        time.sleep(config["time"])
        flow.response = response
    elif query_param.startswith("mutation ClaimRakeback"):
        response_payload = {
            "data": {
                "claimRakeback": {
                    "id": str(uuid.uuid4()),
                    "currency": "ltc",
                    "amount": 10,
                    "__typename": "RakebackTransaction"
                }
            }
        }
        response = http.Response.make(
            200,
            json.dumps(response_payload),
            {"Content-Type": "application/json"}
        )

        balance_available += 10

        time.sleep(config["time"])
        flow.response = response

        ws_payload = {
            "id": ws_bal_id,
            "type": "next",
            "payload": {
                "data": {
                    "availableBalances": {
                        "amount": 10,
                        "identifier": "",
                        "balance": {
                            "amount": balance_available,
                            "currency": "ltc"
                        }
                    }
                }
            }
        }
        
        for ws in wss:
            ctx.master.commands.call("inject.websocket", ws, True, json.dumps(ws_payload).encode())
    elif query_param.startswith("query UserBalances"):
        with open("preset\\balances.txt", "r", encoding="utf-8", errors="ignore") as file:
            base_response = file.read()

        response_payload = base_response.replace("%UID%", config["id"]).replace("%AVAILABLE%", str(balance_available)).replace("%VAULT%", str(balance_vault))
        response = http.Response.make(
            200,
            response_payload,
            {"Content-Type": "application/json"}
        )

        time.sleep(config["time"])
        flow.response = response
    elif query_param.startswith("mutation CreateVaultDeposit"):
        var_param = flow.request.json()["variables"]
        amount = var_param["amount"]

        balance_available -= amount
        balance_vault += amount

        with open("preset\\deposit.txt", "r", encoding="utf-8", errors="ignore") as file:
            base_response = file.read()

        response_payload = base_response.replace("%ID%", str(uuid.uuid4())).replace("%UID%", config["id"]).replace("%AVAILABLE%", str(balance_available)).replace("%VAULT%", str(balance_vault))
        response = http.Response.make(
            200,
            response_payload,
            {"Content-Type": "application/json"}
        )

        time.sleep(config["time"])
        flow.response = response

        ws_available_payload = {
            "id": ws_bal_id,
            "payload": {
                "data": {
                    "availableBalances": {
                        "amount": amount*-1,
                        "balance": {
                            "amount": balance_available,
                            "currency": "ltc"
                        },
                        "identifier": ""
                    }
                }
            },
            "type": "next"
        }

        ws_vault_payload = {
            "id": ws_vault_id,
            "payload": {
                "data": {
                    "vaultBalances": {
                        "amount": amount,
                        "balance": {
                            "amount": balance_vault,
                            "currency": "ltc"
                        },
                        "identifier": ""
                    }
                }
            },
            "type": "next"
        }

        for ws in wss:
            ctx.master.commands.call("inject.websocket", ws, True, json.dumps(ws_available_payload).encode())
            ctx.master.commands.call("inject.websocket", ws, True, json.dumps(ws_vault_payload).encode())
    elif query_param.startswith("mutation CreateVaultWithdrawal"):
        var_param = flow.request.json()["variables"]
        amount = var_param["amount"]

        balance_available += amount
        balance_vault -= amount

        with open("preset\\withdrawal.txt", "r", encoding="utf-8", errors="ignore") as file:
            base_response = file.read()

        response_payload = base_response.replace("%ID%", str(uuid.uuid4())).replace("%UID%", config["id"]).replace("%EMAIL%", config["email"]).replace("%AVAILABLE%", str(balance_available)).replace("%VAULT%", str(balance_vault))
        response = http.Response.make(
            200,
            response_payload,
            {"Content-Type": "application/json"}
        )

        time.sleep(config["time"])
        flow.response = response

        ws_available_payload = {
            "id": ws_bal_id,
            "payload": {
                "data": {
                    "availableBalances": {
                        "amount": amount,
                        "balance": {
                            "amount": balance_available,
                            "currency": "ltc"
                        },
                        "identifier": ""
                    }
                }
            },
            "type": "next"
        }

        ws_vault_payload = {
            "id": ws_vault_id,
            "payload": {
                "data": {
                    "vaultBalances": {
                        "amount": amount*-1,
                        "balance": {
                            "amount": balance_vault,
                            "currency": "ltc"
                        },
                        "identifier": ""
                    }
                }
            },
            "type": "next"
        }

        for ws in wss:
            ctx.master.commands.call("inject.websocket", ws, True, json.dumps(ws_available_payload).encode())
            ctx.master.commands.call("inject.websocket", ws, True, json.dumps(ws_vault_payload).encode())
    elif query_param.startswith("query VipNavMeta"):
        response_payload = {
            "data": {
                "user": {
                    "id": config["id"],
                    "faucet": {
                        "active": False
                    },
                    "rakeback": {
                        "enabled": True
                    },
                    "flags": [],
                    "activeRollovers": []
                },
                "activeRaffles": []
            }
        }
        response = http.Response.make(
            200,
            json.dumps(response_payload),
            {"Content-Type": "application/json"}
        )

        time.sleep(config["time"])
        flow.response = response
    elif query_param.startswith("query AvailableRakeback"):
        response_payload = {
            "data": {
                "user": {
                    "id": config["id"],
                    "rakeback": {
                        "balances": [
                            {
                                "currency": "ltc",
                                "amount": 10
                            }
                        ]
                    }
                }
            }
        }
        response = http.Response.make(
            200,
            json.dumps(response_payload),
            {"Content-Type": "application/json"}
        )

        time.sleep(config["time"])
        flow.response = response

def websocket_start(flow):
    global wss
    wss.append(flow)

def websocket_message(flow):
    global ws_bet_id
    global ws_bal_id
    global ws_vault_id

    message = flow.websocket.messages[-1]

    if not message.is_text:
        return
    
    try:
        payload = json.loads(message.text)
    except:
        return

    if payload.get("type") != "subscribe":
        return
    
    if payload["payload"]["query"].startswith("subscription HouseBets"):
        ws_bet_id = payload["id"]
        print(f"[WS] HouseBets Event Registered: {ws_bet_id}")
    elif payload["payload"]["query"].startswith("subscription AvailableBalances"):
        ws_bal_id = payload["id"]
        print(f"[WS] AvailableBalances Event Registered: {ws_bal_id}")
    elif payload["payload"]["query"].startswith("subscription VaultBalances"):
        ws_vault_id = payload["id"]
        print(f"[WS] VaultBalances Event Registered: {ws_vault_id}")

# (C) 2024 yuki-1729