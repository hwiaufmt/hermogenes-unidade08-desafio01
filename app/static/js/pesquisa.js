import { mostrarMensagem, requisitar } from "./api.js";
import {
  criarCabecalho,
  criarCelula,
  criarCelulaDisponivel,
  criarRegiaoRolavel,
} from "./tabelas.js";

const ESPERA_DA_BUSCA_MS = 250;

const mensagem = document.getElementById("mensagem");
const formFiltros = document.getElementById("filtros");
const filtroBusca = document.getElementById("filtro-busca");
const filtroCategoria = document.getElementById("filtro-categoria");
const filtroDisponivel = document.getElementById("filtro-disponivel");
const grupos = document.getElementById("grupos");
const aviso = document.getElementById("vazio");
const resumo = document.getElementById("resumo");
const dialogoExclusao = document.getElementById("dialogo-exclusao");
const textoExclusao = document.getElementById("texto-exclusao");
const botaoConfirmarExclusao = document.getElementById("botao-confirmar-exclusao");

const podeExcluir = grupos.dataset.podeExcluir === "sim";
const estado = { emExclusao: null };

function colunasDaTabela() {
  const colunas = [
    ["Material", ""],
    ["Saldo", "num"],
    ["Mínimo", "num"],
    ["Disponível", ""],
  ];
  return podeExcluir ? [...colunas, ["Ações", ""]] : colunas;
}

function criarBotaoExcluir(material) {
  const botao = document.createElement("button");
  botao.type = "button";
  botao.textContent = "Excluir";
  botao.className = "botao-pequeno botao-secundario";
  botao.dataset.materialId = material.id;
  botao.setAttribute("aria-label", `Excluir o material ${material.nome}`);
  botao.addEventListener("click", () => abrirExclusao(material.id));
  return botao;
}

function criarLinha(material) {
  const linha = document.createElement("tr");
  linha.dataset.status = material.status;
  linha.append(
    criarCelula(material.nome),
    criarCelula(material.quantidade, "num"),
    criarCelula(material.estoque_minimo, "num"),
    criarCelulaDisponivel(material.status),
  );
  if (podeExcluir) {
    const acoes = criarCelula("", "acoes");
    acoes.append(criarBotaoExcluir(material));
    linha.append(acoes);
  }
  return linha;
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
  tabela.append(criarCabecalho(colunasDaTabela()), corpo);

  secao.append(titulo, criarRegiaoRolavel(tabela, tituloId));
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

function haFiltroAtivo() {
  return (
    filtroBusca.value.trim() !== "" ||
    filtroCategoria.value !== "" ||
    filtroDisponivel.value !== ""
  );
}

function textoVazio() {
  return haFiltroAtivo()
    ? "Nenhum material encontrado com esses filtros."
    : "Nenhum material cadastrado.";
}

function textoResumo(total) {
  return total === 1 ? "1 material encontrado." : `${total} materiais encontrados.`;
}

function renderizar(materiais) {
  const porCategoria = agruparPorCategoria(materiais);
  grupos.replaceChildren(
    ...porCategoria.map(([categoria, itens], indice) => criarGrupo(categoria, itens, indice)),
  );
  aviso.textContent = textoVazio();
  aviso.hidden = materiais.length > 0;
  resumo.textContent = materiais.length > 0 ? textoResumo(materiais.length) : "";
}

function montarConsulta() {
  const parametros = new URLSearchParams();
  const busca = filtroBusca.value.trim();
  if (busca !== "") parametros.set("q", busca);
  if (filtroCategoria.value !== "") parametros.set("categoria_id", filtroCategoria.value);
  // O valor do filtro é o status da API ("Disponível"/"Indisponível"); a tela mostra Sim/Não.
  if (filtroDisponivel.value !== "") parametros.set("status", filtroDisponivel.value);
  const texto = parametros.toString();
  return texto === "" ? "" : `?${texto}`;
}

async function carregarMateriais() {
  try {
    renderizar(await requisitar(`/materiais${montarConsulta()}`));
  } catch (erro) {
    mostrarMensagem(mensagem, erro.message, "erro");
  }
}

async function carregarCategorias() {
  const categorias = await requisitar("/categorias");
  for (const categoria of categorias) {
    filtroCategoria.add(new Option(categoria.nome, categoria.id));
  }
}

function aoDigitarBusca() {
  let temporizador = null;
  return () => {
    clearTimeout(temporizador);
    temporizador = setTimeout(carregarMateriais, ESPERA_DA_BUSCA_MS);
  };
}

function descreverExclusao(material) {
  const base = "Ao excluir, ele deixa de aparecer no sistema; as movimentações já registradas continuam guardadas.";
  if (material.quantidade === 0) {
    return `O material "${material.nome}" está sem saldo. ${base}`;
  }
  const unidades = material.quantidade === 1 ? "unidade" : "unidades";
  return `O material "${material.nome}" tem ${material.quantidade} ${unidades} em estoque. ${base}`;
}

// Busca o material de novo: o saldo mostrado na confirmação é o de agora.
async function abrirExclusao(materialId) {
  try {
    const material = await requisitar(`/materiais/${materialId}`);
    estado.emExclusao = material;
    textoExclusao.textContent = descreverExclusao(material);
    dialogoExclusao.showModal();
  } catch (erro) {
    mostrarMensagem(mensagem, erro.message, "erro");
    await carregarMateriais();
  }
}

async function confirmarExclusao() {
  const material = estado.emExclusao;
  botaoConfirmarExclusao.disabled = true;
  try {
    await requisitar(`/materiais/${material.id}?confirmar=true`, { method: "DELETE" });
    dialogoExclusao.close();
    mostrarMensagem(mensagem, `Material "${material.nome}" excluído.`, "sucesso");
  } catch (erro) {
    dialogoExclusao.close();
    mostrarMensagem(mensagem, erro.message, "erro");
  } finally {
    botaoConfirmarExclusao.disabled = false;
  }
  await carregarMateriais();
}

async function iniciar() {
  try {
    await carregarCategorias();
  } catch (erro) {
    mostrarMensagem(mensagem, erro.message, "erro");
  }
  await carregarMateriais();
}

formFiltros.addEventListener("submit", (evento) => evento.preventDefault());
filtroBusca.addEventListener("input", aoDigitarBusca());
filtroCategoria.addEventListener("change", carregarMateriais);
filtroDisponivel.addEventListener("change", carregarMateriais);
botaoConfirmarExclusao.addEventListener("click", confirmarExclusao);
document
  .getElementById("botao-cancelar-exclusao")
  .addEventListener("click", () => dialogoExclusao.close());
iniciar();
