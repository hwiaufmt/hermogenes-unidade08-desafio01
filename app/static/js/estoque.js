import { mostrarMensagem, requisitar } from "./api.js";

const mensagem = document.getElementById("mensagem");
const corpoTabela = document.getElementById("lista-materiais");
const aviso = document.getElementById("vazio");

function criarCelula(texto, classe) {
  const celula = document.createElement("td");
  celula.textContent = texto;
  if (classe) celula.className = classe;
  return celula;
}

function criarCelulaStatus(status) {
  const celula = criarCelula(status, "status");
  celula.dataset.status = status;
  return celula;
}

function criarLinha(material) {
  const linha = document.createElement("tr");
  linha.append(
    criarCelula(material.nome),
    criarCelula(material.categoria.nome),
    criarCelula(material.quantidade, "num"),
    criarCelula(material.estoque_minimo, "num"),
    criarCelulaStatus(material.status),
  );
  return linha;
}

function renderizar(materiais) {
  corpoTabela.replaceChildren(...materiais.map(criarLinha));
  aviso.hidden = materiais.length > 0;
}

requisitar("/materiais")
  .then(renderizar)
  .catch((erro) => mostrarMensagem(mensagem, erro.message, "erro"));
