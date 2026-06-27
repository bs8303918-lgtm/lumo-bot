from aiogram.fsm.state import State, StatesGroup


class AddChannelStates(StatesGroup):
    waiting_for_channel = State()


class SetInterestStates(StatesGroup):
    waiting_for_interest = State()


class TestPostStates(StatesGroup):
    waiting_for_text = State()
