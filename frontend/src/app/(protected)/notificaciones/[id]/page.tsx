/**
 * Resolver notificación — redirige al detalle de solicitud relacionado.
 * Ruta: /notificaciones/[id]
 *
 * 1. Obtiene el ID de la notificación desde params.
 * 2. Llama POST /api/notificaciones/{id}/abrir (marcar apertura).
 * 3. Redirige controladamente a /solicitudes/{solicitud_id}.
 *
 * Si la notificación no tiene solicitud asociada, vuelve a /notificaciones.
 */
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AlertCircle, ArrowLeft, Bell, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageWrapper } from "@/components-app/page";
import api from "@/lib/api";
import type { ApiResponse } from "@/types/api.types";

interface NotificacionResolverData {
  id: string;
  solicitud_id: string | null;
  solicitud_id_publico: string | null;
}

export default function NotificacionDetallePage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    const resolver = async () => {
      try {
        // 1. Obtener datos de la notificación para saber la solicitud_id
        const response = await api.get<ApiResponse<NotificacionResolverData>>(
          `/notificaciones/${id}`,
        );

        const data = response.data?.data;

        if (!data) {
          setError("Notificación no encontrada");
          setIsLoading(false);
          return;
        }

        // 2. Marcar como abierta (auditoría de navegación)
        // No esperamos el resultado para redirigir — la llamada es fire-and-forget
        api
          .post(`/notificaciones/${id}/abrir`)
          .catch(() => {
            // Silenciamos errores de apertura — no deben bloquear la navegación
          });

        // 3. Redirigir a la solicitud relacionada
        if (data.solicitud_id) {
          router.replace(`/solicitudes/${data.solicitud_id}`);
        } else if (data.solicitud_id_publico) {
          // Si solo tenemos id_publico, usamos la bandeja filtrada
          router.replace(`/solicitudes?solicitud=${data.solicitud_id_publico}`);
        } else {
          // Sin solicitud asociada — volver a notificaciones
          setError("Esta notificación no tiene una solicitud asociada");
          setIsLoading(false);
        }
      } catch (err) {
        setError("No se pudo resolver la notificación");
        setIsLoading(false);
      }
    };

    resolver();
  }, [id, router]);

  if (isLoading) {
    return (
      <PageWrapper
        title="Notificación"
        description="Abriendo notificación..."
        icon={<Bell className="h-6 w-6 text-primary" />}
      >
        <div className="app-card flex flex-col items-center justify-center py-16 gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">
            Abriendo notificación...
          </p>
        </div>
      </PageWrapper>
    );
  }

  if (error) {
    return (
      <PageWrapper
        title="Notificación"
        description="Detalle de la notificación"
        icon={<Bell className="h-6 w-6 text-primary" />}
        backHref="/notificaciones"
      >
        <div className="app-card flex flex-col items-center justify-center py-16 gap-4 text-center">
          <div className="p-4 bg-destructive/10 rounded-full">
            <AlertCircle className="h-8 w-8 text-destructive" />
          </div>
          <div>
            <h3 className="font-semibold text-lg">No se pudo abrir</h3>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
          <Button
            variant="outline"
            onClick={() => router.push("/notificaciones")}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver a notificaciones
          </Button>
        </div>
      </PageWrapper>
    );
  }

  return null;
}
