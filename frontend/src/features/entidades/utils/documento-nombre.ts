/**
 * Parser del `razon_social` que devuelve la consulta externa de DNI.
 *
 * El worker (`worker/scraper/documento_scraper.py`) puede devolver dos formas:
 *
 *   1. Formato principal (RUC-detail flow):
 *        "APELLIDO_PATERNO APELLIDO_MATERNO, NOMBRES"
 *      ej.: "CALLIRGOS OROZCO, PIERO ALDAIR"
 *
 *   2. Fallback histórico (parseo del h4 si el portal cambió/no respondió):
 *        "APELLIDO_PATERNO APELLIDO_MATERNO NOMBRES"
 *      ej.: "CALLIRGOS OROZCO PIERO ALDAIR"
 *      (mismas palabras, sin la coma separadora)
 *
 * Estrategia de parseo (convención peruana — apellidos primero):
 *   - Si hay ", " → parte izquierda = apellidos, parte derecha = nombres.
 *   - Si NO hay coma → fallback por palabras:
 *       * 1 palabra     → todo a `nombres`.
 *       * 2 palabras    → primera = apellidos, segunda = nombres.
 *       * 3+ palabras   → primeras 2 = apellidos, resto = nombres.
 *
 * Devuelve { nombres, apellidos } con cada campo trim()'eado.
 * Si `razonSocial` viene vacío/null, devuelve ambos vacíos (no se escribe nada).
 */
export interface NombresPartidos {
  nombres: string;
  apellidos: string;
}

export function parseDniRazonSocial(
  razonSocial: string | null | undefined,
): NombresPartidos {
  const trimmed = (razonSocial ?? "").trim();
  if (!trimmed) {
    return { nombres: "", apellidos: "" };
  }

  // Estrategia 1: separador ", " del flujo principal del worker.
  const parts = trimmed.split(", ");
  if (parts.length === 2) {
    return {
      apellidos: parts[0].trim(),
      nombres: parts[1].trim(),
    };
  }

  // Estrategia 2: fallback sin coma (flujo histórico del worker).
  // Convención peruana: las palabras de apellidos van primero.
  const words = trimmed.split(/\s+/).filter(Boolean);
  if (words.length === 1) {
    return { apellidos: "", nombres: words[0] };
  }
  if (words.length === 2) {
    return { apellidos: words[0], nombres: words[1] };
  }
  return {
    apellidos: words.slice(0, 2).join(" "),
    nombres: words.slice(2).join(" "),
  };
}
