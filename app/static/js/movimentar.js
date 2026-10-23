import { enviarJson, mostrarMensagem, requisitar } from "./api.js";

const mensagem = document.getElementById("mensagem");
const form = document.getElementById("form-movimento");
const selectMaterial = document.getElementById("movimento-material");
const painel = document.getElementById("painel-saldo");
const saldoNome = document.getElementById("saldo-nome");
const saldoQuantidade = document.getElementById("saldo-quantidade");
const saldoStatus = document.getElementById("saldo-status");

function renderizarMateriais(materiais, selecionadoId) {
  selectMaterial.replaceChildren(new Option("Selecione…", ""));
  for (const material of materiais) {
    selectMaterial.add(new Option(`${material.nome} (${material.categoria.nome})`, material.id));
  }
  if (selecionadoId) selectMaterial.value = String(selecionadoId);
}

function renderizarSaldo(material) {
  saldoNome.textContent = material.nome;
  saldoQuantidade.textContent = material.quantidade;
  saldoStatus.textContent = material.status;
  saldoStatus.dataset.status = material.status;
  painel.hidden = false;
}

async function mostrarSaldoSelecionado() {
  if (selectMaterial.value === "") {
    painel.hidden = true;
    return;
  }
  try {
    renderizarSaldo(await requisitar(`/materiais/${selectMaterial.value}`));
  } catch (erro) {
    mostrarMensagem(mensagem, erro.message, "erro");
  }
}

function textoSucesso(tipo, quantidade, material) {
  const acao = tipo === "entrada" ? "Entrada" : "Saída";
  return `${acao} de ${quantidade} registrada. Saldo de "${material.nome}": ${material.quantidade} (${material.status}).`;
}

async function registrarMovimento(evento) {
  evento.preventDefault();
  if (selectMaterial.value === "") {
    mostrarMensagem(mensagem, "Selecione um material.", "erro");
    return;
  }
  const tipo = form.elements.tipo.value;
  const quantidade = Number(form.elements.quantidade.value);
  try {
    const material = await enviarJson(`/materiais/${selectMaterial.value}/${tipo}`, {
      quantidade,
    });
    renderizarSaldo(material);
    mostrarMensagem(mensagem, textoSucesso(tipo, quantidade, material), "sucesso");
    form.elements.quantidade.value = "";
  } catch (erro) {
    mostrarMensagem(mensagem, erro.message, "erro");
    await mostrarSaldoSelecionado();
  }
}

async function iniciar() {
  const materiais = await requisitar("/materiais");
  renderizarMateriais(materiais);
}

selectMaterial.addEventListener("change", mostrarSaldoSelecionado);
form.addEventListener("submit", registrarMovimento);
iniciar().catch((erro) => mostrarMensagem(mensagem, erro.message, "erro"));
