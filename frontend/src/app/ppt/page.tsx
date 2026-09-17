"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import "./ppt.css";

const TOTAL_SLIDES = 7;
const SLIDE_IMAGES = Array.from({ length: TOTAL_SLIDES }, (_, i) => `/slides/slide-${i + 1}.png`);

/* ═══════════════════════════════════════════════════════════════════
   Presentation Page — Full-screen slide viewer using exported images
   ═══════════════════════════════════════════════════════════════════ */
export default function PresentationPage() {
  const [current, setCurrent] = useState(0);
  const touchStartX = useRef(0);
  const router = useRouter();

  const goNext = useCallback(
    () => setCurrent((c) => Math.min(c + 1, TOTAL_SLIDES - 1)),
    [],
  );
  const goPrev = useCallback(
    () => setCurrent((c) => Math.max(c - 1, 0)),
    [],
  );

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  }, []);

  /* Keyboard navigation */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      switch (e.key) {
        case "ArrowRight":
        case " ":
          e.preventDefault();
          goNext();
          break;
        case "ArrowLeft":
          e.preventDefault();
          goPrev();
          break;
        case "f":
        case "F":
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            toggleFullscreen();
          }
          break;
        case "Escape":
          if (!document.fullscreenElement) router.push("/");
          break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [goNext, goPrev, toggleFullscreen, router]);

  /* Click navigation — left half = prev, right half = next */
  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest(".ppt-controls")) return;
    const { clientX, currentTarget } = e;
    const rect = currentTarget.getBoundingClientRect();
    if (clientX - rect.left > rect.width * 0.5) goNext();
    else goPrev();
  };

  /* Touch / swipe navigation */
  const onTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  };
  const onTouchEnd = (e: React.TouchEvent) => {
    const diff = touchStartX.current - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 50) {
      diff > 0 ? goNext() : goPrev();
    }
  };

  return (
    <div
      className="ppt-viewport"
      onClick={handleClick}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      {/* Progress bar */}
      <div
        className="ppt-progress"
        style={{ width: `${((current + 1) / TOTAL_SLIDES) * 100}%` }}
      />

      {/* Exit — full-screen viewers have no browser chrome to fall back on */}
      <Link
        href="/"
        className="ppt-exit-btn"
        onClick={(e) => e.stopPropagation()}
        aria-label="Exit presentation"
      >
        ×
      </Link>

      {/* Slide track */}
      <div
        className="ppt-track"
        style={{ transform: `translateX(-${current * 100}vw)` }}
      >
        {SLIDE_IMAGES.map((src, i) => (
          <div key={i} className="ppt-slide">
            <Image
              src={src}
              alt={`Slide ${i + 1}`}
              fill
              priority={i <= 1}
              quality={100}
              style={{ objectFit: "contain" }}
              sizes="100vw"
            />
          </div>
        ))}
      </div>

      {/* Navigation controls */}
      <div className="ppt-controls" onClick={(e) => e.stopPropagation()}>
        <button
          className="ppt-nav-btn"
          onClick={goPrev}
          disabled={current === 0}
          aria-label="Previous slide"
        >
          ‹
        </button>
        <span className="ppt-counter">
          {current + 1}&nbsp;/&nbsp;{TOTAL_SLIDES}
        </span>
        <button
          className="ppt-nav-btn"
          onClick={goNext}
          disabled={current === TOTAL_SLIDES - 1}
          aria-label="Next slide"
        >
          ›
        </button>
        <button
          className="ppt-nav-btn"
          onClick={toggleFullscreen}
          aria-label="Toggle fullscreen"
        >
          ⛶
        </button>
      </div>

      <div className="ppt-hints">← → navigate · F fullscreen · ESC exit</div>
    </div>
  );
}
