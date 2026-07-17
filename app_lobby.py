import streamlit as st
import random
import time
from streamlit_autorefresh import st_autorefresh

# 1. Trigger automatic background refresh every 1 second to keep clocks and players synced
st_autorefresh(interval=1000, key="gamerefresh")

st.title("🧩 Mastermind Mania: Mass Multiplayer Edition")
st.caption("Crack codes together in real-time rooms")

# 2. Setup Global Server Memory (Persists across devices)
@st.cache_resource(validate=None)
def get_global_server():
    return {} 

server = get_global_server()

# --- SIDEBAR: MATCHMAKING, SECURITY & IDENTITY ---
st.sidebar.header("🚪 Matchmaking & Security")

room_id = st.sidebar.text_input("Enter Room Code to Join:", value="Lobby").strip()
room_passcode = st.sidebar.text_input("Enter Lobby Passcode:", type="password", value="1234").strip()

# Initialize the dynamic room state inside server memory if it's completely new
if room_id not in server:
    server[room_id] = {
        "passcode": room_passcode if room_passcode else "1234",
        "game_mode": "Race Mode (Race the Clock)",
        "digits": 5,
        "players": {},       # Dynamic Dict: {"PlayerName": {"secret": None, "guesses": []}}
        "turn_order": [],    # Keeps track of player sequence for Battle Mode
        "current_idx": 0,    # Tracks index of whose turn it is in Battle Mode
        "server_secret": None,
        "turn": "Setup",     # "Setup", "Active", "Game Over"
        "end_time": None,
        "winner": None
    }

game = server[room_id]

