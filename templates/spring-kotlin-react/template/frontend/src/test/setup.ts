// jsdom implements no matchMedia, and Mantine calls it while rendering any themed
// component — so without this stub the first component test fails with
// "window.matchMedia is not a function" instead of anything about the component.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})
