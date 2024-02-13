from premia.utils import types


class ConfigError(Exception):
    """Custom exception class for config directory related errors."""

    pass


class MissingAiError(ConfigError):
    def __init__(self, message="No AI model has been set up yet."):
        self.message = message
        super().__init__(self.message)


class MissingLocalAiError(ConfigError):
    def __init__(self, message="No local AI has been set up yet."):
        self.message = message
        super().__init__(self.message)


class MissingRemoteAiError(ConfigError):
    def __init__(self, message="No remote AI has been set up yet."):
        self.message = message
        super().__init__(self.message)


class MissingDbError(ConfigError):
    def __init__(
        self, message="Premia has not been connected to a database yet."
    ):
        self.message = message
        super().__init__(self.message)


class MissingInstrumentError(ConfigError):
    def __init__(
        self, instrument: types.InstrumentType, message: str | None = None
    ):
        self.instrument = instrument
        self.message = (
            message
            or f"{instrument.value.capitalize()} have not been set up yet."
        )
        super().__init__(self.message)
