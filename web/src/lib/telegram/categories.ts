const categoryKeywords: Record<string, string[]> = {
  mercado: ["mercado", "fortis", "superseis", "box", "stock", "huerta"],
  alimentacao: [
    "almoco",
    "almoço",
    "janta",
    "jantar",
    "cafe",
    "lunch",
    "dinner",
    "pizza",
    "burger",
    "sushi",
    "restaurante",
    "mcdonalds",
  ],
  casa: ["aluguel", "alquiler", "luz", "agua", "tigo", "claro", "casa"],
  transporte: ["uber", "bolt", "gasolina", "combustivel", "combustible", "pedagio"],
  saude: ["farmacia", "hospital", "saude", "salud", "remedio"],
  assinaturas: ["spotify", "chatgpt", "prime", "icloud", "vpn", "google one"],
  educacao: ["curso", "udemy", "livro", "certificacao", "certificación"],
  tecnologia: ["tecnologia", "software", "hosting", "dominio"],
  lazer: ["kart", "airbnb", "hospedagem", "bar", "lazer"],
  roupas: ["nike", "zara", "roupa", "sapato", "tenis"],
  taxas: ["taxa", "tarifa", "comissao", "comisión"],
  impostos: ["imposto", "tax", "tributo"],
};

function normalize(text: string) {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

export function inferCategorySlug(description: string) {
  const normalized = normalize(description);

  for (const [slug, keywords] of Object.entries(categoryKeywords)) {
    if (keywords.some((keyword) => normalized.includes(normalize(keyword)))) {
      return slug;
    }
  }

  return "uncategorized";
}
