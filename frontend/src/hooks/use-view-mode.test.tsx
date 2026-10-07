import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useViewMode } from "@/hooks/use-view-mode";

describe("useViewMode", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("defaults to table view", () => {
    const { result } = renderHook(() => useViewMode());

    expect(result.current[0]).toBe("table");
  });

  it("persists the selected view and restores it after remount", () => {
    const firstMount = renderHook(() => useViewMode());

    act(() => firstMount.result.current[1]("grid"));

    expect(firstMount.result.current[0]).toBe("grid");
    expect(window.localStorage.getItem("prism_project_view_mode")).toBe("grid");
    firstMount.unmount();

    const secondMount = renderHook(() => useViewMode());
    expect(secondMount.result.current[0]).toBe("grid");
  });
});
