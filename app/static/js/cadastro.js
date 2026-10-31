import { enviarJson, mostrarMensagem, requisitar } from "./api.js";

const mensagem = document.getElementById("mensagem");
const formMaterial = document.getElementById("form-material");
const formCategoria = document.getElementById("form-categoria");
const selectCategoria = document.getElementById("material-categoria");
const secaoCategorias = document.getElementById("secao-categorias");
const listaCategorias = document.getElementById("lista-categorias");
const dialogoEdicao = document.getElementById("dialogo-edicao");
const formEdicao = document.getElementById("form-edicao");
const erroEdicao = document.getElementById("erro-edicao");
const dialogoConfirmacao = document.getElementById("dialogo-confirmacao");
const textoConfirmacao = document.getElementById("texto-confirmacao");

const dialogoExclusao = document.getElementById("dialogo-exclusao-categoria");
const textoExclusao = document.getElementById("texto-exclusao-categoria");

const podeEditar = secaoCategorias.dataset.podeEditar === "sim";
const podeExcluir = secaoCategorias.dataset.podeExcluir === "sim";
const estado = { emEdicao: null, novoNome: "", emExclusao: null };

function criarCelula(texto, classe) {
  const celula = document.createElement("td");
  celula.textContent = texto;
  if (classe) celula.className = classe;
  return celula;
}

function criarBotaoEditar(categoria) {
  const botao = document.createElement("button");
  botao.type = "button";
  botao.textContent = "Editar";
  botao.className = "botao-pequeno botao-secundario";
  botao.dataset.categoriaId = categoria.id;
  botao.setAttribute("aria-label", `Editar a categoria ${categoria.nome}`);
  botao.addEventListener("click", () => abrirEdicao(categoria));
  return botao;
}

function criarBotaoExcluir(categoria) {
  const botao = document.createElement("button");
  botao.type = "button";
  botao.textContent = "Excluir";
  botao.className = "botao-pequeno botao-secundario";
  botao.dataset.categoriaId = categoria.id;
  botao.setAttribute("aria-label", `Excluir a categoria ${categoria.nome}`);
  botao.addEventListener("click", () => abrirExclusao(categoria));
  return botao;
}

function criarLinhaCategoria(categoria) {
  const linha = document.createElement("tr");
  linha.append(criarCelula(categoria.nome), criarCelula(categoria.total_materiais, "num"));
  if (podeEditar || podeExcluir) {
    const acoes = criarCelula("", "acoes");
    if (podeEditar) acoes.append(criarBotaoEditar(categoria));
    if (podeExcluir) acoes.append(criarBotaoExcluir(categoria));
    linha.append(acoes);
  }
  return linha;
}

function renderizarCategorias(categorias, selecionadaId) {
  selectCategoria.replaceChildren(new Option("Selecione…", ""));
  for (const categoria of categorias) {
    selectCategoria.add(new Option(categoria.nome, categoria.id));
  }
  if (selecionadaId) selectCategoria.value = String(selecionadaId);
  listaCategorias.replaceChildren(...categorias.map(criarLinhaCategoria));
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
    await carregarCategorias(); // atualiza o total de materiais de cada categoria
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

function abrirEdicao(categoria) {
  estado.emEdicao = categoria;
  formEdicao.elements.nome.value = categoria.nome;
  erroEdicao.hidden = true;
  dialogoEdicao.showModal();
  formEdicao.elements.nome.select();
}

function gravarEdicao(confirmar) {
  const dados = { nome: estado.novoNome, confirmar };
  return enviarJson(`/categorias/${estado.emEdicao.id}`, dados, "PUT");
}

function precisaConfirmar(erro) {
  return erro.status === 409 && Number.isInteger(erro.corpo?.afetados);
}

function pedirConfirmacao(erro) {
  textoConfirmacao.textContent = erro.corpo.detail;
  dialogoEdicao.close();
  dialogoConfirmacao.showModal();
}

async function concluirEdicao(categoria) {
  const anterior = estado.emEdicao;
  await carregarCategorias(selectCategoria.value);
  const afetados =
    categoria.total_materiais > 0 ? ` Registros afetados: ${categoria.total_materiais}.` : "";
  mostrarMensagem(
    mensagem,
    `Categoria "${anterior.nome}" alterada para "${categoria.nome}".${afetados}`,
    "sucesso",
  );
  listaCategorias.querySelector(`[data-categoria-id="${categoria.id}"]`)?.focus();
}

async function salvarEdicao(evento) {
  evento.preventDefault();
  estado.novoNome = formEdicao.elements.nome.value;
  try {
    const categoria = await gravarEdicao(false);
    dialogoEdicao.close();
    await concluirEdicao(categoria);
  } catch (erro) {
    if (precisaConfirmar(erro)) {
      pedirConfirmacao(erro);
      return;
    }
    erroEdicao.textContent = erro.message;
    erroEdicao.hidden = false;
  }
}

async function confirmarEdicao() {
  try {
    const categoria = await gravarEdicao(true);
    dialogoConfirmacao.close();
    await concluirEdicao(categoria);
  } catch (erro) {
    dialogoConfirmacao.close();
    mostrarMensagem(mensagem, erro.message, "erro");
  }
}

function voltarParaEdicao() {
  dialogoConfirmacao.close();
  formEdicao.elements.nome.value = estado.novoNome;
  erroEdicao.hidden = true;
  dialogoEdicao.showModal();
  formEdicao.elements.nome.focus();
}

function abrirExclusao(categoria) {
  estado.emExclusao = categoria;
  textoExclusao.textContent =
    `Excluir a categoria "${categoria.nome}"? Ela deixa de aparecer no sistema ` +
    "e o nome poderá ser usado por uma nova categoria. Os materiais dela sem saldo " +
    "serão excluídos junto; se algum tiver saldo, a exclusão é recusada.";
  dialogoExclusao.showModal();
}

// O servidor decide: com materiais ativos ele recusa (409) e a mensagem vem pronta.
async function confirmarExclusao() {
  const categoria = estado.emExclusao;
  try {
    await requisitar(`/categorias/${categoria.id}`, { method: "DELETE" });
    dialogoExclusao.close();
    await carregarCategorias(selectCategoria.value);
    mostrarMensagem(mensagem, `Categoria "${categoria.nome}" excluída.`, "sucesso");
  } catch (erro) {
    dialogoExclusao.close();
    mostrarMensagem(mensagem, erro.message, "erro");
  }
}

formMaterial.addEventListener("submit", cadastrarMaterial);
formCategoria.addEventListener("submit", criarCategoria);
formEdicao.addEventListener("submit", salvarEdicao);
document
  .getElementById("botao-cancelar-edicao")
  .addEventListener("click", () => dialogoEdicao.close());
document.getElementById("botao-confirmar-edicao").addEventListener("click", confirmarEdicao);
document.getElementById("botao-voltar-edicao").addEventListener("click", voltarParaEdicao);
document.getElementById("botao-confirmar-exclusao-categoria").addEventListener("click", confirmarExclusao);
document
  .getElementById("botao-cancelar-exclusao-categoria")
  .addEventListener("click", () => dialogoExclusao.close());
carregarCategorias().catch((erro) => mostrarMensagem(mensagem, erro.message, "erro"));
