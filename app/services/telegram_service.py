import logging
import json
from datetime import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from app.utils.config import TELEGRAM_BOT_TOKEN
from app.agents.decision_agent import DecisionAgent

from app.services.supabase_client import supabase  # Your Supabase client


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def parse_symbols(symbols):
    """
    Parse the symbols input which might be:
    - a JSON string like '["TCS"]'
    - a Python list like ['TCS']
    - a plain string like 'TCS'
    Returns a list of symbols.
    """
    if isinstance(symbols, str):
        try:
            parsed = json.loads(symbols)
            if isinstance(parsed, list):
                return parsed
            else:
                # If JSON decoded but not a list, just wrap it
                return [str(parsed)]
        except json.JSONDecodeError:
            # Not a JSON string, treat as a single symbol string
            return [symbols]
    elif isinstance(symbols, list):
        return symbols
    else:
        # Unexpected type, return empty list to avoid errors
        return []


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Send me a list of stock symbols separated by commas (e.g., AAPL, TSLA, MSFT)."
    )


async def receive_symbols(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    symbols = [s.strip().upper() for s in text.split(",") if s.strip()]
    if not symbols:
        await update.message.reply_text("Please send a valid list of stock symbols.")
        return

    chat_id = update.effective_chat.id
    context.user_data["symbols"] = symbols

    await update.message.reply_text("Analyzing your stocks. Please wait...")

    summaries = []
    for symbol in symbols:
        agent = DecisionAgent(symbol)
        decision = await agent.run()
        summaries.append(f"{symbol}: {decision.get('final_decision', 'No decision')}")

    summary_text = "\n".join(summaries)
    await update.message.reply_text(f"Portfolio summary:\n{summary_text}")

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Yes", callback_data="subscribe_yes"),
                InlineKeyboardButton("❌ No", callback_data="subscribe_no"),
            ]
        ]
    )
    await update.message.reply_text(
        "Do you want to receive daily updates for your portfolio?", reply_markup=keyboard
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    if data == "subscribe_yes":
        symbols = context.user_data.get("symbols")
        if not symbols:
            await query.edit_message_text(
                "No stock symbols found in session. Please send your symbols again."
            )
            return

        try:
            # Convert list to JSON string before saving
            symbols_json = json.dumps(symbols)
            response = supabase.table("subscriptions").upsert(
                {"chat_id": chat_id, "symbols": symbols_json}
            ).execute()

            if not hasattr(response, "data") or response.data is None:
                logger.error(f"Supabase upsert returned no data for chat_id={chat_id}")
                await query.edit_message_text(
                    "Sorry, failed to save your subscription. Please try again later."
                )
                return

            logger.info(f"Subscribed chat_id={chat_id} symbols={symbols}")
            await query.edit_message_text(
                f"Subscribed to daily updates for: {', '.join(symbols)}"
            )
        except Exception as e:
            logger.error(f"Supabase upsert error: {e}")
            await query.edit_message_text(
                "Sorry, failed to save your subscription. Please try again later."
            )

    elif data == "subscribe_no":
        await query.edit_message_text("No problem! You will not receive daily updates.")


async def daily_update_callback(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Running daily update job")

    try:
        response = supabase.table("subscriptions").select("*").execute()

        if not hasattr(response, "data") or response.data is None:
            logger.error("Error fetching subscriptions or no data returned")
            return

        subscriptions = response.data
    except Exception as e:
        logger.error(f"Failed to fetch subscriptions from Supabase: {e}")
        return

    for sub in subscriptions:
        chat_id = sub["chat_id"]
        symbols = parse_symbols(sub["symbols"])

        if not symbols:
            logger.warning(f"No symbols found for chat_id={chat_id}, skipping update.")
            continue

        summaries = []
        for symbol in symbols:
            agent = DecisionAgent(symbol)
            decision = await agent.run()
            summaries.append(f"{symbol}: {decision.get('final_decision', 'No decision')}")

        summary_text = "\n".join(summaries)
        text = f"📈 Daily Portfolio Update:\n{summary_text}\n\nSelect a stock to get detailed insights."

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(symbol, callback_data=f"details_{symbol}")] for symbol in symbols]
        )

        try:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Failed to send daily update to {chat_id}: {e}")


async def detailed_insights_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    if data.startswith("details_"):
        symbol = data.replace("details_", "")
        agent = DecisionAgent(symbol)
        decision = await agent.run()

        tech_reco = decision.get("final_decision", "N/A")
        reasoning = decision.get("reasoning", "No reasoning provided.")

        details_text = (
            f"📊 Detailed analysis for {symbol}:\n"
            f"Final Decision: {tech_reco}\n"
            f"Reasoning:\n{reasoning}"
        )

        await query.edit_message_text(details_text)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        response = supabase.table("subscriptions").delete().eq("chat_id", chat_id).execute()

        if not hasattr(response, "data") or response.data is None:
            logger.error(f"Error unsubscribing chat_id={chat_id}: no data returned")
            await update.message.reply_text("Failed to unsubscribe, please try again.")
            return

        if isinstance(response.data, list) and len(response.data) == 0:
            await update.message.reply_text("You are not subscribed to daily updates.")
        else:
            await update.message.reply_text("You have unsubscribed from daily updates.")
    except Exception as e:
        logger.error(f"Supabase error on unsubscribe: {e}")
        await update.message.reply_text("An error occurred. Please try again later.")


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_symbols))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^subscribe_"))
    application.add_handler(CallbackQueryHandler(detailed_insights_handler, pattern="^details_"))

    # Schedule daily update at 11:11 AM UTC
    application.job_queue.run_daily(
        daily_update_callback, time=time(hour=11, minute=30, second=0)
    )

    application.run_polling()


if __name__ == "__main__":
    main()
