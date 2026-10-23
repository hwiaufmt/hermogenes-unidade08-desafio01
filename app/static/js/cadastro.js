import { enviarJson, mostrarMensagem, requisitar } from "./api.js";

const mensagem = document.getElementById("mensagem");
const formMaterial = document.getElementById("form-material");
const formCategoria = document.getElementById("form-categoria");
const selectCategoria = document.getElementById("material-categoria");

function renderizarCategorias(categorias, selecionadaId) {
  selectCategoria.replaceChildren(new Option("Selecione…", ""));
  for (const categoria of categorias) {
    selectCategoria.add(new Option(categoria.nome, categoria.id));
  }
  if (selecionadaId) selectCategoria.value = String(selecionadaId);
}

async function carregarCategorias(selecionadaId) {
  const categorias = await requisitar("/categorias");
  renderizarCategorias(categorias, selecionadaId);
}

function lerNumero(campo) {
  return campo.value === "" ? 0 : Number(campo.value);
}

async function cadastrarMaterial(evento) {
  evento.preventDefault();
  const dados = {
    nome: formMaterial.elements.nome.value,
    categoria_id: selectCategoria.value === "" ? null : Number(selectCategoria.value),
    quantidade: lerNumero(formMaterial.elements.quantidade),
    estoque_minimo: lerNumero(formMaterial.elements.estoque_minimo),
  };
  try {
    const material = await enviarJson("/materiais", dados);
    mostrarMensagem(mensagem, `Material "${material.nome}" cadastrado.`, "sucesso");
    formMaterial.reset();
  } catch (erro) {
    mostrarMensagem(mensagem, erro.message, "erro");
  }
}

async function criarCategoria(evento) {
  evento.preventDefault();
  try {
    const categoria = await enviarJson("/categorias", {
      nome: formCategoria.elements.nome.value,
    });
    await carregarCategorias(categoria.id);
    mostrarMensagem(mensagem, `Categoria "${categoria.nome}" criada.`, "sucesso");
    formCategoria.reset();
  } catch (erro) {
    mostrarMensagem(mensagem, erro.message, "erro");
  }
}

formMaterial.addEventListener("submit", cadastrarMaterial);
formCategoria.addEventListener("submit", criarCategoria);
carregarCategorias().catch((erro) => mostrarMensagem(mensagem, erro.message, "erro"));
