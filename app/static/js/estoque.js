import { mostrarMensagem, requisitar } from "./api.js";

const mensagem = document.getElementById("mensagem");
const filtro = document.getElementById("filtro-categoria");
const grupos = document.getElementById("grupos");
const aviso = document.getElementById("vazio");

function criarCelula(texto, classe) {
  const celula = document.createElement("td");
  celula.textContent = texto;
  if (classe) celula.className = classe;
  return celula;
}

function criarCelulaStatus(status) {
  const selo = document.createElement("span");
  selo.className = "selo";
  selo.dataset.status = status;
  selo.textContent = status;
  const celula = document.createElement("td");
  celula.append(selo);
  return celula;
}

function criarLinha(material) {
  const linha = document.createElement("tr");
  linha.dataset.status = material.status;
  linha.append(
    criarCelula(material.nome),
    criarCelula(material.quantidade, "num"),
    criarCelula(material.estoque_minimo, "num"),
    criarCelulaStatus(material.status),
  );
  return linha;
}

function criarCabecalho() {
  const linha = document.createElement("tr");
  for (const [titulo, classe] of [
    ["Material", ""],
    ["Saldo", "num"],
    ["Mínimo", "num"],
    ["Status", ""],
  ]) {
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

function criarGrupo(categoria, materiais, indice) {
  const tituloId = `grupo-${indice}`;
  const secao = document.createElement("section");
  secao.setAttribute("aria-labelledby", tituloId);

  const titulo = document.createElement("h2");
  titulo.id = tituloId;
  titulo.textContent = categoria;

  const corpo = document.createElement("tbody");
  corpo.append(...materiais.map(criarLinha));
  const tabela = document.createElement("table");
  tabela.append(criarCabecalho(), corpo);

  const rolavel = document.createElement("div");
  rolavel.className = "tabela-rolavel";
  rolavel.tabIndex = 0;
  rolavel.setAttribute("role", "region");
  rolavel.setAttribute("aria-labelledby", tituloId);
  rolavel.append(tabela);

  secao.append(titulo, rolavel);
  return secao;
}

function agruparPorCategoria(materiais) {
  const porCategoria = new Map();
  for (const material of materiais) {
    const nome = material.categoria.nome;
    if (!porCategoria.has(nome)) porCategoria.set(nome, []);
    porCategoria.get(nome).push(material);
  }
  return [...porCategoria].sort(([a], [b]) => a.localeCompare(b, "pt-BR"));
}

function textoVazio() {
  if (filtro.value === "") return "Nenhum material cadastrado.";
  return "Nenhum material nesta categoria.";
}

function renderizar(materiais) {
  const porCategoria = agruparPorCategoria(materiais);
  grupos.replaceChildren(
    ...porCategoria.map(([categoria, itens], indice) => criarGrupo(categoria, itens, indice)),
  );
  aviso.textContent = textoVazio();
  aviso.hidden = materiais.length > 0;
}

async function carregarMateriais() {
  const consulta = filtro.value === "" ? "" : `?categoria_id=${filtro.value}`;
  try {
    renderizar(await requisitar(`/materiais${consulta}`));
  } catch (erro) {
    mostrarMensagem(mensagem, erro.message, "erro");
  }
}

async function carregarCategorias() {
  const categorias = await requisitar("/categorias");
  for (const categoria of categorias) {
    filtro.add(new Option(categoria.nome, categoria.id));
  }
}

async function iniciar() {
  try {
    await carregarCategorias();
  } catch (erro) {
    mostrarMensagem(mensagem, erro.message, "erro");
  }
  await carregarMateriais();
}

filtro.addEventListener("change", carregarMateriais);
iniciar();
