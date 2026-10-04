# Web UI

Este diretório não contém uma aplicação frontend independente. A Web UI server-rendered faz parte do FastAPI: rotas e templates Jinja2 estão em `backend/app/web/`, e CSS/HTMX compilados ficam em `backend/app/static/`.

Para instalar e executar a interface localmente, consulte [backend/README.md](../backend/README.md). A aplicação usa HTML5, Tailwind CSS, HTMX local e JavaScript vanilla somente quando necessário; não há SPA, React, Vue ou Next.js.
