import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
import hashlib
import time
import json
import os
import binascii
import threading
import urllib3
import random
import urllib.parse

# SSL Warning များကို ဖျောက်ထားရန်
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BOT_TOKEN = "8872336051:AAFWKsIebEcmb-9p8wLeVWKTwjF-Nb06sYA"
bot = telebot.TeleBot(BOT_TOKEN)

STYLE_HEADER = "💎 *{}* 💎"
STYLE_DIVIDER = "━━━━━━━━━━━━━━━━━━━━━"

PLATFORMS = {
    "CKLOTTERY": {"name": "CKLOTTERY", "baseUrl": "https://ckygjf6r.com/api/webapi/", "color": "🔵"}
}
CURRENT_PLATFORM = PLATFORMS["CKLOTTERY"]

user_sessions = {}
user_settings = {}
user_info_cache = {}
pending_bets = {} 

def generate_signature(data):
    filtered = {k: v for k, v in data.items() if k not in ["signature", "track", "xosoBettingData"] and k != "timestamp" and v is not None and v != ''}
    sorted_dict = {k: filtered[k] for k in sorted(filtered.keys())}
    json_str = json.dumps(sorted_dict, separators=(',', ':'))
    return hashlib.md5(json_str.encode('utf-8')).hexdigest().upper()

def get_headers(session_data):
    return {
        "Authorization": f"{session_data.get('tokenHeader', 'Bearer ')}{session_data.get('token', '')}",
        "Content-Type": "application/json;charset=UTF-8",
        "Ar-Origin": "https://6win598.com", "Origin": "https://6win598.com", "Referer": "https://6win598.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0"
    }

def login_request(phone, password):
    url = CURRENT_PLATFORM["baseUrl"] + "Login"
    body = {
        "username": "95" + phone, "pwd": password, "phonetype": 1, "logintype": "mobile", "packId": "",
        "deviceId": "5dcab3e06db88a206975e91ea6ac7c87", "language": 7, 
        "random": binascii.hexlify(os.urandom(16)).decode('utf-8')
    }
    body["signature"] = generate_signature(body)
    body["timestamp"] = int(time.time())
    
    try:
        response = requests.post(url, json=body, headers=get_headers({}), timeout=15, verify=False)
        res = response.json()
        if res.get("code") == 0 and res.get("data"): return res["data"], "Success"
        return None, res.get("msg", "API Error")
    except Exception as e: return None, str(e)

def get_user_info(session_data):
    url = CURRENT_PLATFORM["baseUrl"] + "GetUserInfo"
    body = {"language": 7, "random": "4fc9f8f8d6764a5f934d4c6a468644e0"}
    body["signature"] = generate_signature(body)
    body["timestamp"] = int(time.time())
    try:
        if (res := requests.post(url, json=body, headers=get_headers(session_data), timeout=10, verify=False).json()).get("code") == 0:
            return res.get("data", {})
    except: pass
    return {}

def get_balance(session_data):
    url = CURRENT_PLATFORM["baseUrl"] + "GetBalance"
    body = {"language": 7, "random": "71ebd56cff7d4679971c482807c33f6f"}
    body["signature"] = generate_signature(body)
    body["timestamp"] = int(time.time())
    try:
        if (res := requests.post(url, json=body, headers=get_headers(session_data), timeout=10, verify=False).json()).get("code") == 0:
            data = res.get("data", {})
            return float(data.get("Amount") or data.get("amount") or data.get("balance") or 0.0)
    except: pass
    return None

def get_game_issue(session_data, type_id):
    url = CURRENT_PLATFORM["baseUrl"] + "GetGameIssue"
    body = {"typeId": type_id, "language": 7, "random": "7d76f361dc5d4d8c98098ae3d48ef7af"}
    body["signature"] = generate_signature(body)
    body["timestamp"] = int(time.time())
    try:
        if (res := requests.post(url, json=body, headers=get_headers(session_data), timeout=10, verify=False).json()).get("code") == 0:
            return res.get("data", {})
    except: pass
    return None

def get_game_results(session_data, type_id):
    url = CURRENT_PLATFORM["baseUrl"] + "GetNoaverageEmerdList"
    body = {"pageSize": 15, "pageNo": 1, "typeId": type_id, "language": 7, "random": "4ad5325e389745a882f4189ed6550e70"}
    body["signature"] = generate_signature(body)
    body["timestamp"] = int(time.time())
    try:
        if (res := requests.post(url, json=body, headers=get_headers(session_data), timeout=10, verify=False).json()).get("code") == 0:
            return res.get("data", {}).get("list", [])
    except: pass
    return []

