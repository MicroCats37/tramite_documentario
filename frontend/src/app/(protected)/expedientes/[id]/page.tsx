"use client";

import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  FileText,
  FolderOpen,
  Link as LinkIcon,
  Paperclip,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageWrapper } from "@/components-app/page";
import { TIPO_PERSONA, TIPO_ARCHIVO, type TipoPersona, type TipoArchivo } from "@/shared/constants/tramite.tokens";
import { useExpedienteDetail } from "@/features/tramites/hooks/useTramites";
import type { ExpedienteDetail } from "@/features/tramites/schemas/tramite.schema";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("es-PE", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

// ── Skeleton ───────────────────────────────────────────────────────────────────

function DetailSkeleton() {
  return (
    <div className="app-page">
      <div className="app-page-header ">
        <Skeleton className="h-10 w-64" />
      </div>
      <div className="space-y-4">
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────────────

function EmptyState({ onBack }: { onBack: () => void }) {
  return (
    <PageWrapper
      title="Detalle de Expediente"
      description="Datos del expediente registrado"
      icon={<FolderOpen className="h-6 w-6 text-primary" />}
      backHref="/expedientes"
    >
      <div className="app-card flex flex-col items-center justify-center py-16 gap-4 text-center">
        <div className="p-4 bg-muted rounded-full">
          <AlertCircle className="h-8 w-8 text-muted-foreground" />
        </div>
        <div>
          <h3 className="font-semibold text-lg">Expediente no encontrado</h3>
          <p className="text-sm text-muted-foreground mt-1">
            No se encontró el expediente solicitado.
          </p>
        </div>
        <Button variant="outline" onClick={onBack}>
          Volver a la consulta
        </Button>
      </div>
    </PageWrapper>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function ExpedienteDetallePage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: item, isLoading, isError } = useExpedienteDetail(id);

  const handleBack = () => router.back();

  if (isLoading) return <DetailSkeleton />;

  if (isError || !item) {
    return <EmptyState onBack={handleBack} />;
  }

  const nombreCompleto =
    item.razon_social ||
    `${item.nombres ?? ""} ${item.apellidos ?? ""}`.trim() ||
    "—";

  return (
    <PageWrapper
      title={item.id_publico ?? "Detalle de Expediente"}
      description="Datos del expediente registrado"
      icon={<FolderOpen className="h-6 w-6 text-primary" />}
      backHref="/expedientes"
      breadcrumbs={[
        { label: "Expedientes", href: "/expedientes" },
        { label: item.id_publico ?? "Detalle" },
      ]}
      actions={
        <Badge className={TIPO_PERSONA[item.tipo_persona as TipoPersona]?.badgeClass}>
          {TIPO_PERSONA[item.tipo_persona as TipoPersona]?.label ?? item.tipo_persona}
        </Badge>
      }
    >
      {/* Datos del Interesado */}
      <div className="app-card p-6 space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Datos del Interesado
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Nombre / Razón Social</span>
            <span className="text-sm flex items-center gap-1.5">
              <User className="h-3.5 w-3.5 text-muted-foreground" />
              {nombreCompleto}
            </span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Documento</span>
            <span className="text-sm">
              {item.tipo_documento} {item.numero_documento ?? "—"}
            </span>
          </div>

          {item.correo && (
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">Correo</span>
              <span className="text-sm">{item.correo}</span>
            </div>
          )}

          {item.telefono && (
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">Teléfono</span>
              <span className="text-sm">{item.telefono}</span>
            </div>
          )}

          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Fecha de Registro</span>
            <span className="text-sm">{formatDate(item.fecha_registro)}</span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Folios</span>
            <span className="text-sm">{item.numero_folios}</span>
          </div>
        </div>

        {item.asunto && (
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Asunto</span>
            <span className="text-sm">{item.asunto}</span>
          </div>
        )}

        {item.observaciones && (
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Observaciones</span>
            <span className="text-sm">{item.observaciones}</span>
          </div>
        )}

        {item.creado_por_nombres && (
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Registrado por</span>
            <span className="text-sm">
              {item.creado_por_nombres}
            </span>
          </div>
        )}
      </div>

      {/* Archivos */}
      <div className="app-card p-6 space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Archivos
        </h2>
        {item.archivos && item.archivos.length > 0 ? (
          <div className="space-y-2">
            {item.archivos.map((archivo) => (
              <div
                key={archivo.id}
                className="flex items-center justify-between bg-muted/50 rounded-lg px-4 py-3 gap-4"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Paperclip className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{archivo.nombre_original}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge
                    className={
                      TIPO_ARCHIVO[archivo.tipo_archivo as TipoArchivo]?.badgeClass ??
                      "bg-muted text-muted-foreground border border-border"
                    }
                  >
                    {TIPO_ARCHIVO[archivo.tipo_archivo as TipoArchivo]?.label ?? archivo.tipo_archivo}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    asChild
                  >
                    <a
                      href={archivo.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="Descargar archivo"
                    >
                      <FileText className="h-4 w-4" />
                    </a>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            No hay archivos asociados a este expediente.
          </p>
        )}
      </div>

      {/* Antecedentes */}
      <div className="app-card p-6 space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Antecedentes
        </h2>
        {item.antecedentes && item.antecedentes.length > 0 ? (
          <div className="space-y-2">
            {item.antecedentes.map((ant) => (
              <div
                key={ant.id_publico}
                className="flex items-center justify-between bg-muted/50 rounded-lg px-4 py-3"
              >
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm font-mono font-medium">
                    {ant.id_publico}
                  </span>
                  {ant.categoria && (
                    <span className="text-xs text-muted-foreground">{ant.categoria}</span>
                  )}
                  {ant.observaciones && (
                    <span className="text-xs text-muted-foreground italic">{ant.observaciones}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            No hay antecedentes registrados para este expediente.
          </p>
        )}
      </div>

      {/* Solicitud Asociada */}
      {item.solicitud_id && (
        <div className="app-card p-6 space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Solicitud Asociada
          </h2>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              Este expediente tiene una solicitud asociada.
            </span>
            <Button
              variant="outline"
              size="sm"
              className="gap-2 shrink-0"
              onClick={() => router.push(`/solicitudes/${item.solicitud_id}`)}
            >
              <LinkIcon className="h-3.5 w-3.5" />
              Ver Solicitud
            </Button>
          </div>
        </div>
      )}
    </PageWrapper>
  );
}
