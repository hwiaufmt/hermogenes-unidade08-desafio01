export function criarCelula(texto, classe) {
  const celula = document.createElement("td");
  celula.textContent = texto;
  if (classe) celula.className = classe;
  return celula;
}

export function criarCelulaStatus(status) {
  const selo = document.createElement("span");
  selo.className = "selo";
  selo.dataset.status = status;
  selo.textContent = status;
  const celula = document.createElement("td");
  celula.append(selo);
  return celula;
}

export function criarCabecalho(colunas) {
  const linha = document.createElement("tr");
  for (const [titulo, classe] of colunas) {
    const celula = document.createElement("th");
    celula.scope = "col";
    celula.textContent = titulo;
    if (classe) celula.className = classe;
    linha.append(celula);
  }
  const cabecalho = document.createElement("thead");
  cabecalho.append(linha);
  return cabecalho;
}

export function criarRegiaoRolavel(tabela, tituloId) {
  const regiao = document.createElement("div");
  regiao.className = "tabela-rolavel";
  regiao.tabIndex = 0;
  regiao.setAttribute("role", "region");
  regiao.setAttribute("aria-labelledby", tituloId);
  regiao.append(tabela);
  return regiao;
}
