from dhooks import Webhook, Embed
from colorama import Fore
from pathlib import Path
from skinpy import Skin
from io import BytesIO
from PIL import Image
import requests
import base64
import time
import json
import re
import os

# Makes the skin folder be written in the same folder that the script is in
os.chdir(Path(__file__).parent)

firstSend = True
senderIgn = ""

settingsList = {}
settingIndex = 0
settingsFile = open(Path(__file__).with_name("settings.txt"), "r")
settingsLines = settingsFile.readlines()
for line in settingsLines:
    line = line.strip()
    settingPart = settingsLines[settingIndex].partition("=")
    settingsList[settingPart[0].format(line)] = settingPart[2].strip()
    settingIndex += 1

hook = Webhook(settingsList["webhookUrl"])
bridgeBotIgn = settingsList["bridgeBotIgn"]

def strip_colors(text: str) -> str:
    return re.sub(r"[§].", "", text)

def getSkin(playerIgn, outputFile):
    print("[DEBUG] fetching skin")

    folder = os.path.dirname(outputFile)
    if folder:  # only make dirs if folder is not empty
        os.makedirs(folder, exist_ok=True)

    # Fetch uuid from ign
    uuidUrl = f"https://api.mojang.com/users/profiles/minecraft/{playerIgn}"
    req_uuid = requests.get(uuidUrl)
    if req_uuid.status_code != 200:
        print(Fore.RED + f"| ERROR: Couldn't find '{playerIgn}' (under getSkin({playerIgn}) -> req_uuid fetch status_code != 200-)")
        raise Exception(f"Username '{playerIgn} not found!'")
    sender_uuid = req_uuid.json()["id"]

    # Fetch skin data (base64 encoded)
    profileUrl = f"https://sessionserver.mojang.com/session/minecraft/profile/{sender_uuid}"
    req_profile = requests.get(profileUrl)
    if req_profile.status_code != 200:
        print(Fore.RED + f"| ERROR: Couldn't fetch skin data (under getSkin({playerIgn}) -> req_profile fetch status_code != 200-)")
        raise Exception("Could not fetch skin data!")
    sender_properties = req_profile.json()["properties"][0]

    # Decode base64
    textureData = base64.b64decode(sender_properties["value"]).decode("utf-8")

    # Fetch skin URL
    texture_json = json.loads(textureData)
    skinUrl = texture_json["textures"]["SKIN"]["url"]
    skinFetchImage = requests.get(skinUrl)
    skin_img = Image.open(BytesIO(skinFetchImage.content))

    # Crop head 1st and 2nd layer
    headL1 = skin_img.crop((8, 8, 16, 16)).convert("RGBA")
    headL2 = skin_img.crop((40, 8, 48, 16)).convert("RGBA")
    headL1.paste(headL2, (0, 0), headL2)

    headFinal = headL1.resize((128, 128), Image.NEAREST)
    headFinal.save(outputFile)


while True:
    try:
        with open(settingsList["latestlogPath"].strip(), encoding="utf-8", errors="ignore") as logLatest:
            for line in logLatest:
                pass  # get last line in file

            # Only store first line to compare later
            if firstSend:
                lineStore = line
                firstSend = False

            if line != lineStore and not firstSend:
                if "[CHAT]" in line:
                    lineStore = line

                    # Extract chat message after [CHAT] and strip colors
                    chat_msg = strip_colors(line.split("[CHAT]", 1)[1]).strip()

                    print(Fore.CYAN + "| Chat > " + Fore.WHITE + chat_msg)

                    # Manage cooldown to avoid rate limits
                    if chat_msg.startswith("Guild > ") and chat_msg.endswith("joined.") and "[" not in chat_msg:
                        joinIgn = chat_msg.partition("> ")[2].partition(" joined.")[0]
                        print(f"[DEBUG] downloading {joinIgn}'s new skin")
                        getSkin(joinIgn, f"./skins/{joinIgn}.png")
                        
                    if chat_msg.startswith("Guild > ") and ":" in chat_msg:
                        print(Fore.GREEN + "| Detected guild message".strip())
                        print("| '" + chat_msg + "'" + Fore.WHITE)

                        if chat_msg.startswith("Guild > ") and len(chat_msg) > 8 and chat_msg[8] != "[":
                            messagePartNR = chat_msg.partition("> ")
                            print(f"[DEBUG] {messagePartNR}")
                            senderIgn = messagePartNR[2].partition(" ")[0]
                            print(f"[DEBUG] {senderIgn}")
                        else:
                            messagePart = chat_msg.partition("] ")
                            senderIgn = messagePart[2].partition(" ")[0]

                        if os.path.exists(f"./skins/{senderIgn}.png"):
                            pass
                        else:
                            getSkin(senderIgn, f"./skins/{senderIgn}.png")

                        with open(f"./skins/{senderIgn}.png", "rb") as f:
                            pfp = f.read()

                        hook.modify(name=f"{senderIgn}", avatar=pfp)

                        dcMessage = chat_msg.partition(": ")[2]

                        embed = Embed(
                            color=0x28703C,
                            timestamp="now"
                        )

                        embed.set_footer(text="Made by SnowyFranzz")
                        embed.add_field(name=f"{dcMessage}", value="")

                        hook.send(embed=embed)

            else:
                pass

    except FileNotFoundError:
        print(Fore.RED + "| Couldn't find file! Are you sure the path to your latest.log is right?")
        time.sleep(10)
        pass