def compute_bet_details(amount):
    if amount % 10000 == 0: return 10000, amount // 10000
    if amount % 1000 == 0: return 1000, amount // 1000
    if amount % 100 == 0: return 100, amount // 100
    if amount % 10 == 0: return 10, amount // 10
    return 1, amount

def place_bet(session_data, issue_number, type_id, select_type, amount):
    url = CURRENT_PLATFORM["baseUrl"] + "GameBetting"
    unit_amount, bet_count = compute_bet_details(amount)
    
    body = {
        "typeId": type_id, "issuenumber": issue_number, "language": 7, "gameType": 2, 
        "amount": unit_amount, "betCount": bet_count, "selectType": select_type, "random": "f9ec46840a374a65bb2abad44dfc4dc3"
    }
    body["signature"] = generate_signature(body)
    body["timestamp"] = int(time.time())
    try:
        return requests.post(url, json=body, headers=get_headers(session_data), timeout=10, verify=False).json()
    except Exception as e: return {"code": -1, "msg": str(e)}

def get_ai_prediction(history_results):
    if not history_results: return random.choice(['B', 'S'])
    try:
        history_list = ['B' if (int(r.get("number", 0)) % 10) >= 5 else 'S' for r in history_results[:15]]
        history_list.reverse() 
        history_str = ", ".join(history_list)
        
        prompt = f"Analyze Big(B)/Small(S) sequence: {history_str}. Predict NEXT outcome. Reply ONLY [RESULT: B] or [RESULT: S]."
        url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
        
        res_text = requests.get(url, timeout=15).text.upper()
        
        if "[RESULT: B]" in res_text or res_text.strip() == "B": return 'B'
        elif "[RESULT: S]" in res_text or res_text.strip() == "S": return 'S'
        else:
            b_c, s_c = res_text.count('B'), res_text.count('S')
            if b_c > s_c: return 'B'
            if s_c > b_c: return 'S'
            return history_list[-1]
    except:
        if history_results: return 'B' if (int(history_results[0].get("number", 0)) % 10) >= 5 else 'S'
    return random.choice(['B', 'S'])

def get_prediction(user_id, session_data, type_id):
    settings = user_settings.get(user_id, {})
    strategy = settings.get("strategy", "AI_GPT")
    
    if strategy == "CUSTOM_PATTERN":
        pat = settings.get("custom_pattern", "B") or "B"
        idx = settings.get("pattern_idx", 0)
        prediction = pat[idx % len(pat)]
        settings["pattern_idx"] = (idx + 1) % len(pat)
        return prediction
    elif strategy == "TREND_FOLLOW":
        results = get_game_results(session_data, type_id)
        if results: return 'B' if (int(results[0].get("number", 0)) % 10) >= 5 else 'S'
    elif strategy == "AI_GPT":
        results = get_game_results(session_data, type_id)
        return get_ai_prediction(results)
    return random.choice(['B', 'S'])

def evaluate_ai_advice(win_rate, total_games):
    if total_games < 5:
        return "⏳ ပွဲမလုံလောက်သေးပါ။ ဆက်ဆော့ကြည့်ပါ။"
    if win_rate >= 60:
        return "🔥 ကံကောင်းနေပါတယ်။ ဆက်ဆော့ရန် သင့်တော်ပါသည်။"
    elif win_rate >= 40:
        return "⚖️ ပုံမှန်အခြေအနေပါ။ အမြတ်/အရှုံး သတိထားဆော့ပါ။"
    else:
        return "⚠️ ရှုံးပွဲများနေပါသည်။ ခဏနားသင့်ပါပြီ (Take a Break)!"

