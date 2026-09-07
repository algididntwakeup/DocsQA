import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

if (typeof Element !== "undefined") {
  Element.prototype.scrollIntoView = () => {};
}

afterEach(() => {
  cleanup();
});