# Security Guard: Instantly stop unauthorized players from entering or interrupting
if game["passcode"] != room_passcode:
    st.sidebar.error("🔒 Incorrect passcode for this lobby!")
    st.error("🔒 Access Denied: Please provide the correct passcode in the sidebar to enter this match room.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.header("👤 Player Identity")
st.sidebar.info(f"Room: **{room_id}** | Mode: **{game['game_mode']}**")

# Dynamic Registration Input
player_name = st.sidebar.text_input("Enter Your Name:", value="", max_chars=12).strip()

if player_name:
    if player_name not in game["players"]:
        if game["turn"] == "Setup":
            if st.sidebar.button(f"🚪 Join Lobby as '{player_name}'"):
                game["players"][player_name] = {"secret": None, "guesses": []}
                st.sidebar.success(f"Successfully joined!")
                st.rerun()
        else:
            st.sidebar.info("👀 Match already active. You are spectating as an Observer.")
    else:
        st.sidebar.success(f"🟢 Active Session: **{player_name}**")
else:
    st.sidebar.warning("⚠️ Type your name to join or play.")

# Display all connected lobby members dynamically
if game["players"]:
    st.sidebar.markdown("### 👥 Connected Players:")
    for p in game["players"]:
        status = "✅ Ready" if (game["game_mode"] == "Race Mode (Race the Clock)" or game["players"][p]["secret"]) else "⏳ Choosing Code..."
        st.sidebar.write(f"- **{p}** ({status})")


# Helper function to calculate Bulls and Cows
def get_bulls_and_cows(secret, guess):
    bulls = sum(1 for s, g in zip(secret, guess) if s == g)
    cows = sum(1 for g in guess if g in secret) - bulls
    return bulls, cows

# Helper to generate neutral server codes for Race Mode
def generate_server_secret(num_digits):
    return "".join(random.sample("0123456789", num_digits))


# --- TIMING SYSTEM MECHANICS (RACE MODE ONLY) ---
time_left = 0
if game["turn"] == "Active" and game["game_mode"] == "Race Mode (Race the Clock)" and game["end_time"] is not None:
    time_left = max(0, int(game["end_time"] - time.time()))
    if time_left == 0 and not game["winner"]:
        game["winner"] = "Timeout"
        game["turn"] = "Game Over"
        st.rerun()


# --- MAIN SCREEN PHASE 1: LOBBY SETUP & CONFIGURATION ---
if game["turn"] == "Setup":
    st.subheader("⚙️ Step 1: Configure Match Settings")
    
    # Configuration options are visible to anyone in setup, but lockable when match starts
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        game["game_mode"] = st.selectbox(
            "Select Game Mode:", 
            ["Race Mode (Race the Clock)", "Battle Mode (Loop Challenge)"]
        )
    with col_cfg2:
        game["digits"] = st.selectbox("Select Code Length:", [4, 5], index=1)

    st.markdown("---")

    # Mode A: Battle Setup (Every player inputs their custom code)
    if game["game_mode"] == "Battle Mode (Loop Challenge)":
        st.warning(f"🔒 **Battle Mode active:** Enter a secret {game['digits']}-digit sequence. Keep your screen hidden!")
        
        if player_name in game["players"]:
            my_data = game["players"][player_name]
            if my_data["secret"] is not None:
                st.success("✅ Your secret code is locked in! Waiting for other participants.")
            else:
                secret_input = st.text_input(f"Create your firewall passkey ({game['digits']} unique digits):", type="password")
                if st.button("Lock Passkey"):
                    if len(secret_input) == game["digits"] and len(set(secret_input)) == game["digits"] and secret_input.isdigit():
                        my_data["secret"] = secret_input
                        st.success("Passkey secured!")
                        st.rerun()
                    else:
                        st.error(f"Error: Passkey must be exactly {game['digits']} completely unique digits.")
        else:
            st.caption("Please register in the sidebar to set a code and participate.")

        # Master Start Condition for Battle Mode (Min 2 players, all must lock codes)
        all_ready = len(game["players"]) >= 2 and all(p["secret"] is not None for p in game["players"].values())
        if all_ready:
            if st.button("🚀 Start Multiplayer Battle Arena"):
                game["turn_order"] = list(game["players"].keys())
                random.shuffle(game["turn_order"]) # Shuffle turn sequence for fun randomness
                game["current_idx"] = 0
                game["turn"] = "Active"
                st.rerun()

    # Mode B: Race Setup (Server Generated - Everyone plays instantly)
    else:
        st.info(f"🏃 **Race Mode active:** The server will generate a random {game['digits']}-digit key. Everyone plays at the same time!")
        if len(game["players"]) >= 1:
            if st.button("🚀 Launch Live Code Race"):
                game["server_secret"] = generate_server_secret(game["digits"])
                duration = 300 if game["digits"] == 5 else 180
                game["end_time"] = time.time() + duration
                game["turn"] = "Active"
                st.rerun()
        else:
            st.caption("Waiting for at least one player to join the room before starting.")


# --- MAIN SCREEN PHASE 2: ACTIVE GAME MODES ---
else:
    st.subheader("🎯 Step 2: Break the Firewall")
    
    # End-game display states
    if game["winner"]:
        if game["winner"] == "Timeout":
            st.error(f"🚨 GAME OVER! Time ran out. Nobody cracked the system firewall! The master code was: `{game['server_secret']}`")
        else:
            st.balloons()
            st.success(f"🏆 VICTORY achieved! **{game['winner']}** successfully cracked the target code!")
    else:
        # Live HUD layouts
        if game["game_mode"] == "Race Mode (Race the Clock)":
            mins, secs = divmod(time_left, 60)
            st.metric("⏳ Room Countdown Timer", f"{mins:02d}:{secs:02d}")
            st.info("⚡ Real-time processing: Submit codes as fast as you can compute them!")
        else:
            active_p = game["turn_order"][game["current_idx"]]
            target_idx = (game["current_idx"] + 1) % len(game["turn_order"])
            target_p = game["turn_order"][target_idx]
            st.info(f"⏳ Current Turn: **{active_p}** ➡️ Targeting: **{target_p}**'s system!")

    st.markdown("---")

    # --- RENDER PERSONAL PLAYER ACTION AREA ---
    if player_name in game["players"] and not game["winner"]:
        can_guess = False
        target_secret = None
        current_target_name = "Server"

        if game["game_mode"] == "Race Mode (Race the Clock)":
            can_guess = True
            target_secret = game["server_secret"]
        elif game["game_mode"] == "Battle Mode (Loop Challenge)" and player_name == game["turn_order"][game["current_idx"]]:
            can_guess = True
            # Target the next person in the loop
            t_idx = (game["current_idx"] + 1) % len(game["turn_order"])
            current_target_name = game["turn_order"][t_idx]
            target_secret = game["players"][current_target_name]["secret"]

        if can_guess:
            st.markdown(f"### ⌨️ Your Input Dashboard (Targeting: **{current_target_name}**)")
            guess_input = st.text_input(f"Enter your {game['digits']}-digit assessment:", max_chars=game["digits"], key=f"guess_{player_name}")
            
            if st.button("Submit Assessment Check"):
                if len(guess_input) == game["digits"] and len(set(guess_input)) == game["digits"] and guess_input.isdigit():
                    b, c = get_bulls_and_cows(target_secret, guess_input)
                    
                    # Record the guess history tracking structure
                    game["players"][player_name]["guesses"].append({
                        "guess": guess_input, "bulls": b, "cows": c, "target": current_target_name
                    })
                    
                    # Victory verification
                    if b == game["digits"]:
                        game["winner"] = player_name
                        game["turn"] = "Game Over"
                    else:
                        # Advance turns if it is Battle Mode
                        if game["game_mode"] == "Battle Mode (Loop Challenge)":
                            game["current_idx"] = (game["current_idx"] + 1) % len(game["turn_order"])
                    st.rerun()
                else:
                    st.error(f"Assessments must contain exactly {game['digits']} unique digits.")
        else:
            if game["game_mode"] == "Battle Mode (Loop Challenge)":
                st.caption(f"🔒 Waiting for **{game['turn_order'][game['current_idx']]}** to complete their calculations...")
    elif player_name not in game["players"]:
        st.caption("📺 Spectator Mode: Watching live arena telemetry feeds...")

    # --- ARENA BATTLE LOGS (Dynamic Tab Structure for N-Players) ---
    st.markdown("---")
    st.subheader("📊 Global Arena History Logs")
    
    if game["players"]:
        player_tabs = st.tabs(list(game["players"].keys()))
        for idx, p_name in enumerate(game["players"]):
            with player_tabs[idx]:
                p_data = game["players"][p_name]
                
                # Vault key visibility rules
                if game["game_mode"] == "Battle Mode (Loop Challenge)":
                    if game["winner"] or p_name == player_name:
                        st.markdown(f"🔑 Private System Key: `{p_data['secret']}`")
                    else:
                        st.markdown("🔑 Private System Key: `•••••` (Hidden)")
                
                # Render Guess Records Dynamically
                if p_data["guesses"]:
                    for attempt in reversed(p_data["guesses"]):
                        target_str = f"Target: `{attempt['target']}` ➡️ " if game["game_mode"] == "Battle Mode (Loop Challenge)" else ""
                        st.write(f"🔢 {target_str}Guess: `{attempt['guess']}` ➡️ 🐂 Bulls: **{attempt['bulls']}** | 🐄 Cows: **{attempt['cows']}**")
                else:
                    st.caption("No entry computations processed yet.")

    # --- GLOBAL SYSTEM RESET OPERATIONS ---
    st.markdown("---")
    if st.button("🔄 Dissolve Room State & Reframe Lobby"):
        server[room_id] = {
            "passcode": game["passcode"], # Retain room password settings
            "game_mode": game["game_mode"],
            "digits": game["digits"],
            "players": {},
            "turn_order": [],
            "current_idx": 0,
            "server_secret": None,
            "turn": "Setup",
            "end_time": None,
            "winner": None
        }
        st.rerun()