# --- BACKGROUND WORKER ---
def auto_betting_worker():
    while True:
        try:
            for user_id, settings in list(user_settings.items()):
                if user_id not in user_sessions: continue
                session = user_sessions[user_id]
                type_id = settings.get("type_id", 30)
                bet_amount = settings.get("bet_amount", 10)
                
                pending = pending_bets.get(user_id)
                if pending:
                    msg_id = pending.get("msg_id")
                    if msg_id:
                        tick = pending.get("tick", 0)
                        if tick % 2 == 0: 
                            try:
                                status_str = "⏳ *Waiting for Result...*" if tick % 4 == 0 else "🔄 *Checking Live Data...*"
                                text = f"⏱️ *BET PLACED*\n🔖 Period: `{pending['issue']}`\n🎯 Choice: *{'BIG' if pending['choice']=='B' else 'SMALL'}*\n💰 Amount: {pending['amount']} Ks\n\n{status_str}"
                                bot.edit_message_text(text, user_id, msg_id, parse_mode="Markdown")
                            except: pass
                        pending["tick"] = tick + 1

                    results = get_game_results(session, type_id)
                    for r in results:
                        if str(r.get("issueNumber")) == str(pending["issue"]):
                            number = int(r.get("number", 0)) % 10
                            is_big = number >= 5
                            result_bs = 'B' if is_big else 'S'
                            won = (result_bs == pending["choice"])
                            
                            win_amount = pending["amount"] * 0.96 if won else 0
                            if won:
                                settings["win_count"] += 1
                                settings["total_profit"] += win_amount
                            else:
                                settings["loss_count"] += 1
                                settings["total_profit"] -= pending["amount"]
                                
                            settings["history_log"].append({
                                "issue": pending["issue"], "choice": pending["choice"], 
                                "result": result_bs, "won": won, "amount": pending["amount"]
                            })
                            settings["history_log"] = settings["history_log"][-20:]
                            
                            bal = get_balance(session)
                            bal_str = f"{bal} Ks" if bal is not None else "Updating..."
                            
                            t_profit = settings["total_profit"]
                            pf_sign = "+" if t_profit > 0 else ""
                            
                            msg = f"✅ *VICTORY! (+{win_amount} Ks)*\n" if won else f"❌ *LOSS! (-{pending['amount']} Ks)*\n"
                            msg += (
                                f"{STYLE_DIVIDER}\n"
                                f"🔖 Period: `{pending['issue']}`\n"
                                f"🎯 Your Bet: *{'BIG' if pending['choice']=='B' else 'SMALL'}*\n"
                                f"🎲 Result: *{number} ({'BIG' if is_big else 'SMALL'})*\n\n"
                                f"💵 *Live Balance:* {bal_str}\n"
                                f"📈 *Total Profit:* {pf_sign}{t_profit:.2f} Ks"
                            )
                            
                            if msg_id:
                                try: bot.edit_message_text(msg, user_id, msg_id, parse_mode="Markdown")
                                except: bot.send_message(user_id, msg, parse_mode="Markdown")
                            else:
                                bot.send_message(user_id, msg, parse_mode="Markdown")
                                
                            pending_bets[user_id] = None
                            
                            tp = settings.get("target_profit", 0)
                            sl = settings.get("stop_loss", 0)
                            
                            if tp > 0 and t_profit >= tp:
                                settings["running"] = False
                                bot.send_message(user_id, f"🎉 *TARGET REACHED! (ပစ်မှတ်ရောက်သွားပါပြီ)*\nအမြတ်ငွေ {t_profit} Ks ရရှိသွားပြီဖြစ်၍ Bot အလိုအလျောက် ရပ်သွားပါပြီ။", parse_mode="Markdown")
                            elif sl > 0 and t_profit <= -sl:
                                settings["running"] = False
                                bot.send_message(user_id, f"🛑 *STOP LOSS REACHED! (အရှုံးကန့်သတ်ချက် ပြည့်သွားပါပြီ)*\nအရှုံးငွေ {abs(t_profit)} Ks ရောက်သွားပြီဖြစ်၍ Bot အလိုအလျောက် ရပ်သွားပါပြီ။", parse_mode="Markdown")
                            
                            break
                            
                if settings.get("running") and not pending_bets.get(user_id):
                    issue_data = get_game_issue(session, type_id)
                    if not issue_data: continue
                    
                    current_issue = issue_data.get("issueNumber")
                    if current_issue and current_issue != settings.get("last_issue"):
                        prediction = get_prediction(user_id, session, type_id)
                        select_type = 13 if prediction == 'B' else 14
                        
                        res = place_bet(session, current_issue, type_id, select_type, bet_amount)
                        settings["last_issue"] = current_issue
                        
                        if res and res.get("code") == 0:
                            msg_text = f"⏱️ *BET PLACED*\n🔖 Period: `{current_issue}`\n🎯 Choice: *{'BIG' if prediction == 'B' else 'SMALL'}*\n💰 Amount: {bet_amount} Ks\n\n⏳ *Waiting for Result...*"
                            sent_msg = bot.send_message(user_id, msg_text, parse_mode="Markdown")
                            pending_bets[user_id] = {
                                "issue": current_issue, "choice": prediction, 
                                "amount": bet_amount, "msg_id": sent_msg.message_id, "tick": 0
                            }
                        else:
                            bot.send_message(user_id, f"❌ *Bet Failed!*\nReason: {res.get('msg', 'Betting Amount Error')}")
                            
        except Exception as e: pass
        time.sleep(3)

