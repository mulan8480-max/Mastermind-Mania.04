import streamlit as st
import random
import time
from streamlit_autorefresh import st_autorefresh

# 1. Trigger automatic background refresh every 1 second to keep the countdown accurate
st_autorefresh(interval=1000, key="gamerefresh")

st.title("🧩 Mastermind Mania")
st.caption("Multi-Mode Split-Screen Code Cracking Arena")

# 2. Setup Global Server Memory (Persists across devices)
@st.cache_resource(validate=None)
def get_global_server():
    return {} 

server = get_global_server()

# --- SIDEBAR: MATCHMAKING, SECURITY & IDENTITY ---
st.sidebar.header("🚪 Matchmaking & Security")

room_id = st.sidebar.text_input("Enter Room Code to Join:", value="Lobby").strip()
room_passcode = st.sidebar.text_input("Enter Lobby Passcode:", type="password", value="1234").strip()

# Initialize the room state inside server memory if it's completely new
if room_id not in server:
    server[room_id] = {
        "passcode": room_passcode if room_passcode else "1234",
        "game_mode": "Battle Mode (Crack Each Other)",
        "digits": 5,
        "p1_name": "Player 1",
        "p2_name": "Player 2",
        "p1_secret": None,
        "p2_secret": None,
        "server_secret": None,
        "p1_guesses": [],
        "p2_guesses": [],
        "turn": "Setup", # "Setup", "Player 1", "Player 2", "Race Active", "Game Over"
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
st.sidebar.header("👤 Your Identity")
st.sidebar.info(f"Connected to Room: **{room_id}**")

my_role = st.sidebar.radio("Who are you?", ["Observer", "Player 1", "Player 2"])

if my_role == "Player 1":
    game["p1_name"] = st.sidebar.text_input("Edit Your Name (P1):", value=game["p1_name"])
elif my_role == "Player 2":
    game["p2_name"] = st.sidebar.text_input("Edit Your Name (P2):", value=game["p2_name"])


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
if game["turn"] == "Race Active" and game["end_time"] is not None:
    time_left = max(0, int(game["end_time"] - time.time()))
    if time_left == 0 and not game["winner"]:
        game["winner"] = "Timeout"
        game["turn"] = "Game Over"
        st.rerun()


# --- MAIN SCREEN PHASE 1: LOBBY SETUP & CONFIGURATION ---
if game["turn"] == "Setup":
    st.subheader("⚙️ Step 1: Configure Match Settings & Keys")
    
    # Game rules selectors (Only accessible during setup)
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        game["game_mode"] = st.selectbox(
            "Select Game Mode:", 
            ["Battle Mode (Crack Each Other)", "Race Mode (Race the Clock)"]
        )
    with col_cfg2:
        game["digits"] = st.selectbox("Select Code Length:", [4, 5], index=1)

    st.markdown("---")

    # Mode A: Battle Setup (Players choice input)
    if game["game_mode"] == "Battle Mode (Crack Each Other)":
        st.warning(f"⚠️ Never share screens! Both players must input a unique {game['digits']}-digit code.")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"### 🔴 {game['p1_name']}")
            if game["p1_secret"] is not None:
                st.success("✅ Code safely locked!")
            elif my_role == "Player 1":
                p1_input = st.text_input(f"Create your secret {game['digits']}-digit code:", type="password", key="p1_set_input")
                if st.button("Lock Code (P1)", key="p1_lock_btn"):
                    if len(p1_input) == game["digits"] and len(set(p1_input)) == game["digits"] and p1_input.isdigit():
                        game["p1_secret"] = p1_input
                        st.success("Locked!")
                        st.rerun()
                    else:
                        st.error(f"Must be exactly {game['digits']} unique digits!")
            else:
                st.caption("⏳ Waiting for Player 1 to lock their code...")

        with col2:
            st.markdown(f"### 🔵 {game['p2_name']}")
            if game["p2_secret"] is not None:
                st.success("✅ Code safely locked!")
            elif my_role == "Player 2":
                p2_input = st.text_input(f"Create your secret {game['digits']}-digit code:", type="password", key="p2_set_input")
                if st.button("Lock Code (P2)", key="p2_lock_btn"):
                    if len(p2_input) == game["digits"] and len(set(p2_input)) == game["digits"] and p2_input.isdigit():
                        game["p2_secret"] = p2_input
                        st.success("Locked!")
                        st.rerun()
                    else:
                        st.error(f"Must be exactly {game['digits']} unique digits!")
            else:
                st.caption("⏳ Waiting for Player 2 to lock their code...")

        # Advance automatically for Battle Mode
        if game["p1_secret"] and game["p2_secret"]:
            game["turn"] = "Player 1"
            st.rerun()

    # Mode B: Race Setup (Server Generated)
    else:
        st.info(f"🏃 Race Mode: The server will generate a hidden {game['digits']}-digit code. The fastest player to solve it wins!")
        if st.button("🚀 Initialization Sequence: Start Race"):
            game["server_secret"] = generate_server_secret(game["digits"])
            # 3 minutes (180s) for 4-digits || 5 minutes (300s) for 5-digits
            duration = 300 if game["digits"] == 5 else 180
            game["end_time"] = time.time() + duration
            game["turn"] = "Race Active"
            st.rerun()


