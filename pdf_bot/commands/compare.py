import os
import tempfile

import pdf_diff
from pdf_diff import NoDifferenceError
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, CANCEL, PDF_INVALID_FORMAT, PDF_OK, TEXT_FILTER
from pdf_bot.language import set_lang
from pdf_bot.utils import cancel, check_pdf, check_user_data, send_result_file

WAIT_FIRST = 0
WAIT_SECOND = 1
COMPARE_ID = "compare_id"


def compare_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("compare", compare)],
        states={
            WAIT_FIRST: [MessageHandler(Filters.document, check_first_doc)],
            WAIT_SECOND: [MessageHandler(Filters.document, check_second_doc)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(TEXT_FILTER, check_text),
        ],
        allow_reentry=True,
    )

    return conv_handler


def compare(update, context):
    return ask_first_doc(update, context)


def ask_first_doc(update, context):
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup(
        [[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(
        "{desc_1}\n\n{desc_2}".format(
            desc_1=_("Send me one of the PDF files that you'll like to compare"),
            desc_2=_("Note that I can only look for text differences"),
        ),
        reply_markup=reply_markup,
    )

    return WAIT_FIRST


def check_text(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text == _(BACK):
        return ask_first_doc(update, context)
    if text == _(CANCEL):
        return cancel(update, context)

    return None


def check_first_doc(update, context):
    result = check_pdf(update, context)
    if result == PDF_INVALID_FORMAT:
        return WAIT_FIRST
    if result != PDF_OK:
        return ConversationHandler.END

    _ = set_lang(update, context)
    context.user_data[COMPARE_ID] = update.effective_message.document.file_id

    reply_markup = ReplyKeyboardMarkup(
        [[_(BACK), _(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(
        _("Send me the other PDF file that you'll like to compare"),
        reply_markup=reply_markup,
    )

    return WAIT_SECOND


def check_second_doc(update, context):
    if not check_user_data(update, context, COMPARE_ID):
        return ConversationHandler.END

    result = check_pdf(update, context)
    if result == PDF_INVALID_FORMAT:
        return WAIT_SECOND
    if result != PDF_OK:
        return ConversationHandler.END

    return compare_pdf(update, context)


def compare_pdf(update, context):
    _ = set_lang(update, context)
    message = update.effective_message
    message.reply_text(
        _("Comparing your PDF files"), reply_markup=ReplyKeyboardRemove()
    )

    with tempfile.NamedTemporaryFile() as tf1, tempfile.NamedTemporaryFile() as tf2:
        # Download PDF files
        user_data = context.user_data
        first_file_id = user_data[COMPARE_ID]
        first_file = context.bot.get_file(first_file_id)
        first_file.download(custom_path=tf1.name)
        second_file = message.document.get_file()
        second_file.download(custom_path=tf2.name)

        try:
            with tempfile.TemporaryDirectory() as dir_name:
                out_fn = os.path.join(dir_name, "Differences.png")
                pdf_diff.main(files=[tf1.name, tf2.name], out_file=out_fn)
                send_result_file(update, context, out_fn, TaskType.compare_pdf)
        except NoDifferenceError:
            message.reply_text(
                _("There are no text differences between your PDF files")
            )

    # Clean up memory and files
    if user_data[COMPARE_ID] == first_file_id:
        del user_data[COMPARE_ID]

    return ConversationHandler.END
