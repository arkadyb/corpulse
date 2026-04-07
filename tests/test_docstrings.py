"""Verify all public Memento methods have complete docstrings (DOC-05)."""
import inspect
import rag_memento.memento as m_module


def test_memento_public_methods_have_docstrings():
    """Every public method on Memento must have a non-empty __doc__."""
    cls = m_module.Memento
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
    "log_source_update",
    "register_document",
    "get_duplicates",
    "get_suspects",
    "to_dataframe",
    "report",
]


def test_memento_docstrings_have_args_section():
    """Public methods with parameters must have an Args: section."""
    cls = m_module.Memento
    missing_args = []
    for name in _METHODS_WITH_PARAMS:
        method = getattr(cls, name)
        doc = method.__doc__ or ""
        if "Args:" not in doc:
            missing_args.append(name)
    assert missing_args == [], f"Missing Args: section in docstrings: {missing_args}"
