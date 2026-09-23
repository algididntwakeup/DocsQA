"use client";

import { Panel, Separator, Group } from "react-resizable-panels";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export function ResizablePanelGroup({ className, ...props }: ComponentProps<typeof Group>) {
  return <Group className={cn("flex h-full w-full", className)} {...props} />;
}

export function ResizablePanel({ className, ...props }: ComponentProps<typeof Panel>) {
  return <Panel className={cn("h-full min-w-0 overflow-hidden", className)} {...props} />;
}

export function ResizableHandle({ className, ...props }: ComponentProps<typeof Separator>) {
  return (
    <Separator
      className={cn(
        "w-px shrink-0 bg-border transition-colors hover:bg-primary/40 focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      {...props}
    />
  );
}
