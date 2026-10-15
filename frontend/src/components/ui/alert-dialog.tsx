"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { AlertTriangle, X } from "lucide-react";

interface AlertDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  closeLabel?: string;
  busyLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  tone?: "danger" | "warning";
}

/**
 * Confirmation dialog in the Shadcn style.
 *
 * The project has no dialog primitive installed, so this wraps the native
 * `<dialog>` element: it gives real modal semantics (focus trap, Escape to
 * close, inert background) without pulling in a new dependency.
 */
export function AlertDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel,
  closeLabel = "Close dialog",
  busyLabel,
  busy = false,
  onConfirm,
  tone = "danger",
}: AlertDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const toneClasses =
    tone === "danger"
      ? { badge: "bg-rose-50 text-rose-600", button: "bg-rose-600 hover:bg-rose-700" }
      : { badge: "bg-amber-50 text-amber-600", button: "bg-amber-600 hover:bg-amber-700" };

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="alert-dialog-title"
      className="m-auto w-[min(92vw,28rem)] overflow-hidden rounded-2xl border border-border bg-card p-0 text-foreground shadow-2xl backdrop:bg-slate-950/50 backdrop:backdrop-blur-sm"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onOpenChange(false);
      }}
      onClose={() => onOpenChange(false)}
    >
      <div className="p-6">
        <div className="flex items-start gap-3">
          <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${toneClasses.badge}`}>
            <AlertTriangle size={17} />
          </div>
          <div className="min-w-0 flex-1">
            <h2 id="alert-dialog-title" className="text-base font-bold text-foreground">
              {title}
            </h2>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{description}</p>
          </div>
          <button
            type="button"
            aria-label={closeLabel}
            disabled={busy}
            onClick={() => onOpenChange(false)}
            className="rounded-lg p-1 text-muted-foreground transition hover:bg-muted hover:text-foreground disabled:opacity-50"
          >
            <X size={16} />
          </button>
        </div>

        <div className="mt-6 flex justify-end gap-2 border-t border-border pt-4">
          <button
            type="button"
            disabled={busy}
            onClick={() => onOpenChange(false)}
            className="rounded-lg border border-border px-4 py-2 text-xs font-semibold text-foreground transition hover:bg-muted/60 disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onConfirm}
            className={`rounded-lg px-4 py-2 text-xs font-bold text-white shadow-xs transition disabled:opacity-50 ${toneClasses.button}`}
          >
            {busy ? busyLabel ?? confirmLabel : confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}
