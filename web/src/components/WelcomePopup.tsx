import { useCallback, useEffect, useState } from "react";

export const WELCOME_KEY = "paris-cinema:welcomed";

const HEARTS = "♥ ♥ ♥ ♥ ♥";

export function WelcomePopup() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(WELCOME_KEY)) setShow(true);
    } catch {
      // Storage unavailable (private mode): show it; dismissal just won't persist.
      setShow(true);
    }
  }, []);

  const dismiss = useCallback(() => {
    try {
      localStorage.setItem(WELCOME_KEY, "1");
    } catch {
      // Non-persisting environment; dismissal lasts for this session only.
    }
    setShow(false);
  }, []);

  useEffect(() => {
    if (!show) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") dismiss();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [show, dismiss]);

  if (!show) return null;

  return (
    <div
      className="popup-overlay"
      onClick={dismiss}
      role="dialog"
      aria-modal="true"
      aria-label="A message for you"
    >
      <div className="popup-card" onClick={(e) => e.stopPropagation()}>
        <div className="popup-hearts" aria-hidden="true">{HEARTS}</div>
        <p className="popup-line popup-greeting">To the love of my life,</p>
        <p className="popup-line">
          Doğum günün kutlu olsun, nice mutlu yıllara. I made this small website for
          you so you don’t have to go site by site to find what movie you can go to.
          You are the first and only person that has it, so I hope you don’t find too
          many bugs. I love you as much as every millisecond in every movie that was
          ever filmed. Feliz cumpleaños mi amor, I hope I can celebrate many many more
          birthdays of yours.
        </p>
        <p className="popup-sig">— Deniz</p>
        <div className="popup-hearts" aria-hidden="true">{HEARTS}</div>
        <button className="popup-close" onClick={dismiss} autoFocus aria-label="Close">
          ♥
        </button>
      </div>
    </div>
  );
}
