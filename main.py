#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging
import math
import os
import sys
from functools import wraps

import requests
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler)

LIST_OF_DOCTORS = [353341197, 777300358, 724115614, 691609650, 951862290]

logging.basicConfig(format='%(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def start(update, context):
    update.message.reply_text("Welcome to Emergency Transit Protocol!")
    reply_keyboard = [[
        "♥️ Heart",
        "🤰 Pregnancy"],
        ["🧠 Brain",
         "🤢 Stomach"
         ]]
    problem_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text("what speciality are you looking in a doctor?\nChoose from below:",
                              reply_markup=problem_markup)


def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_DOCTORS:
            print("Unauthorized access denied for {}.".format(user_id))
            return
        return func(update, context, *args, **kwargs)

    return wrapped


def callback_query_handler(update, context):
    user_id = update.effective_user.id
    message_id = update.callback_query.message.message_id
    query = update.callback_query.data.split(";")
    if query[0] == "yeah":
        patient_id = query[1]
        context.bot.edit_message_text(
            text=f"You have accepted the request with patient id: {patient_id}.",
            chat_id=user_id,
            message_id=message_id,
        )
        context.bot.send_message(chat_id=patient_id, text=f"Doctor with id {user_id} has accepted your request")
    elif query[0] == "nope":
        context.bot.edit_message_text(
            text=f"You have declined their request.",
            chat_id=user_id,
            message_id=message_id,
        )


def scene_handler(update, context):
    chat_id = update.message.chat_id
    text = update.message.text
    e = ["♥️", "🤰", "🧠", "🤢"]
    if any(x in text for x in e):
        issue = text
        context.user_data['type'] = issue
    location_keyboard = telegram.KeyboardButton(text="📍 Send location", request_location=True)
    custom_keyboard = [[location_keyboard]]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)
    context.bot.send_message(chat_id=chat_id,
                             text="Would you mind sharing your location? 🗺",
                             reply_markup=reply_markup)


def distance(x, y):
    x1, y1 = x[0], x[1]
    x2, y2 = y[0], y[1]
    dist = math.hypot(x2 - x1, y2 - y1)
    return dist


def find_doctors(issue, location):
    coordinate = location
    coordinates_list = [(11.6702634, 72.313323), (31.67342698, 78.465323)]
    nearest = min(coordinates_list, key=lambda x: distance(x, coordinate))
    return nearest


def reverse_geocode(location):
    lon = location[1]
    lat = location[0]
    params = (
        ('lon', str(lon)),
        ('lat', str(lat)),)
    response = requests.get('http://photon.komoot.de/reverse', params=params)
    response = json.loads(response.text)
    return response


def location_handler(update, context):
    chat_id = update.message.chat_id
    location = (float(update.message.location.latitude), float(update.message.location.longitude))
    issue = context.user_data['type']
    # closest = find_doctors(issue, location)
    update.message.reply_text("Doctors have been informed.", reply_markup=telegram.ReplyKeyboardRemove())
    x = reverse_geocode(location)
    try:
        name = x['features'][0]['properties']['name']
    except KeyError:
        name = "{}, {}".format(float(update.message.location.latitude), float(update.message.location.longitude))
    state = x['features'][0]['properties']['state']
    postcode = x['features'][0]['properties']['postcode']
    keyboard = [[InlineKeyboardButton("✅", callback_data=f'yeah;{chat_id}'),
                     InlineKeyboardButton("❌", callback_data='nope')]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=LIST_OF_DOCTORS[2],
                                text=f"A patient at {name} in {state}, {postcode} of {issue} emergency.",
                                  reply_markup=reply_markup)
    context.bot.send_message(chat_id=LIST_OF_DOCTORS[3],
                                 text=f"A patient at {name} in {state}, {postcode} of {issue} emergency.",
                                 reply_markup=reply_markup)
    context.user_data.clear()


def help_handler(update, context):
    update.message.reply_text('This is a bot to help you connect with nearest doctors around you based on '
                              'location and confirm their availability for a specified problem in order to avoid '
                              'hassle after reaching the hospital!')


def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    try:
        token = sys.argv[1]
    except IndexError:
        token = os.environ.get("TOKEN")
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start, pass_user_data=True))
    dp.add_handler(CommandHandler("help", help_handler))
    dp.add_handler(MessageHandler(Filters.text, scene_handler, pass_user_data=True))
    dp.add_handler((CallbackQueryHandler(callback_query_handler)))
    dp.add_handler(MessageHandler(~Filters.text & (~Filters.location), find_doctors))
    dp.add_handler(MessageHandler(Filters.location, location_handler, pass_user_data=True))
    dp.add_error_handler(error)
    updater.start_polling()
    logger.info("Ready to rock..!")
    updater.idle()


if __name__ == '__main__':
    main()
