"""Verify all public Corpulse methods have complete docstrings (DOC-05)."""
import inspect

import corpulse.async_core as ac_module
import corpulse.core as c_module


def test_corpulse_public_methods_have_docstrings():
    """Every public method on Corpulse must have a non-empty __doc__."""
    cls = c_module.Corpulse
    public = [
        name for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
        if not name.startswith("_")
    ]
    missing = [name for name in public if not getattr(cls, name).__doc__]
    assert missing == [], f"Missing docstrings: {missing}"


# Methods that accept parameters beyond 'self' and must document them
_METHODS_WITH_PARAMS = [
    "log_retrieval",
    "log_engagement",
    "log_generation_trace",
    "log_source_update",
    "register_document",
    "get_duplicates",
    "get_suspects",
    "get_generation_traces",
    "to_dataframe",
    "report",
]


def test_corpulse_docstrings_have_args_section():
    """Public methods with parameters must have an Args: section."""
    cls = c_module.Corpulse
    missing_args = []
    for name in _METHODS_WITH_PARAMS:
        method = getattr(cls, name)
        doc = method.__doc__ or ""
        if "Args:" not in doc:
            missing_args.append(name)
    assert missing_args == [], f"Missing Args: section in docstrings: {missing_args}"


def test_async_corpulse_public_methods_have_docstrings():
    """Every public method on AsyncCorpulse must have a non-empty __doc__."""
    cls = ac_module.AsyncCorpulse
    public = [
        name for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
        if not name.startswith("_")
    ]
    missing = [name for name in public if not getattr(cls, name).__doc__]
    assert missing == [], f"Missing docstrings: {missing}"


_ASYNC_METHODS_WITH_PARAMS = [
    "log_retrieval",
    "log_engagement",
    "log_generation_trace",
    "log_source_update",
    "register_document",
    "get_duplicates",
    "get_suspects",
    "get_generation_traces",
    "to_dataframe",
    "report",
]


def test_async_corpulse_docstrings_have_args_section():
    """Async public methods with parameters must have an Args: section."""
    cls = ac_module.AsyncCorpulse
    missing_args = []
    for name in _ASYNC_METHODS_WITH_PARAMS:
        method = getattr(cls, name)
        doc = method.__doc__ or ""
        if "Args:" not in doc:
            missing_args.append(name)
    assert missing_args == [], f"Missing Args: section in docstrings: {missing_args}"