# --- BOT INTERFACE ---
def init_user(user_id):
    if user_id not in user_settings:
        user_settings[user_id] = {
            "strategy": "AI_GPT", "running": False, "type_id": 30, "bet_amount": 10, 
            "custom_pattern": "B", "pattern_idx": 0, "target_profit": 0, "stop_loss": 0,
            "win_count": 0, "loss_count": 0, "total_profit": 0.0, "history_log": []
        }

def get_main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # Clean, short English buttons for a premium look
    markup.add(KeyboardButton("🔐 Login"), KeyboardButton("📊 Dashboard"))
    markup.add(KeyboardButton("🎮 Game"), KeyboardButton("💰 Amount"))
    markup.add(KeyboardButton("🎯 Target/SL"), KeyboardButton("📜 History"))
    markup.add(KeyboardButton("⚙️ Strategy"))
    markup.add(KeyboardButton("▶️ Start Auto"), KeyboardButton("⏹️ Stop Auto"))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    init_user(user_id)
    s = user_settings[user_id]
    
    text = (
        f"{STYLE_HEADER.format('BUSINESS AUTO BOT')}\n"
        f"{STYLE_DIVIDER}\n\n"
        f"Welcome, *{message.from_user.first_name}*.\n\n"
        f"🔹 *Game:* {'Win Go 30s' if s['type_id'] == 30 else 'Win Go 1Min'}\n"
        f"🔹 *Bet Amount:* {s['bet_amount']} Ks\n"
        f"🔹 *Status:* {'🟢 Running' if s['running'] else '🔴 Stopped'}\n\n"
        f"📖 *MENU GUIDE (အသုံးပြုနည်း လမ်းညွှန်):*\n"
        f"🔐 Login - အကောင့်ဝင်ရန်\n"
        f"📊 Dashboard - လက်ကျန်ငွေကြည့်ရန်\n"
        f"🎮 Game - ဂိမ်းအမျိုးအစားရွေးရန်\n"
        f"💰 Amount - လောင်းကြေးပြောင်းရန်\n"
        f"🎯 Target/SL - အမြတ်/အရှုံး ကန့်သတ်ရန်\n"
        f"📜 History - မှတ်တမ်းကြည့်ရန်\n"
        f"⚙️ Strategy - နည်းဗျူဟာပြောင်းရန်\n"
        f"▶️ Start Auto - အော်တို စတင်ရန်"
    )
    bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = message.chat.id
    text = message.text
    init_user(user_id)
    s = user_settings[user_id]

    try:
        if text == "🔐 Login":
            msg = bot.send_message(user_id, "📱 ဖုန်းနံပါတ် နှင့် Password ကို Space ခြား၍ ရိုက်ထည့်ပါ။\n(e.g., `9781991467 password`)", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_login)
            
        elif text == "📊 Dashboard":
            if user_id in user_sessions:
                status_msg = bot.send_message(user_id, "⏳ Fetching live data...")
                bal = get_balance(user_sessions[user_id])
                uid = user_info_cache.get(user_id, {}).get("userId", "Unknown")
                
                if bal is not None:
                    pf_sign = "+" if s['total_profit'] > 0 else ""
                    msg = (f"👤 *UID:* `{uid}`\n"
                           f"💳 *Live Balance:* {bal} Ks\n\n"
                           f"📈 *Session Profit:* {pf_sign}{s['total_profit']:.2f} Ks\n"
                           f"🎯 *Target:* {s['target_profit']} Ks | 🛑 *Stop Loss:* {s['stop_loss']} Ks\n"
                           f"⚙️ *Strategy:* {s['strategy'].replace('_', ' ')}")
                else:
                    msg = "❌ Fetch failed. Please check connection."
                bot.edit_message_text(msg, user_id, status_msg.message_id, parse_mode="Markdown")
            else:
                bot.send_message(user_id, "⚠️ Please login first.")
                
        elif text == "🎮 Game":
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("⏱️ Win Go 30s", callback_data="game:30"), InlineKeyboardButton("🕒 Win Go 1Min", callback_data="game:1"))
            bot.send_message(user_id, f"{STYLE_HEADER.format('SELECT GAME TYPE')}", parse_mode="Markdown", reply_markup=markup)
            
        elif text == "💰 Amount":
            msg = bot.send_message(user_id, "💰 လောင်းကြေးပမာဏ ရိုက်ထည့်ပါ (ဥပမာ - 10, 20, 50, 100):")
            bot.register_next_step_handler(msg, process_amount)

        elif text == "🎯 Target/SL":
            msg = bot.send_message(user_id, "🎯 *အမြတ်ပစ်မှတ် (Target)* နှင့် *အရှုံးကန့်သတ်ချက် (Stop Loss)* ကို Space ခြား၍ ရိုက်ထည့်ပါ။\n\n(ဥပမာ - `1000 500` ဟုရိုက်လျှင် ၁၀၀၀ မြတ်လျှင် သို့မဟုတ် ၅၀၀ ရှုံးလျှင် ရပ်မည်)\nပိတ်ထားလိုပါက `0 0` ဟု ရိုက်ပါ။", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_limits)

        elif text == "📜 History":
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("📊 Summary (အကျဉ်းချုပ်)", callback_data="hist:sum"))
            markup.row(InlineKeyboardButton("📝 Detailed (အသေးစိတ်)", callback_data="hist:det"))
            bot.send_message(user_id, "📜 ကြည့်ရှုလိုသော မှတ်တမ်းအမျိုးအစားကို ရွေးချယ်ပါ:", reply_markup=markup)
            
        elif text == "⚙️ Strategy":
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("🤖 AI GPT Predict", callback_data="set_strat:AI_GPT"))
            markup.row(InlineKeyboardButton("📈 Trend Follow", callback_data="set_strat:TREND_FOLLOW"))
            markup.row(InlineKeyboardButton("📝 Custom Pattern", callback_data="set_custom_pattern"))
            bot.send_message(user_id, f"{STYLE_HEADER.format('STRATEGY SETTINGS')}", parse_mode="Markdown", reply_markup=markup)
            
        elif text == "▶️ Start Auto":
            if user_id not in user_sessions: 
                bot.send_message(user_id, "⚠️ Please login first.")
                return
            s["running"] = True
            bot.send_message(user_id, "▶️ *AUTO BETTING ACTIVATED*", parse_mode="Markdown")
            
        elif text == "⏹️ Stop Auto":
            s["running"] = False
            bot.send_message(user_id, "⏹️ *AUTO BETTING STOPPED*", parse_mode="Markdown")
            
    except Exception as e: print(f"Message Handler Error: {e}")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.message.chat.id
    init_user(user_id)
    s = user_settings[user_id]
    
    try:
        if call.data.startswith("game:"):
            s["type_id"] = int(call.data.split(":")[1])
            bot.edit_message_text(f"✅ Game set to: *{'Win Go 30s' if s['type_id']==30 else 'Win Go 1Min'}*", user_id, call.message.message_id, parse_mode="Markdown")
            
        elif call.data == "set_custom_pattern":
            msg = bot.send_message(user_id, "📝 သင်၏ ကိုယ်ပိုင် Pattern ကို B (အကြီး) နှင့် S (အသေး) သုံး၍ ရိုက်ထည့်ပါ။\n(ဥပမာ - `BBS`, `BSBS`, `B`)", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_pattern)
            
        elif call.data.startswith("set_strat:"):
            s["strategy"] = call.data.split(":")[1]
            bot.edit_message_text(f"✅ Strategy set to: *{s['strategy'].replace('_', ' ')}*", user_id, call.message.message_id, parse_mode="Markdown")
            
        elif call.data.startswith("hist:"):
            w_c, l_c = s["win_count"], s["loss_count"]
            t_games = w_c + l_c
            w_rate = (w_c / t_games * 100) if t_games > 0 else 0
            ai_advice = evaluate_ai_advice(w_rate, t_games)
            
            if call.data == "hist:sum":
                msg = (f"📊 *SUMMARY HISTORY*\n{STYLE_DIVIDER}\n"
                       f"✅ Total Wins (နိုင်ပွဲ): {w_c}\n"
                       f"❌ Total Losses (ရှုံးပွဲ): {l_c}\n"
                       f"📈 Win Rate (နိုင်ခြေ): {w_rate:.1f}%\n"
                       f"💰 Total Profit: {s['total_profit']} Ks\n\n"
                       f"🤖 *AI Advice:*\n{ai_advice}")
                bot.edit_message_text(msg, user_id, call.message.message_id, parse_mode="Markdown")
            
            elif call.data == "hist:det":
                logs = s["history_log"]
                if not logs:
                    bot.edit_message_text("No history available yet. (မှတ်တမ်း မရှိသေးပါ)", user_id, call.message.message_id)
                    return
                msg = f"📝 *DETAILED HISTORY*\n{STYLE_DIVIDER}\n"
                for log in logs:
                    icon = "✅" if log["won"] else "❌"
                    msg += f"{icon} `...{log['issue'][-4:]}` | Bet: {log['choice']} | Res: {log['result']} | {log['amount']}Ks\n"
                msg += f"\n🤖 *AI Advice:* {ai_advice}"
                bot.edit_message_text(msg, user_id, call.message.message_id, parse_mode="Markdown")

    except Exception as e: print(f"Callback Error: {e}")

