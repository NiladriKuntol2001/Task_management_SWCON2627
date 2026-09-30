import { useCallback, useEffect, useState } from "react";

/** Track an element's rendered width so SVG charts draw at real pixel size
 *  (crisp text, no stretched strokes) and reflow on resize. Uses a callback
 *  ref so it still works if the element mounts after the first render. */
export function useWidth<T extends HTMLElement>(fallback = 600) {
  const [node, setNode] = useState<T | null>(null);
  const [width, setWidth] = useState(fallback);

  const ref = useCallback((el: T | null) => setNode(el), []);

  useEffect(() => {
    if (!node) return;
    setWidth(node.clientWidth || fallback);
    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w) setWidth(w);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [node, fallback]);

  return [ref, width] as const;
}
