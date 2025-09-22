# import logging
# from datetime import time

# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import (
#     Application,
#     CommandHandler,
#     MessageHandler,
#     CallbackQueryHandler,
#     ContextTypes,
#     filters,
# )

# from app.utils.config import TELEGRAM_BOT_TOKEN
# from app.agents.decision_agent import DecisionAgent

# from app.services.supabase_client import supabase  # Your Supabase client


# logging.basicConfig(
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
# )
# logger = logging.getLogger(__name__)


# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text(
#         "Welcome! Send me a list of stock symbols separated by commas (e.g., AAPL, TSLA, MSFT)."
#     )


# async def receive_symbols(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     text = update.message.text.strip()
#     symbols = [s.strip().upper() for s in text.split(",") if s.strip()]
#     if not symbols:
#         await update.message.reply_text("Please send a valid list of stock symbols.")
#         return

#     chat_id = update.effective_chat.id
#     context.user_data["symbols"] = symbols

#     await update.message.reply_text("Analyzing your stocks. Please wait...")

#     # Run DecisionAgent for each symbol and aggregate result
#     summaries = []
#     for symbol in symbols:
#         agent = DecisionAgent(symbol)
#         decision = await agent.run()
#         summaries.append(f"{symbol}: {decision.get('final_decision', 'No decision')}")

#     summary_text = "\n".join(summaries)
#     await update.message.reply_text(f"Portfolio summary:\n{summary_text}")

#     # Ask to subscribe to daily updates
#     keyboard = InlineKeyboardMarkup(
#         [
#             [
#                 InlineKeyboardButton("✅ Yes", callback_data="subscribe_yes"),
#                 InlineKeyboardButton("❌ No", callback_data="subscribe_no"),
#             ]
#         ]
#     )
#     await update.message.reply_text(
#         "Do you want to receive daily updates for your portfolio?", reply_markup=keyboard
#     )


# async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()

#     chat_id = query.message.chat_id
#     data = query.data

#     if data == "subscribe_yes":
#         symbols = context.user_data.get("symbols")
#         if not symbols:
#             await query.edit_message_text(
#                 "No stock symbols found in session. Please send your symbols again."
#             )
#             return

#         try:
#             # Upsert subscription in Supabase
#             supabase.table("subscriptions").upsert(
#                 {"chat_id": chat_id, "symbols": symbols}
#             ).execute()

#             logger.info(f"Subscribed chat_id={chat_id} symbols={symbols}")
#             await query.edit_message_text(
#                 f"Subscribed to daily updates for: {', '.join(symbols)}"
#             )
#         except Exception as e:
#             logger.error(f"Supabase upsert error: {e}")
#             await query.edit_message_text(
#                 "Sorry, failed to save your subscription. Please try again later."
#             )

#     elif data == "subscribe_no":
#         await query.edit_message_text("No problem! You will not receive daily updates.")


# async def daily_update_callback(context: ContextTypes.DEFAULT_TYPE):
#     logger.info("Running daily update job")

#     # Fetch all subscriptions from Supabase
#     try:
#         response = supabase.table("subscriptions").select("*").execute()
#         if response.error:
#             logger.error(f"Error fetching subscriptions: {response.error}")
#             return
#         subscriptions = response.data  # list of dicts with chat_id and symbols
#     except Exception as e:
#         logger.error(f"Failed to fetch subscriptions from Supabase: {e}")
#         return

#     for sub in subscriptions:
#         chat_id = sub["chat_id"]
#         symbols = sub["symbols"]

#         summaries = []
#         for symbol in symbols:
#             agent = DecisionAgent(symbol)
#             decision = await agent.run()
#             summaries.append(f"{symbol}: {decision.get('final_decision', 'No decision')}")

#         summary_text = "\n".join(summaries)
#         text = f"📈 Daily Portfolio Update:\n{summary_text}\n\nSelect a stock to get detailed insights."

#         keyboard = InlineKeyboardMarkup(
#             [[InlineKeyboardButton(symbol, callback_data=f"details_{symbol}")] for symbol in symbols]
#         )

#         try:
#             await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
#         except Exception as e:
#             logger.error(f"Failed to send daily update to {chat_id}: {e}")


# async def detailed_insights_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()

#     chat_id = query.message.chat_id
#     data = query.data

#     if data.startswith("details_"):
#         symbol = data.replace("details_", "")
#         agent = DecisionAgent(symbol)
#         decision = await agent.run()

