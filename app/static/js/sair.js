const botao = document.getElementById("botao-sair");

async function sair() {
  botao.disabled = true;
  try {
    await fetch("/logout", { method: "POST" });
  } finally {
    window.location.assign("/login");
  }
}

botao.addEventListener("click", sair);
