import { enviarJson, mostrarMensagem } from "./api.js";

const form = document.getElementById("form-login");
const mensagem = document.getElementById("mensagem");

async function entrar(evento) {
  evento.preventDefault();
  const botao = form.querySelector("button[type=submit]");
  botao.disabled = true;
  try {
    await enviarJson("/login", {
      cpf: form.elements.cpf.value,
      senha: form.elements.senha.value,
    });
    window.location.assign("/");
  } catch (erro) {
    mostrarMensagem(mensagem, erro.message, "erro");
    form.elements.senha.value = "";
    form.elements.senha.focus();
    botao.disabled = false;
  }
}

form.addEventListener("submit", entrar);