#         tech_reco = decision.get("final_decision", "N/A")
#         reasoning = decision.get("reasoning", "No reasoning provided.")

#         details_text = (
#             f"📊 Detailed analysis for {symbol}:\n"
#             f"Final Decision: {tech_reco}\n"
#             f"Reasoning:\n{reasoning}"
#         )

#         await query.edit_message_text(details_text)


# async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     chat_id = update.effective_chat.id
#     try:
#         response = supabase.table("subscriptions").delete().eq("chat_id", chat_id).execute()
#         if response.error:
#             logger.error(f"Error unsubscribing chat_id={chat_id}: {response.error}")
#             await update.message.reply_text("Failed to unsubscribe, please try again.")
#             return

#         if response.count == 0:
#             await update.message.reply_text("You are not subscribed to daily updates.")
#         else:
#             await update.message.reply_text("You have unsubscribed from daily updates.")
#     except Exception as e:
#         logger.error(f"Supabase error on unsubscribe: {e}")
#         await update.message.reply_text("An error occurred. Please try again later.")


# def main():
#     application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

#     application.add_handler(CommandHandler("start", start))
#     application.add_handler(CommandHandler("stop", stop))
#     application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_symbols))
#     application.add_handler(CallbackQueryHandler(button_handler, pattern="^subscribe_"))
#     application.add_handler(CallbackQueryHandler(detailed_insights_handler, pattern="^details_"))

#     # Schedule daily update at 9 AM UTC (you can adjust or disable for now)
#     application.job_queue.run_daily(
#         daily_update_callback, time=time(hour=6, minute=33, second=0)
#     )

#     application.run_polling()


# if __name__ == "__main__":
#     main()
# app/services/telegram_service.py
import logging
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

    # Run DecisionAgent for each symbol and aggregate result
    summaries = []
    for symbol in symbols:
        agent = DecisionAgent(symbol)
        decision = await agent.run()
        summaries.append(f"{symbol}: {decision.get('final_decision', 'No decision')}")

    summary_text = "\n".join(summaries)
    await update.message.reply_text(f"Portfolio summary:\n{summary_text}")

    # Ask to subscribe to daily updates
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
            # Fetch existing symbols string from Supabase
            response = supabase.table("subscriptions").select("symbols").eq("chat_id", chat_id).execute()
            if response.error:
                raise Exception(response.error)

            # Parse existing symbols from comma-separated string to list
            if response.data and response.data[0]["symbols"]:
                existing_symbols = [s.strip().upper() for s in response.data[0]["symbols"].split(",")]
            else:
                existing_symbols = []

            # Merge and deduplicate symbols
            updated_symbols = list(set(existing_symbols + symbols))

            # Convert back to comma-separated string for storage
            symbols_str = ",".join(updated_symbols)

            # Upsert updated symbols string
            supabase.table("subscriptions").upsert(
                {"chat_id": chat_id, "symbols": symbols_str}
            ).execute()

            logger.info(f"Subscribed chat_id={chat_id} symbols={updated_symbols}")
            await query.edit_message_text(
                f"Subscribed to daily updates for: {', '.join(updated_symbols)}"
            )
        except Exception as e:
            logger.error(f"Supabase upsert error: {e}", exc_info=True)
            await query.edit_message_text(
                "Sorry, failed to save your subscription. Please try again later."
            )

    elif data == "subscribe_no":
        await query.edit_message_text("No problem! You will not receive daily updates.")


async def daily_update_callback(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Running daily update job")

    # Fetch all subscriptions from Supabase
    try:
        response = supabase.table("subscriptions").select("*").execute()
        if response.error:
            logger.error(f"Error fetching subscriptions: {response.error}")
            return
        subscriptions = response.data  # list of dicts with chat_id and symbols
    except Exception as e:
        logger.error(f"Failed to fetch subscriptions from Supabase: {e}")
        return

    for sub in subscriptions:
        chat_id = sub["chat_id"]
        # Convert stored comma-separated string back to list
        if sub.get("symbols"):
            symbols = [s.strip().upper() for s in sub["symbols"].split(",")]
        else:
            symbols = []

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
        if response.error:
            logger.error(f"Error unsubscribing chat_id={chat_id}: {response.error}")
            await update.message.reply_text("Failed to unsubscribe, please try again.")
            return

        if response.count == 0:
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

    # Schedule daily update 
    application.job_queue.run_daily(
        daily_update_callback, time=time(hour=3, minute=30, second=0)
    )

    application.run_polling()


if __name__ == "__main__":
    main()

