import { mostrarMensagem, requisitar } from "./api.js";
import { criarCelula, criarCelulaDisponivel } from "./tabelas.js";

const mensagem = document.getElementById("mensagem");
const botaoAtualizar = document.getElementById("botao-atualizar");
const corpoSaldos = document.getElementById("corpo-saldos");
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

function criarLinha(material, categoria, inicioDeGrupo) {
  const linha = document.createElement("tr");
  linha.dataset.status = material.status;
  linha.dataset.inicioGrupo = String(inicioDeGrupo);
  linha.append(
    criarCelula(material.nome),
    criarCelula(material.quantidade, "num"),
    criarCelula(categoria.nome),
    criarCelulaDisponivel(material.status),
  );
  return linha;
}

// O servidor já entrega categorias e materiais em ordem alfabética; aqui só se
// "achata" a lista, mantendo os materiais de cada categoria juntos.
function criarLinhas(categorias) {
  const linhas = [];
  for (const saldo of categorias) {
    saldo.materiais.forEach((material, indice) => {
      linhas.push(criarLinha(material, saldo.categoria, indice === 0));
    });
  }
  return linhas;
}

function renderizar(consulta) {
  renderizarTotais(consulta.totais);
  const linhas = criarLinhas(consulta.categorias);
  corpoSaldos.replaceChildren(...linhas);
  aviso.hidden = linhas.length > 0;
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
