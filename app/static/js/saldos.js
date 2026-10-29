import { mostrarMensagem, requisitar } from "./api.js";
import {
  criarCabecalho,
  criarCelula,
  criarCelulaStatus,
  criarRegiaoRolavel,
} from "./tabelas.js";

const mensagem = document.getElementById("mensagem");
const botaoAtualizar = document.getElementById("botao-atualizar");
const resumoCategorias = document.getElementById("resumo-categorias");
const detalhe = document.getElementById("detalhe-saldos");
const aviso = document.getElementById("vazio");
const totalMateriais = document.getElementById("total-materiais");
const totalUnidades = document.getElementById("total-unidades");
const totalIndisponiveis = document.getElementById("total-indisponiveis");

const COLUNAS_MATERIAL = [
  ["Material", ""],
  ["Saldo", "num"],
  ["Mínimo", "num"],
  ["Status", ""],
];

function renderizarTotais(totais) {
  totalMateriais.textContent = totais.total_materiais;
  totalUnidades.textContent = totais.total_unidades;
  totalIndisponiveis.textContent = totais.total_indisponiveis;
  totalIndisponiveis.dataset.zero = String(totais.total_indisponiveis === 0);
}

function criarLinhaResumo(saldo) {
  const linha = document.createElement("tr");
  linha.append(
    criarCelula(saldo.categoria.nome),
    criarCelula(saldo.total_materiais, "num"),
    criarCelula(saldo.total_unidades, "num"),
    criarCelula(saldo.total_indisponiveis, "num"),
  );
  return linha;
}

function criarLinhaMaterial(material) {
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

function criarGrupo(saldo, indice) {
  const tituloId = `saldo-categoria-${indice}`;
  const secao = document.createElement("section");
  secao.setAttribute("aria-labelledby", tituloId);

  const titulo = document.createElement("h3");
  titulo.id = tituloId;
  titulo.textContent = saldo.categoria.nome;

  const corpo = document.createElement("tbody");
  corpo.append(...saldo.materiais.map(criarLinhaMaterial));
  const tabela = document.createElement("table");
  tabela.append(criarCabecalho(COLUNAS_MATERIAL), corpo);

  secao.append(titulo, criarRegiaoRolavel(tabela, tituloId));
  return secao;
}

function renderizar(consulta) {
  renderizarTotais(consulta.totais);
  resumoCategorias.replaceChildren(...consulta.categorias.map(criarLinhaResumo));
  const comMateriais = consulta.categorias.filter((saldo) => saldo.materiais.length > 0);
  detalhe.replaceChildren(...comMateriais.map(criarGrupo));
  aviso.hidden = comMateriais.length > 0;
}

async function carregarSaldos() {
  botaoAtualizar.disabled = true;
  try {
    renderizar(await requisitar("/saldos"));
  } catch (erro) {
    mostrarMensagem(mensagem, erro.message, "erro");
  } finally {
    botaoAtualizar.disabled = false;
  }
}

botaoAtualizar.addEventListener("click", carregarSaldos);
carregarSaldos();
