import warnings

try:
    from langchain_core._api.deprecation import LangChainPendingDeprecationWarning
except Exception:
    LangChainPendingDeprecationWarning = None

if LangChainPendingDeprecationWarning is not None:
    warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)
else:
    warnings.filterwarnings("ignore", message=r".*allowed_objects.*")

warnings.filterwarnings(
    "ignore",
    message=r".*ast\.NameConstant is deprecated.*",
    category=DeprecationWarning,
)
