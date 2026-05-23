import streamlit as st
import time
from streamlit_autorefresh import st_autorefresh

# 1. Background refresh every 1 second to keep the global clock ticking accurately
st_autorefresh(interval=1000, key="timer_refresh")

st.title("🧩 Mastermind Mania: Multi-Lobby Edition")

# HTML5/JavaScript Audio Generator (Plays a system beep when time gets critical)
def play_sound_alert():
    sound_html = """
    <audio autoplay>
        <source src="data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==\n" type="audio/wav">
    </audio>
    <script>
    var context = new (window.AudioContext || window.webkitAudioContext)();
    var osc = context.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, context.currentTime); // High pitch beep
    osc.connect(context.destination);
    osc.start();
    setTimeout(() => { osc.stop(); }, 150); // Beep duration 150ms
    </script>
    """
    st.components.v1.html(sound_html, height=0, width=0)

# 2. Shared Multi-Room Server Architecture 
@st.cache_resource(validate=None)
def get_global_server():
    return {} # Format: {"RoomName": {"passcode": "123", "players": {}, "settings": {}, "state": {}}}

server = get_global_server()

# --- SIDEBAR: SECURE MATCHMAKING ---
st.sidebar.header("🚪 Secure Matchmaking")
room_id = st.sidebar.text_input("Lobby Name:", value="RoomA").strip()
room_passcode = st.sidebar.text_input("Lobby Passcode:", type="password", value="1234").strip()

# Initialize a protected room structure if it's new
if room_id not in server:
    server[room_id] = {
        "passcode": room_passcode,
        "digits": 5,        # Default setting
        "is_paused": False, # Play/Pause tracking
        "players": {},      # Dict structure: {"PlayerName": {"secret": "12345", "guesses": [], "unsolved": True}}
        "turn_order": [],   # Dynamic matching tracker
        "current_idx": 0,
        "timer_start": time.time(),
        "time_left": 30,
        "winner": None
    }

game = server[room_id]

# Security Guard: Stop access if the passcode doesn't match
if game["passcode"] != room_passcode:
    st.error("🔒 Incorrect passcode for this lobby! Please type the correct code or create a unique Room name.")
    st.stop()

# --- PLAYER REGISTRATION & IDENTITY ---
st.sidebar.markdown("---")
st.sidebar.header("👤 Player Registration")
player_name = st.sidebar.text_input("Enter Your Name:", value="", max_chars=12).strip()

if player_name:
    if player_name not in game["players"] and not game["turn_order"]:
        # Choose code length during creation
        game["digits"] = st.sidebar.selectbox("Choose Code Length:", [4, 5], index=1 if game["digits"]==5 else 0)
        
        if st.sidebar.button(f"Join as Player: {player_name}"):
            game["players"][player_name] = {"secret": None, "guesses": [], "unsolved": True}
            st.rerun()
else:
    st.sidebar.warning("Please type your name to participate.")

# Show connected participants
if game["players"]:
    st.sidebar.markdown("**Lobby Members:**")
    for p in game["players"]:
        ready_status = "✅ Code Set" if game["players"][p]["secret"] else "⏳ Setting Code..."
        st.sidebar.write(f"- {p} ({ready_status})")

# --- GAME CONTROLS (PLAY / PAUSE) ---
st.sidebar.markdown("---")
st.sidebar.header("🕹️ Game Operations")
if st.sidebar.button("⏸️ Pause Clock" if not game["is_paused"] else "▶️ Resume Clock"):
    game["is_paused"] = not game["is_paused"]
    game["timer_start"] = time.time() # Reset timestamp window
    st.rerun()

# --- HELPER LOGIC ---
def get_bulls_and_cows(secret, guess):
    bulls = sum(1 for s, g in zip(secret, guess) if s == g)
    cows = sum(1 for g in guess if g in secret) - bulls
    return bulls, cows

# --- PHASE 1: LOBBY SETUP (CREATING PASSCODES) ---
if not game["turn_order"]:
    st.subheader(f"🔒 Step 1: Locked Code Submission ({game['digits']}-Digits)")
    st.info(f"Lobby Configured for **{game['digits']} unique digits**. Identity verification required before viewing inputs.")
    
    if player_name in game["players"]:
        my_data = game["players"][player_name]
        if my_data["secret"] is not None:
            st.success("Your secret code is locked in! Waiting for all other players to complete setup.")
        else:
            secret_input = st.text_input(f"Create your secret {game['digits']}-digit sequence:", type="password")
            if st.button("Lock Secret Passcode"):
                if len(secret_input) == game["digits"] and len(set(secret_input)) == game["digits"] and secret_input.isdigit():
                    my_data["secret"] = secret_input
                    st.success("Sequence successfully locked!")
                    st.rerun()
                else:
                    st.error(f"Error: Sequence must consist of exactly {game['digits']} non-repeating digits.")
    else:
        st.caption("Please join the lobby through the sidebar to input your passcodes.")

    # Master Start Game Condition (Minimum 2 players, all must be ready)
    if len(game["players"]) >= 2 and all(p["secret"] for p in game["players"].values()):
        if st.button("🚀 Initialization Sequence: Start Match"):
            game["turn_order"] = list(game["players"].keys())
            game["current_idx"] = 0
            game["timer_start"] = time.time()
            game["time_left"] = 30
            st.rerun()

