export function formatGuaraniAmount(value: number) {
  return new Intl.NumberFormat("es-PY", {
    maximumFractionDigits: 0,
  }).format(value);
}