# --- MAIN SCREEN PHASE 2: ACTIVE GAME MODES ---
else:
    st.subheader("🎯 Step 2: Crack the Target Systems")
    
    # Global Display Headers for Winner or Ticking Clock
    if game["winner"]:
        if game["winner"] == "Timeout":
            st.error(f"🚨 GAME OVER! The countdown timer expired! Nobody cracked the code. The answer was: `{game['server_secret']}`")
        else:
            st.balloons()
            st.success(f"🎉 GAME OVER! **{game['winner']}** broke the firewall and won the game!")
    else:
        if game["turn"] == "Race Active":
            mins, secs = divmod(time_left, 60)
            st.metric("⏳ Absolute Global Time Remaining", f"{mins:02d}:{secs:02d}")
        else:
            current_turn_name = game["p1_name"] if game["turn"] == "Player 1" else game["p2_name"]
            st.info(f"⏳ Dynamic Turn Matrix: **{current_turn_name}**")

    col1, col2 = st.columns(2)

    # --- PLAYER 1 INTERACTIVE CONTAINER ---
    with col1:
        st.markdown(f"### 🔴 {game['p1_name']}'s Board")
        
        # Determine if Player 1 is authorized to input an assessment right now
        p1_can_act = False
        if not game["winner"]:
            if game["turn"] == "Player 1" and my_role == "Player 1":
                p1_can_act = True
            elif game["turn"] == "Race Active" and my_role == "Player 1":
                p1_can_act = True

        if p1_can_act:
            p1_guess = st.text_input(f"Enter your {game['digits']}-digit assessment:", max_chars=game["digits"], key="p1_assessment")
            if st.button("Submit Assessment (P1)", key="p1_sub_btn"):
                if len(p1_guess) == game["digits"] and len(set(p1_guess)) == game["digits"] and p1_guess.isdigit():
                    
                    # Logic branch based on game rules
                    if game["game_mode"] == "Race Mode (Race the Clock)":
                        b, c = get_bulls_and_cows(game["server_secret"], p1_guess)
                        game["p1_guesses"].append((p1_guess, b, c))
                        if b == game["digits"]:
                            game["winner"] = game["p1_name"]
                            game["turn"] = "Game Over"
                    else:
                        b, c = get_bulls_and_cows(game["p2_secret"], p1_guess)
                        game["p1_guesses"].append((p1_guess, b, c))
                        if b == game["digits"]:
                            game["winner"] = game["p1_name"]
                            game["turn"] = "Game Over"
                        else:
                            game["turn"] = "Player 2"
                    st.rerun()
                else:
                    st.error(f"Entry requires exactly {game['digits']} unique digits!")
        elif game["turn"] == "Player 2" and not game["winner"]:
            st.caption("Waiting for opponent's turn loop...")
        elif game["turn"] == "Race Active" and my_role != "Player 1" and not game["winner"]:
            st.caption("Synchronizing data feeds...")

        if game["p1_guesses"]:
            st.markdown("**History Log:**")
            for g, b, c in reversed(game['p1_guesses']):
                st.write(f"🔢 `{g}` ➡️ 🐂 **{b}** | 🐄 **{c}**")

    # --- PLAYER 2 INTERACTIVE CONTAINER ---
    with col2:
        st.markdown(f"### 🔵 {game['p2_name']}'s Board")
        
        # Determine if Player 2 is authorized to input an assessment right now
        p2_can_act = False
        if not game["winner"]:
            if game["turn"] == "Player 2" and my_role == "Player 2":
                p2_can_act = True
            elif game["turn"] == "Race Active" and my_role == "Player 2":
                p2_can_act = True

        if p2_can_act:
            p2_guess = st.text_input(f"Enter your {game['digits']}-digit assessment:", max_chars=game["digits"], key="p2_assessment")
            if st.button("Submit Assessment (P2)", key="p2_sub_btn"):
                if len(p2_guess) == game["digits"] and len(set(p2_guess)) == game["digits"] and p2_guess.isdigit():
                    
                    # Logic branch based on game rules
                    if game["game_mode"] == "Race Mode (Race the Clock)":
                        b, c = get_bulls_and_cows(game["server_secret"], p2_guess)
                        game["p2_guesses"].append((p2_guess, b, c))
                        if b == game["digits"]:
                            game["winner"] = game["p2_name"]
                            game["turn"] = "Game Over"
                    else:
                        b, c = get_bulls_and_cows(game["p1_secret"], p2_guess)
                        game["p2_guesses"].append((p2_guess, b, c))
                        if b == game["digits"]:
                            game["winner"] = game["p2_name"]
                            game["turn"] = "Game Over"
                        else:
                            game["turn"] = "Player 1"
                    st.rerun()
                else:
                    st.error(f"Entry requires exactly {game['digits']} unique digits!")
        elif game["turn"] == "Player 1" and not game["winner"]:
            st.caption("Waiting for opponent's turn loop...")
        elif game["turn"] == "Race Active" and my_role != "Player 2" and not game["winner"]:
            st.caption("Synchronizing data feeds...")

        if game["p2_guesses"]:
            st.markdown("**History Log:**")
            for g, b, c in reversed(game['p2_guesses']):
                st.write(f"🔢 `{g}` ➡️ 🐂 **{b}** | 🐄 **{c}**")

    # --- SYSTEM CLEANUP OPERATIONS ---
    st.markdown("---")
    if st.button("🔄 Dissolve & Reset Room"):
        server[room_id] = {
            "passcode": game["passcode"], # Retain room password settings
            "game_mode": game["game_mode"],
            "digits": game["digits"],
            "p1_name": game["p1_name"],
            "p2_name": game["p2_name"],
            "p1_secret": None,
            "p2_secret": None,
            "server_secret": None,
            "p1_guesses": [],
            "p2_guesses": [],
            "turn": "Setup",
            "end_time": None,
            "winner": None
        }
        st.rerun()