# --- PHASE 2: BATTLE IN THE LOBBY ---
else:
    # ⏱️ Real-time Timer Computation Mechanics
    if not game["winner"] and not game["is_paused"]:
        elapsed = time.time() - game["timer_start"]
        game["time_left"] = max(0, 30 - int(elapsed))
        
        # Audio alarm triggers when time falls under 6 seconds remaining
        if 0 < game["time_left"] <= 5:
            play_sound_alert()

        # Force Turn Skip when Timer Expires
        if game["time_left"] == 0:
            game["current_idx"] = (game["current_idx"] + 1) % len(game["turn_order"])
            game["timer_start"] = time.time()
            game["time_left"] = 30
            st.rerun()

    # Track currently active players
    active_guesser = game["turn_order"][game["current_idx"]]
    
    # Target distribution structure: You crack the code of the person standing right next to you in the loop
    target_idx = (game["current_idx"] + 1) % len(game["turn_order"])
    target_victim = game["turn_order"][target_idx]

    # Visual HUD Layout Interface
    col_hud1, col_hud2 = st.columns(2)
    with col_hud1:
        st.markdown(f"### ⚔️ Current Turn: **{active_guesser}**")
        st.markdown(f"🎯 Target Objective: Crack **{target_victim}**'s system code!")
    with col_hud2:
        if game["is_paused"]:
            st.markdown("## ⏸️ CLOCK PAUSED")
        else:
            color = "red" if game["time_left"] <= 5 else "inverse"
            st.metric("⏳ Round Countdown Time", f"{game['time_left']} Seconds")

    st.markdown("---")

    # Render Active Player Guessing Dashboard Matrix
    if player_name == active_guesser and not game["winner"] and not game["is_paused"]:
        guess_input = st.text_input(f"Enter your {game['digits']}-digit code assessment:", max_chars=game["digits"])
        if st.button("Submit Assessment Check"):
            if len(guess_input) == game["digits"] and len(set(guess_input)) == game["digits"] and guess_input.isdigit():
                
                # Fetch target code parameters
                target_secret = game["players"][target_victim]["secret"]
                b, c = get_bulls_and_cows(target_secret, guess_input)
                
                # Append analytics
                game["players"][active_guesser]["guesses"].append((guess_input, b, c, target_victim))
                
                if b == game["digits"]:
                    game["winner"] = active_guesser
                    game["players"][target_victim]["unsolved"] = False
                else:
                    # Switch to next player's turn index
                    game["current_idx"] = (game["current_idx"] + 1) % len(game["turn_order"])
                    game["timer_start"] = time.time()
                    game["time_left"] = 30
                st.rerun()
            else:
                st.error(f"Sequence entry requires {game['digits']} structural unique numbers.")

    # --- SHOWCASE CENTRAL MONITOR DISPLAY AREA ---
    st.subheader("📊 Arena Battle Logs")
    tabs = st.tabs(list(game["players"].keys()))
    
    for i, p_tab_name in enumerate(game["players"]):
        with tabs[i]:
            p_data = game["players"][p_tab_name]
            
            # Feature Request Implementation: Reveal code instantly if compromised or match terminates
            if game["winner"] or not p_data["unsolved"]:
                st.markdown(f"🔓 **Revealed Secret Key Vector:** `{p_data['secret']}`")
            else:
                st.markdown("🔒 **Revealed Secret Key Vector:** `•••••` (Hidden until cracked or round ends)")

            # Render Guess History Tracking logs
            if p_data["guesses"]:
                st.markdown("**Submission Attempts:**")
                for g, b, c, target in reversed(p_data["guesses"]):
                    st.write(f"🔢 Target: `{target}` ➡️ Guess: `{g}` ➡️ 🐂 Bulls: **{b}** | 🐄 Cows: **{c}**")
            else:
                st.caption("No entry computations processed yet.")

    # Victory End State Conditions Trigger
    if game["winner"]:
        st.balloons()
        st.success(f"🏆 System Announcement: Victory achieved! {game['winner']} successfully broke the firewall!")
        
        # Display all remaining unsolved vault keys to players
        st.subheader("📂 Complete Global Vault Reveal")
        for key, value in game["players"].items():
            st.write(f"👤 Player: **{key}** ➡️ Master System Key: `{value['secret']}`")

    # Master Reset Controller Button
    st.markdown("---")
    if st.button("🔄 Dissolve Room State & Reframe Lobby"):
        server[room_id] = {
            "passcode": room_passcode,
            "digits": game["digits"],
            "is_paused": False,
            "players": {},
            "turn_order": [],
            "current_idx": 0,
            "timer_start": time.time(),
            "time_left": 30,
            "winner": None
        }
        st.rerun()
