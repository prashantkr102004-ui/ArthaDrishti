from fastapi import APIRouter

from app.api.v1.routes import (
    advanced,
    analytics,
    assistant,
    auth,
    budgets,
    categories,
    document_search,
    documents,
    goals,
    transactions,
    users,
)

api_router = APIRouter()
api_router.include_router(advanced.router)
api_router.include_router(analytics.router)
api_router.include_router(assistant.router)
api_router.include_router(auth.router)
api_router.include_router(budgets.router)
api_router.include_router(categories.router)
api_router.include_router(document_search.router)
api_router.include_router(documents.router)
api_router.include_router(goals.router)
api_router.include_router(transactions.router)
api_router.include_router(users.router)


@api_router.get("/")
def api_v1_root() -> dict[str, str]:
    return {
        "status": "ok",
        "api_version": "v1",
    }
