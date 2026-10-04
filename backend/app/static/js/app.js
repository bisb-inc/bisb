document.body.addEventListener("htmx:responseError", (event) => {
  const target = event.detail.target;
  if (!target) return;

  const message = document.createElement("p");
  message.className = "text-sm text-danger";
  message.setAttribute("role", "alert");
  message.textContent = "Não foi possível concluir a solicitação. Revise os dados e tente novamente.";
  target.replaceChildren(message);
});

document.body.addEventListener("htmx:sendError", (event) => {
  const target = event.detail.target;
  if (!target) return;

  const message = document.createElement("p");
  message.className = "text-sm text-danger";
  message.setAttribute("role", "alert");
  message.textContent = "A conexão falhou. Verifique o servidor e tente novamente.";
  target.replaceChildren(message);
});

document.body.addEventListener("htmx:afterSwap", (event) => {
  if (event.detail.target?.id === "wizard-panel") {
    event.detail.target.querySelector("#wizard-step-content")?.focus();
  }
});

document.body.addEventListener("submit", (event) => {
  if (!(event.target instanceof HTMLFormElement) || event.target.id !== "wizard-final-form") return;
  const button = event.target.querySelector('button[type="submit"]');
  if (!button) return;
  button.disabled = true;
  button.textContent = button.dataset.loadingLabel || "Processando…";
  event.target.setAttribute("aria-busy", "true");
  const status = event.target.querySelector('[role="status"]');
  if (status) status.textContent = button.textContent;
});

document.body.addEventListener("change", (event) => {
  const input = event.target;
  if (input instanceof HTMLSelectElement && input.name === "period") {
    const form = input.closest("form");
    const dateFields = form?.querySelectorAll('[name="from_date"], [name="to_date"]');
    const custom = input.value === "custom";
    if (custom) form?.querySelector("details")?.setAttribute("open", "");
    dateFields?.forEach((field) => {
      if (field instanceof HTMLInputElement) field.required = custom;
    });
    return;
  }
  if (!(input instanceof HTMLInputElement) || input.name !== "period" || input.value === "custom") return;
  const form = input.closest("form");
  const from = form?.querySelector('[name="from_date"]');
  const to = form?.querySelector('[name="to_date"]');
  if (!(from instanceof HTMLInputElement) || !(to instanceof HTMLInputElement)) return;

  const end = new Date();
  const start = new Date(end);
  if (input.value === "week") start.setDate(start.getDate() - 6);
  else {
    const months = input.value === "month" ? 1 : 3;
    const day = start.getDate();
    start.setDate(1);
    start.setMonth(start.getMonth() - months);
    const lastDay = new Date(start.getFullYear(), start.getMonth() + 1, 0).getDate();
    start.setDate(Math.min(day, lastDay));
  }
  const toIso = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };
  from.value = toIso(start);
  to.value = toIso(end);
});
