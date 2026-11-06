// A API devolve o status como "Disponível" ou "Indisponível". Nas telas, a
// disponibilidade aparece como "Sim" ou "Não": é só o rótulo, o status vem pronto.
export function rotuloDisponivel(status) {
  return status === "Disponível" ? "Sim" : "Não";
}

export function criarSeloDisponivel(status) {
  const selo = document.createElement("span");
  selo.className = "selo";
  selo.dataset.status = status;
  selo.textContent = rotuloDisponivel(status);
  return selo;
}

export function criarCelula(texto, classe) {
  const celula = document.createElement("td");
  celula.textContent = texto;
  if (classe) celula.className = classe;
  return celula;
}

export function criarCelulaDisponivel(status) {
  const celula = document.createElement("td");
  celula.append(criarSeloDisponivel(status));
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

export function criarTabela(colunas, linhas) {
  const corpo = document.createElement("tbody");
  corpo.append(...linhas);
  const tabela = document.createElement("table");
  tabela.append(criarCabecalho(colunas), corpo);
  return tabela;
}

// Seção de uma categoria, igual na Pesquisa e nos Saldos: título (h2) e o conteúdo
// montado por `montarConteudo(tituloId)`, que recebe o id do título para a acessibilidade.
export function criarSecaoDeCategoria(indice, titulo, montarConteudo) {
  const tituloId = `grupo-${indice}`;
  const secao = document.createElement("section");
  secao.setAttribute("aria-labelledby", tituloId);

  const cabecalho = document.createElement("h2");
  cabecalho.id = tituloId;
  cabecalho.textContent = titulo;

  secao.append(cabecalho, montarConteudo(tituloId));
  return secao;
}
