from cli.utils import types


class PremiaError(Exception):
    """Curstom exception class for Premia errors that should be caught."""

    pass


class InternalError(Exception):
    """Curstom exception class for errors that happen in Premia internal processes without user influence."""

    pass


class MigrationError(PremiaError):
    """Custom exception class for migration errors."""

    pass


class ConfigError(PremiaError):
    """Custom exception class for config directory related errors."""

    pass


class DataImportError(PremiaError):
    """Custom exception class for data import related errors."""

    pass


class DbError(PremiaError):
    """Custom exception class for db related errors."""

    pass


class AiError(PremiaError):
    """Custom exception class for ai related errors."""

    pass


class WizardError(PremiaError):
    """Custom exception class for errors that occur during wizard flows."""

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
