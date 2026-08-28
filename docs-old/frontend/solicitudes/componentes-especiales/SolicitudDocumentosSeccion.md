# SolicitudDocumentosSeccion

Sección colapsable que muestra un visor de documentos PDF. **Presentational** con estado de expansión local.

## Rol en la Arquitectura

- **Sub-sección de detalle**: aparece dentro de la vista de detalle de una solicitud.
- **No fetchea datos**: recibe los URLs y metadata como props.

## Estado Local

| Estado | Tipo | Default | Propósito |
|--------|------|---------|-----------|
| `isExpanded` | `boolean` | `false` | Control de expansión/colapso del acordeón |

## Props

```typescript
interface SolicitudDocumentsSectionProps {
  documentoPrincipal?: string;              // URL del documento principal
  documentosAnexados?: Document[];         // Array de documentos anexados
}

interface Document {
  id: number;
  archivo_anexo: string;    // URL del archivo
  descripcion: string;     // Texto descriptivo
}
```

## Comportamiento de Render

```
totalDocuments = (documentoPrincipal ? 1 : 0) + documentosAnexados.length
```

- Si `totalDocuments === 0` → retorna `null` (no renderiza nada)
- Si `totalDocuments > 0` → renderiza botón toggle + contenido expandable

## Estructura

```
SolicitudDocumentsSection
├── Botón toggle (ChevronDown con rotación)
│   └── Muestra "Documentos (N)"
└── Contenido expandido (if isExpanded)
    ├── PDFViewer (documento principal, si existe)
    └── PDFViewer[] (documentos anexados, mapeados por id)
```

## Interacción

```typescript
onClick={() => setIsExpanded(!isExpanded)}
```

- Click en el botón alterna `isExpanded`
- Chevron rota 180° cuando está expandido

## Dependencias

- `@/components/pdfViewer/PDFViewer`: componente visor de PDF
- `@/components/ui/button`
- `lucide-react`: `ChevronDown`
