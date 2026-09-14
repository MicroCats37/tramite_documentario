"use client";

import {
  BookOpen,
  CheckCircle2,
  FileText,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { PageWrapper } from "@/components-app/page/PageWrapper";
import { LibroReclamacionesForm } from "@/features/libro-reclamaciones/components";
import { useLibroReclamacionesUIStore } from "@/features/libro-reclamaciones/store";

/**
 * Libro de Reclamaciones — Stepper Form UI
 *
 * Route: /libro-reclamaciones
 * Reference: https://servicioscdl.ciplima.org.pe/libro-de-reclamaciones/
 *
 * HARD CONSTRAINT: FRONTEND ONLY.
 * No backend endpoint, service calls, API hooks, database, or migrations.
 * Submit is mock/local only — shows success toast and does not POST anywhere.
 */

// ── Legal / info cards ────────────────────────────────────────────────────────

function LegalCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-border/60 bg-card p-4 hover:border-primary/30 transition-colors duration-200">
      <div className="p-2 rounded-lg bg-primary/10 text-primary shrink-0">
        <Icon className="h-4 w-4" />
      </div>
      <div className="space-y-0.5">
        <p className="text-sm font-semibold text-foreground">{title}</p>
        <p className="text-xs text-muted-foreground leading-relaxed">
          {description}
        </p>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function LibroReclamacionesPage() {
  const { open, isSubmitted } = useLibroReclamacionesUIStore();

  return (
    <PageWrapper
      title="Libro de Reclamaciones"
      description="Formulario de reclamaciones y quejas — Ley N° 29571"
      icon={<BookOpen className="h-6 w-6 text-primary" />}
    >
      {/* ── Hero banner ──────────────────────────────────────────────────── */}
      {!isSubmitted && (
        <div className="relative overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/5 via-background to-primary/10 p-6 sm:p-8 mb-6">
          {/* Decorative accent */}
          <div className="absolute top-0 right-0 w-48 h-48 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-32 h-32 bg-primary/5 rounded-full blur-2xl pointer-events-none" />

          <div className="relative flex flex-col sm:flex-row sm:items-center gap-5">
            <div className="flex-1 space-y-3">
              <div className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                <Sparkles className="h-3 w-3" />
                Ley N° 29571 — Código de Protección y Defensa del Consumidor
              </div>
              <h2 className="text-xl sm:text-2xl font-black text-foreground leading-tight">
                ¿Tiene una reclamación o queja?
              </h2>
              <p className="text-sm text-muted-foreground max-w-lg leading-relaxed">
                Complete el formulario en línea. Su reclamación será registrada
                y atendida de acuerdo con la normativa vigente. Todo proceso es
                gratuito y confidencial.
              </p>
            </div>

            <div className="shrink-0">
              <Button
                size="lg"
                className="gap-2 font-bold shadow-lg shadow-primary/20 rounded-xl h-12 px-8"
                onClick={open}
              >
                <FileText className="h-4 w-4" />
                Registrar reclamación
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── Info cards (hidden after submission) ─────────────────────────── */}
      {!isSubmitted && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          <LegalCard
            icon={CheckCircle2}
            title="Derecho a ser escuchado"
            description="Todo consumidor tiene derecho a presentar reclamaciones y quejas ante las entidades, de forma gratuita."
          />
          <LegalCard
            icon={ShieldCheck}
            title="Protección de datos"
            description="Sus datos personales están protegidos. La información se utiliza exclusivamente para atender su reclamo."
          />
          <LegalCard
            icon={FileText}
            title="Seguimiento gratuito"
            description="Reciba un código de seguimiento. El trámite es completamente gratuito, sin costos por derecho de trámite."
          />
        </div>
      )}

      {/* ── Feature form (renders modal + inline success state) ─────────── */}
      <LibroReclamacionesForm />
    </PageWrapper>
  );
}
