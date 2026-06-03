import { useEffect, useState } from "react";

export function useRotatingMessages(messages, intervalMs = 1800) {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (!messages.length) {
      return undefined;
    }

    const interval = window.setInterval(() => {
      setCurrentIndex((value) => (value + 1) % messages.length);
    }, intervalMs);

    return () => window.clearInterval(interval);
  }, [intervalMs, messages]);

  return messages[currentIndex] || "";
}
