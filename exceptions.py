class AppError(Exception):
    """Base class for expected, user-facing failures."""


class ConfigurationError(AppError):
    pass


class OxfordError(AppError):
    pass


class OxfordNetworkError(OxfordError):
    pass


class OxfordBlockedError(OxfordError):
    pass


class OxfordStructureError(OxfordError):
    pass


class WordNotFoundError(OxfordError):
    pass


class NotionError(AppError):
    pass


class NotionSchemaError(NotionError):
    pass


class NotionWriteError(NotionError):
    pass
