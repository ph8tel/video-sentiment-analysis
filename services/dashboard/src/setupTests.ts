import "@testing-library/jest-dom";

// Recharts internally uses ResizeObserver, which jsdom doesn't provide.
window.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Recharts SVG layout helpers missing in jsdom
if (typeof window !== "undefined" && window.SVGElement) {
  Object.defineProperty(window.SVGElement.prototype, "getBBox", {
    writable: true,
    value: () => ({ x: 0, y: 0, width: 0, height: 0 }),
  });
}
