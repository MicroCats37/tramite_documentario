import { FolderOpen } from "lucide-react";
import { redirect } from "next/navigation";
import { PageWrapper } from "@/components-app/page";
import { ProyectosView } from "@/features/proyectos/views/ProyectosView";
import { getUserSession } from "@/lib/auth";

/**
 * Página de Proyectos - protegida por auth.
 *
 * Lista proyectos con liquidaciones de edificaciones usando paginación.
 * Endpoint: GET /api/proyectos/?page=&page_size=
 */
export default async function ProyectosPage() {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return (
    <PageWrapper
      title="Proyectos"
      description="Gestiona los proyectos de liquidaciones"
      icon={<FolderOpen className="h-6 w-6 text-primary" />}
    >
      <ProyectosView />
    </PageWrapper>
  );
}
