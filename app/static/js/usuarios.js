import { mostrarMensagem, requisitar } from "./api.js";

const mensagem = document.getElementById("mensagem");
const form = document.getElementById("form-usuario");
const tituloForm = document.getElementById("titulo-form-usuario");
const botaoSalvar = document.getElementById("botao-salvar");
const botaoCancelar = document.getElementById("botao-cancelar");
const dicaSenha = document.getElementById("dica-senha");
const lista = document.getElementById("lista-usuarios");

const estado = { emEdicao: null, usuarios: [] };

function formatarCpf(cpf) {
  return `${cpf.slice(0, 3)}.${cpf.slice(3, 6)}.${cpf.slice(6, 9)}-${cpf.slice(9)}`;
}

function criarCelula(texto, classe) {
  const celula = document.createElement("td");
  celula.textContent = texto;
  if (classe) celula.className = classe;
  return celula;
}

function criarBotao(rotulo, aoClicar, classe) {
  const botao = document.createElement("button");
  botao.type = "button";
  botao.textContent = rotulo;
  botao.className = `botao-pequeno ${classe}`;
  botao.addEventListener("click", aoClicar);
  return botao;
}

function criarCelulaSituacao(usuario) {
  const selo = document.createElement("span");
  selo.className = "selo";
  selo.dataset.status = usuario.ativo ? "Disponível" : "Indisponível";
  selo.textContent = usuario.ativo ? "Ativo" : "Inativo";
  const celula = document.createElement("td");
  celula.append(selo);
  return celula;
}

function criarCelulaAcoes(usuario) {
  const celula = document.createElement("td");
  celula.className = "acoes";
  const alternar = usuario.ativo
    ? criarBotao("Inativar", () => alterarSituacao(usuario, "inativar"), "botao-secundario")
    : criarBotao("Reativar", () => alterarSituacao(usuario, "reativar"), "botao-secundario");
  celula.append(criarBotao("Editar", () => iniciarEdicao(usuario), "botao-secundario"), alternar);
  return celula;
}

function criarLinha(usuario) {
  const linha = document.createElement("tr");
  linha.dataset.status = usuario.ativo ? "Disponível" : "Indisponível";
  linha.append(
    criarCelula(usuario.nome),
    criarCelula(formatarCpf(usuario.cpf), "sem-quebra"),
    criarCelula(usuario.email),
    criarCelula(usuario.perfil),
    criarCelulaSituacao(usuario),
    criarCelulaAcoes(usuario),
  );
  return linha;
}

function renderizarLista() {
  lista.replaceChildren(...estado.usuarios.map(criarLinha));
}

async function carregarUsuarios() {
  estado.usuarios = await requisitar("/usuarios");
  renderizarLista();
}

function modoCadastro() {
  estado.emEdicao = null;
  form.reset();
  form.elements.cpf.disabled = false;
  tituloForm.textContent = "Novo usuário";
  botaoSalvar.textContent = "Cadastrar usuário";
  botaoCancelar.hidden = true;
  dicaSenha.textContent = dicaSenha.dataset.cadastro;
}

function iniciarEdicao(usuario) {
  estado.emEdicao = usuario;
  form.elements.nome.value = usuario.nome;
  form.elements.cpf.value = formatarCpf(usuario.cpf);
  form.elements.cpf.disabled = true;
  form.elements.email.value = usuario.email;
  form.elements.perfil.value = usuario.perfil;
  form.elements.senha.value = "";
  tituloForm.textContent = `Editar usuário: ${usuario.nome}`;
  botaoSalvar.textContent = "Salvar alterações";
  botaoCancelar.hidden = false;
  dicaSenha.textContent = "Deixe em branco para manter a senha atual.";
  form.elements.nome.focus();
}

function dadosDoFormulario() {
  return {
    nome: form.elements.nome.value,
    cpf: form.elements.cpf.value,
    email: form.elements.email.value,
    perfil: form.elements.perfil.value,
    senha: form.elements.senha.value,
  };
}

function corpoDeCadastro() {
  const { senha, ...demais } = dadosDoFormulario();
  // Sem senha informada, o servidor usa a senha padrão.
  return senha === "" ? demais : { ...demais, senha };
}

function corpoDeEdicao() {
  const { nome, email, perfil, senha } = dadosDoFormulario();
  return { nome, email, perfil, senha: senha === "" ? null : senha };
}

async function salvar(evento) {
  evento.preventDefault();
  const edicao = estado.emEdicao;
  try {
    const usuario = edicao
      ? await requisitar(`/usuarios/${edicao.id}`, opcoesJson("PUT", corpoDeEdicao()))
      : await requisitar("/usuarios", opcoesJson("POST", corpoDeCadastro()));
    await carregarUsuarios();
    mostrarMensagem(
      mensagem,
      edicao ? `Usuário "${usuario.nome}" atualizado.` : `Usuário "${usuario.nome}" cadastrado.`,
      "sucesso",
    );
    modoCadastro();
  } catch (erro) {
    mostrarMensagem(mensagem, erro.message, "erro");
  }
}

function opcoesJson(metodo, corpo) {
  return {
    method: metodo,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  };
}

async function alterarSituacao(usuario, acao) {
  try {
    const atualizado = await requisitar(`/usuarios/${usuario.id}/${acao}`, { method: "POST" });
    await carregarUsuarios();
    const verbo = acao === "inativar" ? "inativado" : "reativado";
    mostrarMensagem(mensagem, `Usuário "${atualizado.nome}" ${verbo}.`, "sucesso");
  } catch (erro) {
    mostrarMensagem(mensagem, erro.message, "erro");
  }
}

form.addEventListener("submit", salvar);
botaoCancelar.addEventListener("click", modoCadastro);
carregarUsuarios().catch((erro) => mostrarMensagem(mensagem, erro.message, "erro"));
