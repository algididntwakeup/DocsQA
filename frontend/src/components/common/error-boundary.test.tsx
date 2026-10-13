import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ErrorBoundary } from "./error-boundary";

describe("ErrorBoundary", () => {
  afterEach(() => {
    Reflect.deleteProperty(navigator, "sendBeacon");
    Reflect.deleteProperty(navigator, "clipboard");
    vi.restoreAllMocks();
  });

  it("shows a recovery UI, reports the crash, and copies its trace ID", async () => {
    const sendBeacon = vi.fn((url: string, data: BodyInit) =>
      url === "/api/v1/logs/client" && data instanceof Blob,
    );
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "sendBeacon", { configurable: true, value: sendBeacon });
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    vi.spyOn(console, "error").mockImplementation(() => undefined);

    const crash = new Error("Test Crash");
    function BrokenWidget(): ReactNode {
      throw crash;
    }

    render(
      <ErrorBoundary>
        <BrokenWidget />
      </ErrorBoundary>,
    );

    expect(screen.getByRole("heading", { name: "Terjadi Kendala Teknis" })).toBeTruthy();
    expect(screen.getByText(/Kode pelacak:/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Muat Ulang Halaman" })).toBeTruthy();
    expect(sendBeacon).toHaveBeenCalledWith(
      "/api/v1/logs/client",
      expect.objectContaining({ type: "application/json" }),
    );
    const reportBlob = sendBeacon.mock.calls[0]?.[1] as Blob | undefined;
    if (!(reportBlob instanceof Blob)) throw new Error("Expected the logger to enqueue a JSON Blob.");
    const report = JSON.parse(await reportBlob.text()) as {
      message: string;
      component_stack: string | null;
      correlation_id: string;
      timestamp: string;
    };
    expect(report.message).toBe("Test Crash");
    expect(report.component_stack).toContain("BrokenWidget");
    expect(report.correlation_id).toBeTruthy();
    expect(screen.getByText(/Kode pelacak:/).textContent).toContain(report.correlation_id);
    expect(report.timestamp).toBeTruthy();

    await fireEvent.click(screen.getByRole("button", { name: "Copy Tracking Code" }));
    expect(writeText).toHaveBeenCalledWith(expect.any(String));
    expect(await screen.findByRole("button", { name: "Tracking Code Copied" })).toBeTruthy();
  });
});
