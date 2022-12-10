from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, CANCEL
from pdf_bot.language import LanguageService
from pdf_bot.pdf import PdfServiceError
from pdf_bot.pdf.pdf_service import PdfService
from pdf_bot.telegram_internal import (
    TelegramService,
    TelegramServiceError,
    TelegramUserDataKeyError,
)


class WatermarkService:
    WAIT_SOURCE_PDF = 0
    WAIT_WATERMARK_PDF = 1
    WATERMARK_KEY = "watermark"

    def __init__(
        self,
        pdf_service: PdfService,
        telegram_service: TelegramService,
        language_service: LanguageService,
    ) -> None:
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service
        self.language_service = language_service

    def ask_source_pdf(self, update: Update, context: CallbackContext) -> int:
        _ = self.language_service.set_app_language(update, context)
        self.telegram_service.reply_with_cancel_markup(
            update,
            context,
            _("Send me the PDF file that you'll like to add a watermark"),
        )
        return self.WAIT_SOURCE_PDF

    def check_source_pdf(self, update: Update, context: CallbackContext) -> int:
        _ = self.language_service.set_app_language(update, context)
        message = update.effective_message

        try:
            doc = self.telegram_service.check_pdf_document(message)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return self.WAIT_SOURCE_PDF

        context.user_data[self.WATERMARK_KEY] = doc.file_id
        reply_markup = ReplyKeyboardMarkup(
            [[_(BACK), _(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
        )
        message.reply_text(
            _("Send me the watermark PDF file"), reply_markup=reply_markup
        )

        return self.WAIT_WATERMARK_PDF

    def add_watermark_to_pdf(self, update: Update, context: CallbackContext) -> int:
        _ = self.language_service.set_app_language(update, context)
        message = update.effective_message

        try:
            doc = self.telegram_service.check_pdf_document(message)
            src_file_id = self.telegram_service.get_user_data(
                context, self.WATERMARK_KEY
            )
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            if isinstance(e, TelegramUserDataKeyError):
                return ConversationHandler.END
            return self.WAIT_WATERMARK_PDF

        message.reply_text(
            _("Adding the watermark onto your PDF file"),
            reply_markup=ReplyKeyboardRemove(),
        )

        try:
            with self.pdf_service.add_watermark_to_pdf(
                src_file_id, doc.file_id
            ) as out_path:
                self.telegram_service.reply_with_file(
                    update, context, out_path, TaskType.watermark_pdf
                )
        except PdfServiceError as e:
            message.reply_text(_(str(e)))

        return ConversationHandler.END

    def check_text(self, update: Update, context: CallbackContext) -> int | None:
        _ = self.language_service.set_app_language(update, context)
        text = update.effective_message.text

        if text == _(BACK):
            return self.ask_source_pdf(update, context)
        if text == _(CANCEL):
            return self.telegram_service.cancel_conversation(update, context)

        return None
