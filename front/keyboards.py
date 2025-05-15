from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def confirm_delete_keyboard(doc_id_or_filename: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, УДАЛИТЬ", callback_data=f"confirm_delete:{doc_id_or_filename}"),
            InlineKeyboardButton(text="Отмена", callback_data="cancel_delete")]])
