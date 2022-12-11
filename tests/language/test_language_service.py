from unittest.mock import MagicMock, patch

from pdf_bot.language import LanguageRepository, LanguageService
from tests.telegram_internal.telegram_test_mixin import TelegramTestMixin


class TestLanguageService(TelegramTestMixin):
    VALID_LANGUAGE = "🇺🇸 English (US)"
    VALID_LANGUAGE_CODE = "en_US"

    def setup_method(self) -> None:
        super().setup_method()
        self.language_repository = MagicMock(spec=LanguageRepository)
        self.language_repository.get_language.return_value = self.VALID_LANGUAGE_CODE

        self.sut = LanguageService(self.language_repository)

        self.gettext_patcher = patch("pdf_bot.language.language_service.gettext")
        self.gettext_patcher.start()

    def teardown_method(self) -> None:
        self.gettext_patcher.stop()
        super().teardown_method()

    def test_send_language_options(self) -> None:
        self.sut.send_language_options(self.telegram_update, self.telegram_context)
        self.telegram_update.effective_message.reply_text.assert_called_once()

    def test_get_user_language(self) -> None:
        actual = self.sut.get_user_language(self.telegram_update, self.telegram_context)

        assert actual == self.VALID_LANGUAGE_CODE
        self.telegram_user_data.__setitem__.assert_called_once_with(
            self.sut.LANGUAGE, self.VALID_LANGUAGE_CODE
        )

    def test_get_user_language_cached(self) -> None:
        cached_lang = "cached_lang"
        user_data = {self.sut.LANGUAGE: cached_lang}
        self.telegram_user_data.__getitem__.side_effect = user_data.__getitem__
        self.telegram_user_data.__contains__.side_effect = user_data.__contains__

        actual = self.sut.get_user_language(self.telegram_update, self.telegram_context)

        assert actual == cached_lang
        self.telegram_user_data.__setitem__.assert_not_called()

    def test_get_user_language_from_query(self) -> None:
        actual = self.sut.get_user_language(
            self.telegram_update, self.telegram_context, self.telegram_callback_query
        )

        assert actual == self.VALID_LANGUAGE_CODE
        self.telegram_user_data.__setitem__.assert_called_once_with(
            self.sut.LANGUAGE, self.VALID_LANGUAGE_CODE
        )

    def test_update_user_language(self) -> None:
        self.telegram_callback_query.data = self.VALID_LANGUAGE
        user_data = {self.sut.LANGUAGE: self.VALID_LANGUAGE_CODE}
        self.telegram_user_data.__getitem__.side_effect = user_data.__getitem__
        self.telegram_user_data.__contains__.side_effect = user_data.__contains__

        self.sut.update_user_language(
            self.telegram_update, self.telegram_context, self.telegram_callback_query
        )

        self.language_repository.upsert_language.assert_called_once_with(
            self.TELEGRAM_QUERY_USER_ID, self.VALID_LANGUAGE_CODE
        )
        self.telegram_user_data.__setitem__.assert_called_once_with(
            self.sut.LANGUAGE, self.VALID_LANGUAGE_CODE
        )

    def test_update_user_language_invalid_language(self) -> None:
        self.telegram_callback_query.data = "clearly_invalid"

        self.sut.update_user_language(
            self.telegram_update, self.telegram_context, self.telegram_callback_query
        )

        self.language_repository.upsert_language.assert_not_called()
        self.telegram_user_data.__setitem__.assert_not_called()
