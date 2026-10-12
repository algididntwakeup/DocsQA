import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as pdfjsLib from "pdfjs-dist";
import { PdfCanvasViewer } from "./pdf-canvas-viewer";

const pageViewport = { width: 600, height: 800 };
const renderMock = vi.fn().mockResolvedValue(undefined);

vi.mock("pdfjs-dist", () => ({
  GlobalWorkerOptions: { workerSrc: "" },
  getDocument: vi.fn(),
}));

function installPdfDocumentMock() {
  const page = {
    getViewport: ({ scale }: { scale: number }) => ({
      width: pageViewport.width * scale,
      height: pageViewport.height * scale,
    }),
    render: renderMock,
    cleanup: vi.fn(),
  };
  vi.mocked(pdfjsLib.getDocument).mockReturnValue({
    promise: Promise.resolve({
      numPages: 3,
      getPage: vi.fn().mockResolvedValue(page),
      cleanup: vi.fn().mockResolvedValue(undefined),
    }),
    destroy: vi.fn().mockResolvedValue(undefined),
  } as never);
}

describe("PdfCanvasViewer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.cookie = "access_token=Bearer test-token";
    installPdfDocumentMock();

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        arrayBuffer: async () => new Uint8Array([1, 2, 3]).buffer,
        json: async () => ({}),
      }),
    );

    vi.stubGlobal(
      "ResizeObserver",
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      },
    );
  });

  function renderViewer() {
    return render(
      <PdfCanvasViewer
        documentId="doc-1"
        currentPage={1}
        onPageChange={() => undefined}
        totalPages={3}
      />,
    );
  }

  it("fetches the PDF with cookie credentials and a bearer token", async () => {
    renderViewer();
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    const [url, options] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/documents/doc-1/pdf");
    expect(options.credentials).toBe("include");
    expect((options.headers as Record<string, string>).Authorization).toBe("Bearer test-token");
    expect(url).not.toContain("test-token");
  });

  it("renders the canvas at the shared page wrapper size", async () => {
    renderViewer();
    const canvas = await screen.findByTestId("pdf-canvas");
    const surface = screen.getByTestId("pdf-page-surface");
    await waitFor(() => {
      expect(canvas.style.width).not.toBe("");
      expect(canvas.style.width).toBe(surface.style.width);
      expect(canvas.style.height).toBe(surface.style.height);
    });
  });

  it("zooms continuously on ctrl+wheel and clamps to the zoom bounds", async () => {
    renderViewer();
    await screen.findByTestId("pdf-canvas");
    const scrollArea = screen.getByTestId("pdf-scroll-area");

    fireEvent.wheel(scrollArea, { deltaY: -120, ctrlKey: true, clientX: 10, clientY: 10 });
    await waitFor(() => expect(screen.getByText(/^\d+%$/).textContent).not.toBe("100%"));
    const firstZoom = screen.getByText(/^\d+%$/).textContent;

    fireEvent.wheel(scrollArea, { deltaY: -60, ctrlKey: true, clientX: 10, clientY: 10 });
    await waitFor(() => expect(screen.getByText(/^\d+%$/).textContent).not.toBe(firstZoom));
    const secondZoom = screen.getByText(/^\d+%$/).textContent;

    expect(Number.parseInt(firstZoom ?? "0", 10)).toBeGreaterThan(100);
    expect(Number.parseInt(secondZoom ?? "0", 10)).toBeGreaterThan(
      Number.parseInt(firstZoom ?? "0", 10),
    );
    expect(Number.parseInt(secondZoom ?? "0", 10)).toBeLessThanOrEqual(1000);
  });

  it("leaves zoom unchanged for a plain wheel event", async () => {
    renderViewer();
    await screen.findByTestId("pdf-canvas");
    const scrollArea = screen.getByTestId("pdf-scroll-area");

    fireEvent.wheel(scrollArea, { deltaY: -240, clientX: 10, clientY: 10 });
    expect(screen.getByText("100%")).toBeDefined();
  });

  it("pans the scroll container on mouse drag", async () => {
    renderViewer();
    const surface = await screen.findByTestId("pdf-page-surface");
    const scrollArea = screen.getByTestId("pdf-scroll-area");
    const capture = vi.fn();
    Object.assign(surface, { setPointerCapture: capture, hasPointerCapture: () => true });

    fireEvent.pointerDown(surface, {
      button: 0,
      pointerType: "mouse",
      pointerId: 1,
      clientX: 100,
      clientY: 100,
    });
    fireEvent.pointerMove(surface, { pointerId: 1, clientX: 40, clientY: 30 });
    fireEvent.pointerUp(surface, { pointerId: 1, clientX: 40, clientY: 30 });

    expect(capture).toHaveBeenCalledWith(1);
    expect(scrollArea.scrollLeft).toBe(60);
    expect(scrollArea.scrollTop).toBe(70);
  });

  it("zooms with Meta+wheel and leaves touch pointer movement native", async () => {
    renderViewer();
    const surface = await screen.findByTestId("pdf-page-surface");
    const scrollArea = screen.getByTestId("pdf-scroll-area");

    fireEvent.wheel(scrollArea, { deltaY: -60, metaKey: true, clientX: 10, clientY: 10 });
    await waitFor(() => expect(screen.getByText(/^[1-9]\d*%$/).textContent).not.toBe("100%"));
    await waitFor(() => expect(scrollArea.scrollLeft).not.toBe(0));
    const zoom = screen.getByText(/^[1-9]\d*%$/).textContent;
    const scrollLeftBeforeTouch = scrollArea.scrollLeft;
    const scrollTopBeforeTouch = scrollArea.scrollTop;

    const down = fireEvent.pointerDown(surface, {
      button: 0,
      pointerType: "touch",
      pointerId: 2,
      clientX: 100,
      clientY: 100,
    });
    fireEvent.pointerMove(surface, { pointerId: 2, pointerType: "touch", clientX: 40, clientY: 30 });
    fireEvent.pointerUp(surface, { pointerId: 2, pointerType: "touch", clientX: 40, clientY: 30 });

    expect(down).toBe(true);
    expect(scrollArea.scrollLeft).toBe(scrollLeftBeforeTouch);
    expect(scrollArea.scrollTop).toBe(scrollTopBeforeTouch);
    expect(screen.getByText(/^[1-9]\d*%$/).textContent).toBe(zoom);
  });
});
