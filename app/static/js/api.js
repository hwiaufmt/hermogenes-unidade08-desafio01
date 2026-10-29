export function mensagemDeErro(corpo) {
  const detalhe = corpo?.detail;
  if (typeof detalhe === "string") return detalhe;
  if (Array.isArray(detalhe) && detalhe.length > 0) {
    return detalhe
      .map((item) => String(item.msg).replace(/^Value error, /, ""))
      .join(" ");
  }
  return "Não foi possível concluir a operação.";
}

export class ErroDeApi extends Error {
  constructor(mensagem, status, corpo) {
    super(mensagem);
    this.status = status;
    this.corpo = corpo;
  }
}

export async function requisitar(url, opcoes = {}) {
  let resposta;
  try {
    resposta = await fetch(url, opcoes);
  } catch {
    throw new Error("Falha de conexão com o servidor.");
  }
  const corpo = await resposta.json().catch(() => null);
  if (resposta.status === 401 && url !== "/login") {
    window.location.assign("/login");
  }
  if (!resposta.ok) throw new ErroDeApi(mensagemDeErro(corpo), resposta.status, corpo);
  return corpo;
}

export function enviarJson(url, dados, metodo = "POST") {
  return requisitar(url, {
    method: metodo,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  });
}

export function mostrarMensagem(elemento, texto, tipo) {
  elemento.textContent = texto;
  elemento.dataset.tipo = tipo;
  elemento.hidden = false;
}
