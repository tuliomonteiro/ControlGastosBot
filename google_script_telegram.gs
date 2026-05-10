// Public repo safe version.
// Replace these placeholders in your Apps Script project before running it.
var TELEGRAM_BOT_TOKEN = "SET_TELEGRAM_BOT_TOKEN";
var TELEGRAM_CHAT_ID = "SET_TELEGRAM_CHAT_ID";
var SHEET_NAME = "2026";

function enviarRelatorioSemanal() {
  gerarRelatorio("SEMANAL");
}

function enviarRelatorioMensal() {
  gerarRelatorio("MENSAL");
}

function gerarRelatorio(tipo) {
  if (
    TELEGRAM_BOT_TOKEN === "SET_TELEGRAM_BOT_TOKEN" ||
    TELEGRAM_CHAT_ID === "SET_TELEGRAM_CHAT_ID"
  ) {
    throw new Error("Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID before running the script.");
  }

  var aba = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  var dados = aba.getDataRange().getValues();

  var totalGeral = 0;
  var totalFacturado = 0;
  var categorias = {};

  var hoje = new Date();
  var dataInicio = new Date();
  var dataFim = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate() - 1, 23, 59, 59, 999);
  var titulo = "";

  if (tipo === "SEMANAL") {
    titulo = "📊 *RESUMO SEMANAL*";
    dataInicio = new Date(dataFim.getTime() - (6 * 24 * 60 * 60 * 1000));
    dataInicio.setHours(0, 0, 0, 0);
  } else if (tipo === "MENSAL") {
    titulo = "📊 *RESUMO MENSAL*";
    dataInicio = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1, 0, 0, 0, 0);
    dataFim = new Date(hoje.getFullYear(), hoje.getMonth(), 0, 23, 59, 59, 999);
  } else {
    throw new Error("Tipo de relatorio invalido: " + tipo);
  }

  for (var i = 1; i < dados.length; i++) {
    var linha = dados[i];
    if (!linha[4] || !linha[5]) continue;

    var dataBruta = linha[5];
    var dataGasto = dataBruta instanceof Date ? dataBruta : null;
    if (!dataGasto) {
      var partes = dataBruta.toString().split("/");
      if (partes.length === 3) {
        dataGasto = new Date(partes[2], partes[1] - 1, partes[0]);
      }
    }

    if (dataGasto && dataGasto >= dataInicio && dataGasto <= dataFim) {
      var valorTexto = linha[4].toString();
      var valorLimpo = valorTexto.replace(/\./g, "").replace(",", ".");
      var valor = parseFloat(valorLimpo) || 0;

      var cat = linha[6] ? linha[6].toString().trim() : "OUTRA";

      totalGeral += valor;
      categorias[cat] = (categorias[cat] || 0) + valor;

      var temFactura = linha[9] ? linha[9].toString().toUpperCase().trim() : "NO";
      if (temFactura === "SI") {
        totalFacturado += valor;
      }
    }
  }

  if (totalGeral <= 0) {
    return;
  }

  var mensagem = montarMensagemResumo(titulo, totalGeral, totalFacturado, categorias);

  UrlFetchApp.fetch("https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage", {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify({
      chat_id: TELEGRAM_CHAT_ID,
      text: mensagem,
      parse_mode: "Markdown"
    })
  });
}

function montarMensagemResumo(titulo, totalGeral, totalFacturado, categorias) {
  var mensagem = titulo + "\n\n";
  mensagem += "💰 *Total Gasto:* " + formatarMoeda(totalGeral) + " Gs\n";
  mensagem += "🧾 *Total Facturado:* " + formatarMoeda(totalFacturado) + " Gs\n\n";
  mensagem += "📉 *Por Categoria:*\n";

  var sortedCats = Object.keys(categorias).sort(function(a, b) {
    return categorias[b] - categorias[a];
  });

  for (var j = 0; j < sortedCats.length; j++) {
    var categoria = sortedCats[j];
    var valorCategoria = categorias[categoria];
    var percentual = (valorCategoria / totalGeral) * 100;
    mensagem += "- " + categoria + " (" + percentual.toFixed(0) + "%): " + formatarMoeda(valorCategoria) + " Gs\n";
  }

  return mensagem;
}

function formatarMoeda(valor) {
  return valor.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}
