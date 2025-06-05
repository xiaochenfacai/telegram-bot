import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime

# --- Bot Config ---
BOT_TOKEN = "8179217333:AAE1vGFun7lYj5Ff4ak6DKYjCR99kp0uN_E"
BOT_OWNER_USERNAME = "xiaochenfacai8888"

# --- Logging ---
logging.basicConfig(level=logging.INFO)

# --- In-memory database (per group) ---
group_data = {}

# --- Helper Functions ---
def get_group_data(group_id):
    if group_id not in group_data:
        group_data[group_id] = {
            "records": [],
            "withdrawals": [],
            "rate": 9.0,
            "admins": set()
        }
    return group_data[group_id]

def format_response(records, withdrawals, rate):
    lines = []
    lines.append(f"入款（{len(records)}笔）：")
    for record in records:
        lines.append(f"{record['time']}  {record['text']} / {rate}=%.2f" % (record['amount'] / rate))
    lines.append("\n下发（{}笔）：{}".format(len(withdrawals), " ".join([f"{w}u" for w in withdrawals]) if withdrawals else ""))
    total = sum(r['amount'] for r in records)
    should_send = total / rate
    sent = sum(withdrawals)
    not_sent = should_send - sent
    lines.append(f"\n总入款：{int(total)}")
    lines.append(f"费率：0%")
    lines.append(f"USD汇率：{rate}")
    lines.append(f"\n应下发：%.2f USDT" % should_send)
    lines.append(f"未下发：%.2f USDT" % not_sent)
    return "\n".join(lines)

def is_admin(username, group):
    return username == BOT_OWNER_USERNAME or username in group["admins"]

# --- Handlers ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in ["group", "supergroup"]:
        return

    user = update.effective_user.username
    group_id = update.effective_chat.id
    group = get_group_data(group_id)
    text = update.message.text.strip()
    now = datetime.now().strftime("%H:%M:%S")

    # Match deposits or named deposits
    if text.startswith("+") or "+" in text:
        try:
            if "+" in text[1:]:
                name, amt = text.rsplit("+", 1)
                name = name.strip()
            else:
                name = ""
                amt = text.strip("+").strip()
            amount = float(amt)
            group["records"].append({"time": now, "amount": amount, "text": name + "+" + amt if name else amt})
            await update.message.reply_text(format_response(group["records"], group["withdrawals"], group["rate"]))
        except:
            pass

    # Match withdrawals: 下发 100
    elif text.startswith("下发"):
        try:
            _, amt = text.split()
            amount = float(amt)
            group["withdrawals"].append(amount)
            await update.message.reply_text(format_response(group["records"], group["withdrawals"], group["rate"]))
        except:
            pass

    # Match minus
    elif text.startswith("-"):
        try:
            amount = float(text.strip("-"))
            group["records"].append({"time": now, "amount": -amount, "text": f"-{amount}"})
            await update.message.reply_text(format_response(group["records"], group["withdrawals"], group["rate"]))
        except:
            pass

# --- Commands ---
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username
    group_id = update.effective_chat.id
    group = get_group_data(group_id)
    if is_admin(user, group):
        group["records"].clear()
        group["withdrawals"].clear()
        await update.message.reply_text("✅ 已清空记录")
    else:
        await update.message.reply_text("❌ 无权限")

async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username
    group_id = update.effective_chat.id
    group = get_group_data(group_id)
    if is_admin(user, group):
        try:
            group["rate"] = float(context.args[0])
            await update.message.reply_text(f"✅ 汇率已设置为 {group['rate']}")
        except:
            await update.message.reply_text("❌ 格式错误，应为 /rate 9.0")
    else:
        await update.message.reply_text("❌ 无权限")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username
    group_id = update.effective_chat.id
    group = get_group_data(group_id)
    if user == BOT_OWNER_USERNAME:
        try:
            username = context.args[0].replace("@", "")
            group["admins"].add(username)
            await update.message.reply_text(f"✅ 已添加管理员：@{username}")
        except:
            await update.message.reply_text("❌ 格式错误，应为 /add @username")
    else:
        await update.message.reply_text("❌ 只有机器人主人可以添加管理员")

# --- Main Bot Setup ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("rate", rate))
    app.add_handler(CommandHandler("add", add_admin))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
