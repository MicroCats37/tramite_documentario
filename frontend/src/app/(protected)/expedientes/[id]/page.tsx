"use client";

import {
  AlertCircle,
  FileText,
  FolderOpen,
  Link as LinkIcon,
  Paperclip,
  User,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageWrapper } from "@/components-app/page";
import { useExpedienteDetail } from "@/features/tramites/hooks/useTramites";
import {
  TIPO_ARCHIVO,
  TIPO_PERSONA,
  type TipoArchivo,
  type TipoPersona,
} from "@/shared/constants/tramite.tokens";

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
        <Badge
          className={TIPO_PERSONA[item.tipo_persona as TipoPersona]?.badgeClass}
        >
          {TIPO_PERSONA[item.tipo_persona as TipoPersona]?.label ??
            item.tipo_persona}
        </Badge>
      }
    >
      {/*
        Expediente has no chat — single-column content flow,
        content-proportional. No empty right rail.
      */}
      <div className="min-w-0 space-y-5">
        <div className="app-card overflow-hidden p-0">
          <div className="border-b border-border/70 bg-muted/30 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Interesado
            </p>
            <h2 className="mt-1 flex items-center gap-2 text-lg font-semibold leading-snug">
              <User className="h-4 w-4 text-muted-foreground" />
              {nombreCompleto}
            </h2>
            {item.asunto && (
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {item.asunto}
              </p>
            )}
          </div>

          <div className="grid gap-3 p-5 [grid-template-columns:repeat(auto-fit,minmax(11rem,1fr))]">
            <div className="rounded-xl border border-border/70 bg-background p-3">
              <span className="text-xs text-muted-foreground">Documento</span>
              <p className="mt-1 text-sm font-medium">
                {item.tipo_documento.nombre} {item.numero_documento ?? "—"}
              </p>
            </div>
            {item.correo && (
              <div className="rounded-xl border border-border/70 bg-background p-3">
                <span className="text-xs text-muted-foreground">Correo</span>
                <p className="mt-1 break-words text-sm font-medium">
                  {item.correo}
                </p>
              </div>
            )}
            {item.telefono && (
              <div className="rounded-xl border border-border/70 bg-background p-3">
                <span className="text-xs text-muted-foreground">Teléfono</span>
                <p className="mt-1 text-sm font-medium">{item.telefono}</p>
              </div>
            )}
            <div className="rounded-xl border border-border/70 bg-background p-3">
              <span className="text-xs text-muted-foreground">
                Fecha de Registro
              </span>
              <p className="mt-1 text-sm font-medium">
                {formatDate(item.fecha_registro)}
              </p>
            </div>
            <div className="rounded-xl border border-border/70 bg-background p-3">
              <span className="text-xs text-muted-foreground">Folios</span>
              <p className="mt-1 text-sm font-medium">{item.numero_folios}</p>
            </div>
            {item.creado_por_nombres && (
              <div className="rounded-xl border border-border/70 bg-background p-3">
                <span className="text-xs text-muted-foreground">
                  Registrado por
                </span>
                <p className="mt-1 text-sm font-medium">
                  {item.creado_por_nombres}
                </p>
              </div>
            )}
          </div>

          {item.observaciones && (
            <div className="border-t border-border/70 px-5 py-4">
              <span className="text-xs text-muted-foreground">
                Observaciones
              </span>
              <p className="mt-1 text-sm leading-relaxed">
                {item.observaciones}
              </p>
            </div>
          )}
        </div>

        <div className="app-card p-5 space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Archivos
          </h2>
          {item.archivos && item.archivos.length > 0 ? (
            <div className="grid gap-2 [grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr))]">
              {item.archivos.map((archivo) => (
                <div
                  key={archivo.id}
                  className="flex items-center justify-between gap-4 rounded-xl border border-border/70 bg-background px-4 py-3"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Paperclip className="h-4 w-4 text-muted-foreground shrink-0" />
                    <p className="truncate text-sm font-medium">
                      {archivo.nombre_original}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge
                      className={
                        TIPO_ARCHIVO[archivo.tipo_archivo as TipoArchivo]
                          ?.badgeClass ??
                        "bg-muted text-muted-foreground border border-border"
                      }
                    >
                      {TIPO_ARCHIVO[archivo.tipo_archivo as TipoArchivo]
                        ?.label ?? archivo.tipo_archivo}
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

        <div className="app-card p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Antecedentes
            </h2>
            <span className="text-xs text-muted-foreground">
              {item.antecedentes?.length ?? 0} registros
            </span>
          </div>
          {item.antecedentes && item.antecedentes.length > 0 ? (
            <div className="grid gap-2 [grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr))]">
              {item.antecedentes.map((ant) => (
                <div
                  key={ant.id_publico}
                  className="rounded-xl border border-border/70 bg-background px-4 py-3"
                >
                  <span className="text-sm font-mono font-medium">
                    {ant.id_publico}
                  </span>
                  {ant.categoria && (
                    <p className="text-xs text-muted-foreground">
                      {ant.categoria}
                    </p>
                  )}
                  {ant.observaciones && (
                    <p className="mt-1 text-xs text-muted-foreground italic">
                      {ant.observaciones}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground italic">
              No hay antecedentes registrados para este expediente.
            </p>
          )}
        </div>

        {item.solicitud_id && (
          <div className="app-card p-5 space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Solicitud Asociada
            </h2>
            <p className="text-sm text-muted-foreground">
              Este expediente tiene una solicitud asociada.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => router.push(`/solicitudes/${item.solicitud_id}`)}
            >
              <LinkIcon className="h-3.5 w-3.5" />
              Ver Solicitud
            </Button>
          </div>
        )}
      </div>
    </PageWrapper>
  );
}
