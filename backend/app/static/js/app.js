document.body.addEventListener("htmx:responseError", (event) => {
  const target = event.detail.target;
  if (!target) return;

  const message = document.createElement("p");
  message.className = "text-sm text-danger";
  message.setAttribute("role", "status");
  message.textContent = "Não foi possível concluir a solicitação. Revise os dados e tente novamente.";
  target.replaceChildren(message);
});

document.body.addEventListener("htmx:sendError", (event) => {
  const target = event.detail.target;
  if (!target) return;

  const message = document.createElement("p");
  message.className = "text-sm text-danger";
  message.setAttribute("role", "status");
  message.textContent = "A conexão falhou. Verifique o servidor e tente novamente.";
  target.replaceChildren(message);
});
