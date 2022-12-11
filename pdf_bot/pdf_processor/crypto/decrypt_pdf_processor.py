from contextlib import contextmanager
from gettext import gettext as _
from typing import Generator, Type

from telegram import Update
from telegram.ext import CallbackContext

from pdf_bot.analytics import TaskType
from pdf_bot.consts import FILE_DATA
from pdf_bot.file_processor import ErrorHandlerType
from pdf_bot.pdf import PdfIncorrectPasswordError

from .abstract_crypto_pdf_processor import AbstractCryptoPDFProcessor


class DecryptPDFProcessor(AbstractCryptoPDFProcessor):
    @property
    def wait_password_state(self) -> str:
        return "wait_decrypt_password"

    @property
    def wait_password_text(self) -> str:
        return _("Send me the password to decrypt your PDF file")

    @property
    def task_type(self) -> TaskType:
        return TaskType.decrypt_pdf

    @property
    def custom_error_handlers(self) -> dict[Type[Exception], ErrorHandlerType]:
        return {PdfIncorrectPasswordError: self._handle_incorrect_password}

    @contextmanager
    def process_file_task(
        self, file_id: str, message_text: str
    ) -> Generator[str, None, None]:
        with self.pdf_service.decrypt_pdf(file_id, message_text) as path:
            yield path

    def _handle_incorrect_password(
        self,
        update: Update,
        context: CallbackContext,
        exception: Exception,
        file_id: str,
        file_name: str,
    ) -> str:
        _ = self.language_service.set_app_language(update, context)
        update.effective_message.reply_text(_(str(exception)))  # type: ignore
        context.user_data[FILE_DATA] = (file_id, file_name)  # type: ignore
        return self.wait_password_state
