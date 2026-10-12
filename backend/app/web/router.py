from fastapi import APIRouter

from app.web.routes import event_analysis, pages, setup, wizard, workspace

router = APIRouter()
# O wizard precisa vir antes do workspace: /ui/analyses/new não pode cair em /ui/analyses/{id}.
router.include_router(pages.router)
router.include_router(wizard.router)
router.include_router(workspace.router)
router.include_router(setup.router)
router.include_router(event_analysis.router)
