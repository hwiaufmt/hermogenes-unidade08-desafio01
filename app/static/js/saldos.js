import { mostrarMensagem, requisitar } from "./api.js";
import {
  criarCelula,
  criarCelulaDisponivel,
  criarRegiaoRolavel,
  criarSecaoDeCategoria,
  criarTabela,
} from "./tabelas.js";

const COLUNAS = [
  ["Material", ""],
  ["Quantidade", "num"],
  ["Disponível", ""],
];

const mensagem = document.getElementById("mensagem");
const botaoAtualizar = document.getElementById("botao-atualizar");
const grupos = document.getElementById("grupos");
const aviso = document.getElementById("vazio");
const totalMateriais = document.getElementById("total-materiais");
const totalUnidades = document.getElementById("total-unidades");
const totalIndisponiveis = document.getElementById("total-indisponiveis");

function renderizarTotais(totais) {
  totalMateriais.textContent = totais.total_materiais;
  totalUnidades.textContent = totais.total_unidades;
  totalIndisponiveis.textContent = totais.total_indisponiveis;
  totalIndisponiveis.dataset.zero = String(totais.total_indisponiveis === 0);
}

function criarLinha(material) {
  const linha = document.createElement("tr");
  linha.dataset.status = material.status;
  linha.append(
    criarCelula(material.nome),
    criarCelula(material.quantidade, "num"),
    criarCelulaDisponivel(material.status),
  );
  return linha;
}

function criarAvisoSemMateriais() {
  const texto = document.createElement("p");
  texto.className = "sem-materiais";
  texto.textContent = "Nenhum material nesta categoria.";
  return texto;
}

function criarConteudo(materiais, tituloId) {
  if (materiais.length === 0) return criarAvisoSemMateriais();
  return criarRegiaoRolavel(criarTabela(COLUNAS, materiais.map(criarLinha)), tituloId);
}

// O servidor já entrega categorias e materiais em ordem alfabética, as categorias
// vazias incluídas, e os totais prontos; aqui só se monta cada seção, como na Pesquisa.
function criarGrupo(saldo, indice) {
  return criarSecaoDeCategoria(indice, saldo.categoria.nome, (tituloId) =>
    criarConteudo(saldo.materiais, tituloId),
  );
}

function renderizar(consulta) {
  renderizarTotais(consulta.totais);
  grupos.replaceChildren(...consulta.categorias.map(criarGrupo));
  aviso.hidden = consulta.categorias.length > 0;
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