def process_amount(message):
    try:
        amt = int(message.text.strip())
        if amt < 10 or amt % 10 != 0: 
            bot.send_message(message.chat.id, "❌ မှားယွင်းနေပါသည်။ 10, 20, 30 အစရှိသဖြင့် ရိုက်ပါ။")
            return
        user_settings[message.chat.id]["bet_amount"] = amt
        bot.send_message(message.chat.id, f"✅ Amount set to: *{amt} Ks*", parse_mode="Markdown")
    except: bot.send_message(message.chat.id, "❌ ပုံစံမှားယွင်းနေပါသည်။")

def process_limits(message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ ပုံစံမှားယွင်းနေပါသည်။ Space ခြား၍ ဂဏန်း ၂ ခု ရိုက်ထည့်ပါ။")
            return
        tp = int(parts[0])
        sl = int(parts[1])
        user_settings[message.chat.id]["target_profit"] = tp
        user_settings[message.chat.id]["stop_loss"] = sl
        bot.send_message(message.chat.id, f"✅ Limits set.\n🎯 Target: {tp} Ks\n🛑 Stop Loss: {sl} Ks", parse_mode="Markdown")
    except: bot.send_message(message.chat.id, "❌ ဂဏန်းများသာ ရိုက်ထည့်ပါ။")

def process_pattern(message):
    pat = message.text.strip().upper()
    if all(c in ['B', 'S'] for c in pat) and len(pat) > 0:
        user_settings[message.chat.id]["strategy"] = "CUSTOM_PATTERN"
        user_settings[message.chat.id]["custom_pattern"] = pat
        user_settings[message.chat.id]["pattern_idx"] = 0
        bot.send_message(message.chat.id, f"✅ Custom Pattern set to: *{pat}*", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ အင်္ဂလိပ်အက္ခရာ B နှင့် S ကိုသာ အသုံးပြုပါ။")

def process_login(message):
    user_id = message.chat.id
    try:
        parts = message.text.split(" ")
        session_data, err_msg = login_request(parts[0], parts[1])
        if session_data:
            user_sessions[user_id] = session_data
            user_info_cache[user_id] = get_user_info(session_data)
            
            user_settings[user_id]["win_count"] = 0
            user_settings[user_id]["loss_count"] = 0
            user_settings[user_id]["total_profit"] = 0.0
            user_settings[user_id]["history_log"] = []
            
            bot.send_message(user_id, f"✅ *Login Successful!*\nType /start to open the menu.", parse_mode="Markdown")
        else:
            bot.send_message(user_id, f"❌ Login Failed.\nReason: {err_msg}")
    except: bot.send_message(user_id, "❌ Error occurred.")

threading.Thread(target=auto_betting_worker, daemon=True).start()
print("✅ Fully Featured Python Core with Clean UI is running...")
bot.infinity_polling(timeout=10, long_polling_timeout=5)